"""
LatenightPipeline Diagram API Service

A thin HTTP layer around the existing infographic generation pipeline.
Receives diagram requests over the network, runs the full local pipeline
(LLM → GBNF → Validator → Layout → SVG → PNG), and returns the PNG.

The existing llama-server remains private on 127.0.0.1:8080.
This API binds to 0.0.0.0:8090 for remote access over Radmin VPN.

Usage:
    python api.py
    python api.py --host 0.0.0.0 --port 8090
"""

import argparse
import json
import logging
import os
import sys
import time
import threading
import urllib.request
import uuid
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, Field

# ─── Ensure project directory is on sys.path ─────────────────────────────
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from config import LLAMA_API_URL, RESULTS_DIR, RESULTS_PNG_DIR
from llm import generate_infographic_json
from validator import validate_infographic_data, ValidationError
from layout import do_layout
from renderer import render_svg
from generate import convert_svg_to_png, sanitize_filename

# ─── Logging ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("diagram-api")

# ─── Configuration ────────────────────────────────────────────────────────
API_HOST = os.environ.get("DIAGRAM_API_HOST", "0.0.0.0")
API_PORT = int(os.environ.get("DIAGRAM_API_PORT", "8090"))

# ─── Concurrency Lock ────────────────────────────────────────────────────
# The local llama-server processes one request at a time.
# Serialize generation requests to prevent model interference.
_generation_lock = threading.Lock()

# ─── FastAPI App ──────────────────────────────────────────────────────────
app = FastAPI(
    title="LatenightPipeline Diagram API",
    description="Remote diagram generation service",
    version="1.0.0",
)


# ─── Request / Response Models ────────────────────────────────────────────

class GenerateRequest(BaseModel):
    request_id: Optional[str] = Field(
        default=None,
        description="Optional tracing ID. Auto-generated if omitted.",
    )
    topic: str = Field(
        ...,
        min_length=1,
        description="The diagram topic/instruction.",
    )
    context: Optional[str] = Field(
        default="",
        description="Additional context for the diagram generation.",
    )
    output_format: Optional[str] = Field(
        default="png",
        description="Output format. Currently supports: png.",
    )


# ─── Helper: check llama-server health ────────────────────────────────────

