"""
Renderer: translates validated data and computed layout into a high-quality SVG infographic.

Key features:
- Box-based typography layout (no text clipping or overlapping)
- Content vertically and horizontally centered in element bounding boxes
- Shape-aware content insetting (circles and diamonds restrict content area)
- Modern design system with drop shadows, linear gradients, and clean card styling
- Support for --debug bounding box and region visualization
"""

import math
import textwrap
from xml.sax.saxutils import escape
from typing import Dict, Any, List, Optional, Tuple

from config import (
    CANVAS_WIDTH, CANVAS_HEIGHT, COLORS, FONT_FAMILY,
    TYPESCALE, ELEMENT_PADDING,
)
from layout import LayoutResult, ElementBox, PageRegions, Rect
from icons import get_icon_svg


def _wrap_text(text: str, max_chars: int, max_lines: int) -> List[str]:
    """Wrap text to max_chars per line, capped at max_lines with ellipsis."""
    if not text:
        return []
    lines = textwrap.wrap(text, width=max_chars)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        if len(lines[-1]) > max_chars - 3:
            lines[-1] = lines[-1][:max_chars - 3] + "..."
        else:
            lines[-1] += "..."
    return lines


def _draw_shape_svg(box: ElementBox, fill: str, stroke: str, filter_id: Optional[str] = None) -> str:
    """Draw the SVG element shape matching box coordinates and dimensions."""
    x = box.x - box.width / 2
    y = box.y - box.height / 2
    w = box.width
    h = box.height
    filt = f'filter="url(#{filter_id})"' if filter_id else ''

    if box.shape == "rectangle":
        return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="6" fill="{fill}" stroke="{stroke}" stroke-width="1.5" {filt}/>'
    elif box.shape == "rounded_rectangle":
        return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="12" fill="{fill}" stroke="{stroke}" stroke-width="1.5" {filt}/>'
    elif box.shape == "pill":
        rx = min(w, h) / 2
        return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx:.1f}" fill="{fill}" stroke="{stroke}" stroke-width="1.5" {filt}/>'
    elif box.shape == "circle":
        r = min(w, h) / 2
        return f'<circle cx="{box.x:.1f}" cy="{box.y:.1f}" r="{r:.1f}" fill="{fill}" stroke="{stroke}" stroke-width="1.5" {filt}/>'
    elif box.shape == "diamond":
        points = f"{box.x:.1f},{y:.1f} {box.x + w/2:.1f},{box.y:.1f} {box.x:.1f},{box.y + h/2:.1f} {x:.1f},{box.y:.1f}"
        return f'<polygon points="{points}" fill="{fill}" stroke="{stroke}" stroke-width="1.5" {filt}/>'
    elif box.shape == "hexagon":
        pts = [
            f"{box.x - w * 0.32:.1f},{y:.1f}",
            f"{box.x + w * 0.32:.1f},{y:.1f}",
            f"{box.x + w / 2:.1f},{box.y:.1f}",
            f"{box.x + w * 0.32:.1f},{box.y + h/2:.1f}",
            f"{box.x - w * 0.32:.1f},{box.y + h/2:.1f}",
            f"{x:.1f},{box.y:.1f}",
        ]
        return f'<polygon points="{" ".join(pts)}" fill="{fill}" stroke="{stroke}" stroke-width="1.5" {filt}/>'
    else:
        # Default fallback: rounded rectangle
        return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="8" fill="{fill}" stroke="{stroke}" stroke-width="1.5" {filt}/>'


def _get_shape_usable_bounds(box: ElementBox) -> Tuple[float, float]:
    """Calculate the safe inner text width and height for a given shape."""
    w, h = box.width, box.height
    if box.shape == "circle":
        r = min(w, h) / 2
        return r * 1.35, r * 1.35
    elif box.shape == "diamond":
        return w * 0.58, h * 0.58
    elif box.shape == "hexagon":
        return w * 0.68, h * 0.72
    elif box.shape == "pill":
        return max(40.0, w - 36), max(20.0, h - 20)
    else:  # rectangle or rounded_rectangle
        return max(40.0, w - 24), max(20.0, h - 20)


