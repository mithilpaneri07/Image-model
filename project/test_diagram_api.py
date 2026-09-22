"""
Simple integration test for the LatenightPipeline Diagram API.

Usage:
    1. Start the API:    python api.py
    2. Run this test:    python test_diagram_api.py

Optionally pass a custom URL:
    python test_diagram_api.py http://26.182.86.104:8090
"""

import json
import sys
import urllib.request

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8090"

def test_root():
    """GET / should return an HTML status page."""
    print("─── Test: GET / ───")
    req = urllib.request.Request(f"{BASE_URL}/")
    with urllib.request.urlopen(req, timeout=5) as resp:
        assert resp.status == 200, f"Expected 200, got {resp.status}"
        body = resp.read().decode("utf-8")
        assert "LatenightPipeline" in body, "Status page missing expected content"
    print("  PASS: Status page returned\n")

def test_health():
    """GET /health should return JSON with status=ok."""
    print("─── Test: GET /health ───")
    req = urllib.request.Request(f"{BASE_URL}/health")
    with urllib.request.urlopen(req, timeout=5) as resp:
        assert resp.status == 200, f"Expected 200, got {resp.status}"
        data = json.loads(resp.read().decode("utf-8"))
        assert data["status"] == "ok", f"Expected status=ok, got {data['status']}"
        assert data["service"] == "latenight-diagram"
    print(f"  PASS: status={data['status']}, llama={data.get('llama_server')}\n")

def test_generate_png():
    """POST /v1/generate should return a PNG image."""
    print("─── Test: POST /v1/generate ───")
    payload = json.dumps({
        "topic": "How DNS Works",
        "context": "",
        "output_format": "png"
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{BASE_URL}/v1/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
    )

    print("  Sending request (this may take 10-30s for LLM generation)...")
    with urllib.request.urlopen(req, timeout=120) as resp:
        assert resp.status == 200, f"Expected 200, got {resp.status}"

        content_type = resp.headers.get("Content-Type", "")
        assert "image/png" in content_type, f"Expected image/png, got {content_type}"

        png_bytes = resp.read()
        # PNG files start with the magic bytes: 0x89 P N G
        assert png_bytes[:4] == b"\x89PNG", "Response does not start with PNG magic bytes"

        request_id = resp.headers.get("X-Request-ID", "unknown")

    print(f"  PASS: Received valid PNG ({len(png_bytes)} bytes), request_id={request_id}")

    # Optionally save to disk for manual inspection
    out_path = "test_output.png"
    with open(out_path, "wb") as f:
        f.write(png_bytes)
    print(f"  Saved to {out_path}\n")

def test_empty_topic():
    """POST /v1/generate with empty topic should return 422."""
    print("─── Test: POST /v1/generate (empty topic) ───")
    payload = json.dumps({"topic": ""}).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}/v1/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        urllib.request.urlopen(req, timeout=10)
        print("  FAIL: Expected error, got 200\n")
    except urllib.error.HTTPError as e:
        assert e.code in (400, 422), f"Expected 400/422, got {e.code}"
        print(f"  PASS: Correctly rejected with HTTP {e.code}\n")


if __name__ == "__main__":
    print(f"\n{'='*50}")
    print(f"LatenightPipeline Diagram API Test")
    print(f"Target: {BASE_URL}")
    print(f"{'='*50}\n")

    try:
        test_root()
        test_health()
        test_empty_topic()
        test_generate_png()
        print("="*50)
        print("ALL TESTS PASSED ✓")
        print("="*50)
    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        sys.exit(1)