def _check_llama_server() -> bool:
    """Ping the local llama-server to see if it's reachable."""
    # llama-server exposes a GET /health endpoint
    health_url = LLAMA_API_URL.rsplit("/", 1)[0] + "/health"
    try:
        req = urllib.request.Request(health_url, method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status == 200
    except Exception:
        return False


# ─── Endpoints ────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def root_page():
    """Browser-friendly status page."""
    llama_ok = _check_llama_server()
    llama_status = "🟢 Reachable" if llama_ok else "🔴 Unreachable"
    return f"""<!DOCTYPE html>
<html>
<head>
    <title>LatenightPipeline Diagram Service</title>
    <style>
        body {{
            font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
            max-width: 640px; margin: 60px auto; padding: 0 24px;
            background: #F8FAFC; color: #1E293B;
        }}
        h1 {{ color: #3B82F6; margin-bottom: 4px; }}
        .subtitle {{ color: #64748B; margin-bottom: 32px; }}
        .card {{
            background: white; border: 1px solid #E2E8F0;
            border-radius: 12px; padding: 20px 24px; margin-bottom: 16px;
            box-shadow: 0 1px 3px rgba(15,23,42,0.06);
        }}
        .card h3 {{ margin-top: 0; color: #475569; }}
        code {{
            background: #F1F5F9; padding: 2px 8px; border-radius: 4px;
            font-size: 14px;
        }}
        .status {{ font-size: 18px; font-weight: 600; }}
        .green {{ color: #10B981; }}
    </style>
</head>
<body>
    <h1>LatenightPipeline</h1>
    <p class="subtitle">Diagram Generation Service</p>

    <div class="card">
        <h3>Service Status</h3>
        <p class="status green">🟢 Online</p>
        <p>Local LLM Server (llama-server): {llama_status}</p>
    </div>

    <div class="card">
        <h3>API Endpoints</h3>
        <p><code>POST /v1/generate</code> — Generate a diagram (returns PNG)</p>
        <p><code>GET  /health</code> — Health check (JSON)</p>
    </div>

    <div class="card">
        <h3>Example Request</h3>
        <pre style="background:#F1F5F9;padding:12px;border-radius:8px;font-size:13px;overflow-x:auto;">POST /v1/generate
Content-Type: application/json

{{
  "topic": "How DNS Works",
  "context": "",
  "output_format": "png"
}}</pre>
    </div>
</body>
</html>"""


@app.get("/health")
async def health_check():
    """JSON health endpoint."""
    llama_ok = _check_llama_server()
    return {
        "status": "ok",
        "service": "latenight-diagram",
        "llama_server": "reachable" if llama_ok else "unreachable",
        "llama_server_url": LLAMA_API_URL,
    }


@app.post("/v1/generate")
async def generate_diagram(req: GenerateRequest):
    """
    Generate a diagram from a topic and return the PNG image directly.

    The full pipeline runs: LLM → GBNF → Validator → Layout → SVG → PNG.
    """
    # ── Validate request ──────────────────────────────────────────────
    topic = req.topic.strip()
    if not topic:
        raise HTTPException(status_code=400, detail="Topic cannot be empty.")

    request_id = req.request_id or str(uuid.uuid4())[:12]
    context = (req.context or "").strip()

    # Build the effective topic string.
    # If context is provided, prepend it so the LLM sees it alongside the topic.
    if context:
        effective_topic = f"{topic}\n\nContext:\n{context}"
    else:
        effective_topic = topic

    logger.info(f"[{request_id}] Received request — topic: {topic!r}")
    start_time = time.time()

    # ── Check llama-server availability ───────────────────────────────
    if not _check_llama_server():
        logger.error(f"[{request_id}] llama-server unreachable at {LLAMA_API_URL}")
        raise HTTPException(
            status_code=503,
            detail=f"Local LLM server unreachable at {LLAMA_API_URL}. "
                   f"Ensure llama-server is running.",
        )

    # ── Create request-specific output directory ──────────────────────
    request_output_dir = os.path.join(RESULTS_PNG_DIR, request_id)
    os.makedirs(request_output_dir, exist_ok=True)
    os.makedirs(RESULTS_DIR, exist_ok=True)

    filename_base = sanitize_filename(topic)
    svg_path = os.path.join(request_output_dir, f"{filename_base}.svg")
    png_path = os.path.join(request_output_dir, f"{filename_base}.png")

    # ── Run pipeline (serialized) ─────────────────────────────────────
    acquired = _generation_lock.acquire(timeout=120)
    if not acquired:
        logger.error(f"[{request_id}] Timed out waiting for generation lock")
        raise HTTPException(
            status_code=503,
            detail="Server busy. Another diagram is being generated. Try again shortly.",
        )

    try:
        # 1. LLM generation
        logger.info(f"[{request_id}] Calling LLM for topic: {topic!r}")
        try:
            json_str = generate_infographic_json(effective_topic)
        except RuntimeError as e:
            err_msg = str(e)
            if "Failed to connect" in err_msg:
                raise HTTPException(status_code=503, detail=f"LLM server error: {err_msg}")
            raise HTTPException(status_code=500, detail=f"LLM generation failed: {err_msg}")

        # 2. Validate
        logger.info(f"[{request_id}] Validating JSON output")
        try:
            data = validate_infographic_data(json_str)
        except ValidationError as e:
            raise HTTPException(status_code=500, detail=f"Validation error: {e}")

        # 3. Layout
        logger.info(f"[{request_id}] Calculating layout")
        layout = do_layout(data)

        # 4. Render SVG
        logger.info(f"[{request_id}] Rendering SVG")
        svg_content = render_svg(data, layout, debug=False)
        with open(svg_path, "w", encoding="utf-8") as f:
            f.write(svg_content)

        # 5. Convert to PNG
        logger.info(f"[{request_id}] Converting SVG → PNG")
        convert_svg_to_png(svg_path, png_path)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"[{request_id}] Unexpected error during generation")
        raise HTTPException(status_code=500, detail=f"Diagram generation failed: {e}")
    finally:
        _generation_lock.release()

    # ── Return PNG ────────────────────────────────────────────────────
    elapsed = time.time() - start_time
    logger.info(
        f"[{request_id}] ✓ Complete in {elapsed:.1f}s — "
        f"SVG: {svg_path} | PNG: {png_path}"
    )

    if not os.path.exists(png_path):
        raise HTTPException(status_code=500, detail="PNG file was not produced.")

    with open(png_path, "rb") as f:
        png_bytes = f.read()

    return Response(
        content=png_bytes,
        media_type="image/png",
        headers={
            "X-Request-ID": request_id,
            "X-Diagram-Topic": topic[:80],
        },
    )


# ─── Main ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LatenightPipeline Diagram API")
    parser.add_argument("--host", type=str, default=API_HOST,
                        help=f"Bind host (default: {API_HOST})")
    parser.add_argument("--port", type=int, default=API_PORT,
                        help=f"Bind port (default: {API_PORT})")
    args = parser.parse_args()

    import uvicorn

    logger.info(f"Starting Diagram API on {args.host}:{args.port}")
    logger.info(f"LLM server: {LLAMA_API_URL}")
    logger.info(f"SVG output: {RESULTS_DIR}")
    logger.info(f"PNG output: {RESULTS_PNG_DIR}")

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