def render_element(el: Dict[str, Any], box: ElementBox) -> List[str]:
    """Renders a single element (shape, icon, title, and body text)."""
    svg = []
    emphasis = el.get("emphasis", "normal")

    if emphasis == "primary":
        fill = "url(#grad-primary)"
        stroke = "#1D4ED8"
        text_title_col = "#FFFFFF"
        text_body_col = "rgba(255, 255, 255, 0.92)"
        icon_col = "#FFFFFF"
        filter_id = "card-shadow-hover"
    elif emphasis == "highlighted":
        fill = "url(#grad-highlight)"
        stroke = "#B45309"
        text_title_col = "#FFFFFF"
        text_body_col = "rgba(255, 255, 255, 0.92)"
        icon_col = "#FFFFFF"
        filter_id = "card-shadow-hover"
    elif emphasis == "secondary":
        fill = "#F8FAFC"
        stroke = "#CBD5E1"
        text_title_col = COLORS["text_primary"]
        text_body_col = COLORS["text_secondary"]
        icon_col = COLORS["secondary"]
        filter_id = "card-shadow"
    else:  # normal
        fill = "#FFFFFF"
        stroke = "#E2E8F0"
        text_title_col = COLORS["text_primary"]
        text_body_col = COLORS["text_secondary"]
        icon_col = COLORS["accent"]
        filter_id = "card-shadow"

    # 1. Draw shape with drop shadow
    svg.append(f'  <g id="element-{el["id"]}">' )
    svg.append("    " + _draw_shape_svg(box, fill, stroke, filter_id))

    # 2. Compute inner dimensions
    usable_w, usable_h = _get_shape_usable_bounds(box)

    # 3. Calculate icon dimensions
    icon_name = el.get("icon")
    has_icon = bool(icon_name and icon_name != "none")
    icon_size = 24.0
    icon_gap = 6.0
    icon_h = (icon_size + icon_gap) if has_icon else 0.0

    # 4. Wrap Title
    title_text = el.get("title", "")
    title_font_size = 14
    title_line_h = 18.0
    chars_per_title_line = max(6, int(usable_w / 8.2))
    title_lines = _wrap_text(title_text, chars_per_title_line, max_lines=2)
    title_h = len(title_lines) * title_line_h

    # 5. Wrap Body Text
    body_text = el.get("text", "")
    body_font_size = 11
    body_line_h = 15.0
    chars_per_body_line = max(8, int(usable_w / 6.2))

    available_body_h = usable_h - icon_h - title_h - (6.0 if (title_lines and body_text) else 0.0)
    max_body_lines = max(1, min(4, int(available_body_h / body_line_h)))
    body_lines = _wrap_text(body_text, chars_per_body_line, max_lines=max_body_lines) if body_text else []
    body_h = len(body_lines) * body_line_h

    gap_between_title_body = 6.0 if (title_lines and body_lines) else 0.0

    # 6. Center content block vertically
    total_content_h = icon_h + title_h + gap_between_title_body + body_h
    curr_y = box.y - (total_content_h / 2.0)

    # 7. Render Icon
    if has_icon:
        icon_x = box.x - (icon_size / 2.0)
        icon_y = curr_y
        svg.append("    " + get_icon_svg(icon_name, icon_x, icon_y, icon_size, icon_col))
        curr_y += icon_h

    # 8. Render Title
    if title_lines:
        for line in title_lines:
            baseline = curr_y + (title_font_size * 0.82)
            svg.append(
                f'    <text x="{box.x:.1f}" y="{baseline:.1f}" '
                f'font-family="{FONT_FAMILY}" font-size="{title_font_size}" font-weight="700" '
                f'fill="{text_title_col}" text-anchor="middle">{escape(line)}</text>'
            )
            curr_y += title_line_h

    # 9. Render Body
    if body_lines:
        curr_y += gap_between_title_body
        for line in body_lines:
            baseline = curr_y + (body_font_size * 0.82)
            svg.append(
                f'    <text x="{box.x:.1f}" y="{baseline:.1f}" '
                f'font-family="{FONT_FAMILY}" font-size="{body_font_size}" font-weight="400" '
                f'fill="{text_body_col}" text-anchor="middle">{escape(line)}</text>'
            )
            curr_y += body_line_h

    svg.append('  </g>')
    return svg


