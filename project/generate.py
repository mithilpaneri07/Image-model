import argparse
import os
import re
import sys
from config import RESULTS_DIR, RESULTS_PNG_DIR
from llm import generate_infographic_json
from validator import validate_infographic_data, ValidationError
from layout import do_layout
from renderer import render_svg

def sanitize_filename(topic: str) -> str:
    # Convert spaces and invalid characters to dashes
    clean = re.sub(r'[^a-zA-Z0-9]+', '-', topic).strip('-').lower()
    if not clean:
        clean = "infographic"
    # Limit length
    return clean[:50]

def convert_svg_to_png(svg_path: str, png_path: str):
    """Convert an SVG file to PNG using resvg-py (fast, cross-platform) or CairoSVG fallback."""
    try:
        import resvg_py
        png_bytes = resvg_py.svg_to_bytes(svg_path=svg_path)
        with open(png_path, "wb") as f:
            f.write(png_bytes)
        return
    except ImportError:
        pass
    except Exception as e:
        print(f"Warning: resvg-py failed ({e}), attempting CairoSVG fallback...", file=sys.stderr)

    try:
        import cairosvg
        cairosvg.svg2png(url=svg_path, write_to=png_path)
        return
    except ImportError:
        raise RuntimeError("PNG conversion engine missing. Install resvg-py: pip install resvg-py")
    except Exception as e:
        raise RuntimeError(f"Error converting to PNG: {e}")

def main():
    parser = argparse.ArgumentParser(description="AI SVG & PNG Infographic Generator")
    parser.add_argument("topic", type=str, help="The topic for the infographic")
    parser.add_argument("--png", action="store_true", help="Included for backwards-compatibility; PNGs are now generated automatically")
    parser.add_argument("--no-png", action="store_true", help="Skip automatic PNG conversion")
    parser.add_argument("--debug", action="store_true", help="Render bounding box and layout debug guides")
    
    args = parser.parse_args()
    
    if not args.topic.strip():
        print("Error: Topic cannot be empty.", file=sys.stderr)
        sys.exit(1)
        
    os.makedirs(RESULTS_DIR, exist_ok=True)
    os.makedirs(RESULTS_PNG_DIR, exist_ok=True)
    filename_base = sanitize_filename(args.topic)
    svg_filename = f"{filename_base}-debug.svg" if args.debug else f"{filename_base}.svg"
    svg_path = os.path.join(RESULTS_DIR, svg_filename)
    
    print(f"Generating infographic for topic: '{args.topic}'...")
    
    try:
        json_str = generate_infographic_json(args.topic)
    except Exception as e:
        print(f"Error during LLM generation: {e}", file=sys.stderr)
        sys.exit(1)
        
    if args.debug:
        print(f"[DEBUG] Raw LLM output:\n{json_str}")
        
    print("Validating JSON output...")
    try:
        data = validate_infographic_data(json_str)
    except ValidationError as e:
        print(f"Validation Error: {e}", file=sys.stderr)
        sys.exit(1)
        
    print("Calculating layout...")
    layout = do_layout(data)
    if args.debug:
        print(f"[DEBUG] Layout type: {data.get('layout')}")
        print(f"[DEBUG] Elements placed: {len(layout.elements)}")
        for eid, box in layout.elements.items():
            print(f"  - {eid}: center=({box.x:.1f}, {box.y:.1f}), size={box.width:.1f}x{box.height:.1f}, shape={box.shape}")
        print(f"[DEBUG] Connectors: {len(layout.connectors)}")
    
    print("Rendering SVG...")
    svg_content = render_svg(data, layout, debug=args.debug)
    
    with open(svg_path, "w", encoding="utf-8") as f:
        f.write(svg_content)
        
    print(f"Saved SVG to {svg_path}")
    
    # Always generate PNG unless explicitly skipped
    if not args.no_png:
        png_filename = f"{filename_base}-debug.png" if args.debug else f"{filename_base}.png"
        png_path = os.path.join(RESULTS_PNG_DIR, png_filename)
        print("Converting SVG to PNG...")
        try:
            convert_svg_to_png(svg_path, png_path)
            print(f"Saved PNG to {png_path}")
        except Exception as e:
            print(f"Error converting to PNG: {e}", file=sys.stderr)
            sys.exit(1)
            
if __name__ == "__main__":
    main()