def render_svg(data: Dict[str, Any], layout: LayoutResult, debug: bool = False) -> str:
    """Main SVG rendering function."""
    svg = []
    svg.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {CANVAS_WIDTH} {CANVAS_HEIGHT}" '
        f'width="{CANVAS_WIDTH}" height="{CANVAS_HEIGHT}">'
    )

    # Defs: gradients, filters, markers
    svg.append('  <defs>')
    # Drop shadow
    svg.append('    <filter id="card-shadow" x="-10%" y="-10%" width="125%" height="130%">')
    svg.append('      <feDropShadow dx="0" dy="3" stdDeviation="5" flood-color="#0F172A" flood-opacity="0.06"/>')
    svg.append('    </filter>')
    svg.append('    <filter id="card-shadow-hover" x="-10%" y="-10%" width="125%" height="130%">')
    svg.append('      <feDropShadow dx="0" dy="6" stdDeviation="10" flood-color="#0F172A" flood-opacity="0.12"/>')
    svg.append('    </filter>')
    # Linear gradients
    svg.append('    <linearGradient id="grad-bg" x1="0%" y1="0%" x2="0%" y2="100%">')
    svg.append('      <stop offset="0%" stop-color="#F8FAFC"/>')
    svg.append('      <stop offset="100%" stop-color="#EDF2F7"/>')
    svg.append('    </linearGradient>')
    svg.append('    <linearGradient id="grad-primary" x1="0%" y1="0%" x2="100%" y2="100%">')
    svg.append('      <stop offset="0%" stop-color="#3B82F6"/>')
    svg.append('      <stop offset="100%" stop-color="#1D4ED8"/>')
    svg.append('    </linearGradient>')
    svg.append('    <linearGradient id="grad-highlight" x1="0%" y1="0%" x2="100%" y2="100%">')
    svg.append('      <stop offset="0%" stop-color="#F59E0B"/>')
    svg.append('      <stop offset="100%" stop-color="#D97706"/>')
    svg.append('    </linearGradient>')
    # Arrowhead marker
    svg.append(
        f'    <marker id="arrowhead" markerWidth="9" markerHeight="7" refX="7" refY="3.5" orient="auto">'
        f'<polygon points="0 0, 9 3.5, 0 7" fill="{COLORS["connector_arrow"]}"/></marker>'
    )
    svg.append('  </defs>')

    # 1. Background
    svg.append(f'  <rect width="100%" height="100%" fill="url(#grad-bg)" />')

    # Subtle decorative top accent bar
    svg.append(f'  <rect x="0" y="0" width="100%" height="4" fill="{COLORS["accent"]}" />')

    # 2. Header
    header = layout.regions.header
    title = escape(data.get("title", ""))
    subtitle = escape(data.get("subtitle", ""))

    if subtitle:
        title_y = header.y + 36
        sub_y = title_y + 30
        svg.append(
            f'  <text x="{header.cx:.1f}" y="{title_y:.1f}" font-family="{FONT_FAMILY}" '
            f'font-size="{TYPESCALE["title"].size}" font-weight="{TYPESCALE["title"].weight}" '
            f'fill="{COLORS["text_primary"]}" text-anchor="middle" letter-spacing="-0.5">{title}</text>'
        )
        svg.append(
            f'  <text x="{header.cx:.1f}" y="{sub_y:.1f}" font-family="{FONT_FAMILY}" '
            f'font-size="{TYPESCALE["subtitle"].size}" font-weight="{TYPESCALE["subtitle"].weight}" '
            f'fill="{COLORS["text_secondary"]}" text-anchor="middle">{subtitle}</text>'
        )
    else:
        title_y = header.cy + 10
        svg.append(
            f'  <text x="{header.cx:.1f}" y="{title_y:.1f}" font-family="{FONT_FAMILY}" '
            f'font-size="{TYPESCALE["title"].size}" font-weight="{TYPESCALE["title"].weight}" '
            f'fill="{COLORS["text_primary"]}" text-anchor="middle" letter-spacing="-0.5">{title}</text>'
        )

    # 3. Stats Bar
    stats = data.get("stats", [])
    if layout.regions.stats and stats:
        stats_reg = layout.regions.stats
        n = len(stats)
        card_w = min(220.0, max(140.0, (stats_reg.w - (n - 1) * 20.0) / n))
        card_h = 58.0
        total_w = n * card_w + (n - 1) * 20.0
        start_x = stats_reg.cx - (total_w / 2.0)
        card_y = stats_reg.cy - (card_h / 2.0)

        for i, stat in enumerate(stats):
            scx = start_x + i * (card_w + 20.0) + (card_w / 2.0)
            sc_left = start_x + i * (card_w + 20.0)
            val = escape(str(stat.get("value", "")))
            lbl = escape(str(stat.get("label", "")))

            # Mini stat card
            svg.append(
                f'  <rect x="{sc_left:.1f}" y="{card_y:.1f}" width="{card_w:.1f}" height="{card_h:.1f}" '
                f'rx="8" fill="#FFFFFF" stroke="#E2E8F0" stroke-width="1" filter="url(#card-shadow)" />'
            )
            val_len = len(val)
            if val_len > 14:
                val_font_size = 13
                val_y = card_y + 24
            elif val_len > 9:
                val_font_size = 16
                val_y = card_y + 25
            else:
                val_font_size = 22
                val_y = card_y + 26

            lbl_font_size = 11 if len(lbl) > 15 else 12
            lbl_y = card_y + 46

            svg.append(
                f'  <text x="{scx:.1f}" y="{val_y:.1f}" font-family="{FONT_FAMILY}" '
                f'font-size="{val_font_size}" font-weight="700" '
                f'fill="{COLORS["accent_dark"]}" text-anchor="middle">{val}</text>'
            )
            svg.append(
                f'  <text x="{scx:.1f}" y="{lbl_y:.1f}" font-family="{FONT_FAMILY}" '
                f'font-size="{lbl_font_size}" font-weight="600" '
                f'fill="{COLORS["text_secondary"]}" text-anchor="middle" letter-spacing="0.5">{lbl}</text>'
            )

    # 4. Connectors (drawn behind elements)
    svg.append('  <g id="connectors">')
    for conn in layout.connectors:
        x1, y1 = conn["x1"], conn["y1"]
        x2, y2 = conn["x2"], conn["y2"]
        ctype = conn.get("type", "arrow")

        # Skip degenerate lines
        if math.hypot(x2 - x1, y2 - y1) < 8:
            continue

        dash = 'stroke-dasharray="6,6"' if ctype == "dashed_arrow" else ''
        marker = 'marker-end="url(#arrowhead)"' if ctype in ("arrow", "dashed_arrow") else ''

        # Connector start dot
        svg.append(f'    <circle cx="{x1:.1f}" cy="{y1:.1f}" r="3.5" fill="{COLORS["connector_arrow"]}"/>')
        # Connector line
        svg.append(
            f'    <line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{COLORS["connector"]}" stroke-width="2" {dash} {marker} />'
        )
    svg.append('  </g>')

    # 5. Elements
    svg.append('  <g id="elements">')
    for el_raw in data.get("elements", []):
        el_id = el_raw["id"]
        if el_id in layout.elements:
            box = layout.elements[el_id]
            svg.extend(render_element(el_raw, box))
    svg.append('  </g>')

    # 6. Footer
    footer = escape(data.get("footer", ""))
    if footer:
        footer_reg = layout.regions.footer
        svg.append(
            f'  <text x="{footer_reg.cx:.1f}" y="{footer_reg.cy:.1f}" font-family="{FONT_FAMILY}" '
            f'font-size="{TYPESCALE["footer"].size}" fill="{COLORS["text_muted"]}" text-anchor="middle">{footer}</text>'
        )

    # 7. Debug Visual Guides
    if debug:
        svg.append('  <!-- DEBUG GUIDES -->')
        # Region bounding boxes
        regs = [
            ("Header", layout.regions.header, "#EF4444"),
            ("Content", layout.regions.content, "#10B981"),
            ("Footer", layout.regions.footer, "#F59E0B"),
        ]
        if layout.regions.stats:
            regs.append(("Stats", layout.regions.stats, "#3B82F6"))

        for name, r, stroke in regs:
            svg.append(
                f'  <rect x="{r.x:.1f}" y="{r.y:.1f}" width="{r.w:.1f}" height="{r.h:.1f}" '
                f'fill="none" stroke="{stroke}" stroke-width="1.5" stroke-dasharray="4,4"/>'
            )
            svg.append(
                f'  <text x="{r.x + 8:.1f}" y="{r.y + 16:.1f}" font-family="{FONT_FAMILY}" '
                f'font-size="12" font-weight="bold" fill="{stroke}">[{name}]</text>'
            )

        # Element bounding boxes
        for eid, box in layout.elements.items():
            r = box.rect
            svg.append(
                f'  <rect x="{r.x:.1f}" y="{r.y:.1f}" width="{r.w:.1f}" height="{r.h:.1f}" '
                f'fill="none" stroke="#EC4899" stroke-width="1" stroke-dasharray="2,2"/>'
            )
            svg.append(
                f'  <text x="{r.x + 4:.1f}" y="{r.y + 12:.1f}" font-family="{FONT_FAMILY}" '
                f'font-size="10" fill="#EC4899">{eid} ({int(box.width)}x{int(box.height)})</text>'
            )

    svg.append('</svg>')
    return "\n".join(svg)
