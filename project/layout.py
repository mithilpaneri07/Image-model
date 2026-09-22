"""
Layout engine: deterministic coordinate calculation for infographic composition.

The LLM chooses WHAT to show and HOW to compose it (layout type, shapes, emphasis).
This module decides WHERE everything goes (coordinates, dimensions, spacing).

Key principles:
- Every visible element has an explicit bounding box
- No hardcoded y-offsets; regions are calculated from content
- Multi-row reflow when elements don't fit in one row
- Collision detection after placement
- Content-aware element sizing
"""

import math
from dataclasses import dataclass, field
from typing import List, Dict, Any, Tuple, Optional
from config import (
    CANVAS_WIDTH, CANVAS_HEIGHT,
    MARGIN_TOP, MARGIN_BOTTOM, MARGIN_LEFT, MARGIN_RIGHT,
    SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL,
    ELEMENT_SIZES, ELEMENT_PADDING, TYPESCALE,
)


# ─── Data Structures ─────────────────────────────────────────────────────

@dataclass
class Rect:
    """An axis-aligned rectangle defined by its top-left corner and size."""
    x: float
    y: float
    w: float
    h: float

    @property
    def cx(self) -> float: return self.x + self.w / 2
    @property
    def cy(self) -> float: return self.y + self.h / 2
    @property
    def right(self) -> float: return self.x + self.w
    @property
    def bottom(self) -> float: return self.y + self.h

    def intersects(self, other: "Rect") -> bool:
        return not (self.right <= other.x or other.right <= self.x or
                    self.bottom <= other.y or other.bottom <= self.y)

    def pad(self, p: float) -> "Rect":
        return Rect(self.x - p, self.y - p, self.w + 2*p, self.h + 2*p)


@dataclass
class ElementBox:
    """Bounding box for one infographic element. x,y is the CENTER."""
    id: str
    x: float       # center x
    y: float       # center y
    width: float
    height: float
    shape: str

    @property
    def rect(self) -> Rect:
        return Rect(self.x - self.width/2, self.y - self.height/2,
                    self.width, self.height)


@dataclass
class ConnectorAnchor:
    x: float
    y: float


@dataclass
class PageRegions:
    """Calculated vertical regions of the infographic canvas."""
    header: Rect       # title + subtitle
    stats: Optional[Rect]   # optional stats bar
    content: Rect      # main element area
    footer: Rect       # footer text


@dataclass
class LayoutResult:
    elements: Dict[str, ElementBox]
    connectors: List[Dict[str, Any]]
    regions: PageRegions


# ─── Page Region Calculation ──────────────────────────────────────────────

def _calculate_regions(data: Dict[str, Any]) -> PageRegions:
    """Calculate page regions dynamically based on content presence."""
    usable_left = MARGIN_LEFT
    usable_width = CANVAS_WIDTH - MARGIN_LEFT - MARGIN_RIGHT

    # Header: title + subtitle
    header_h = 80  # title ~38px + subtitle ~18px + spacing
    if not data.get("subtitle"):
        header_h = 55
    header = Rect(usable_left, MARGIN_TOP, usable_width, header_h)

    # Footer
    footer_h = 35
    footer_y = CANVAS_HEIGHT - MARGIN_BOTTOM - footer_h
    footer = Rect(usable_left, footer_y, usable_width, footer_h)

    # Stats (optional)
    stats_rect = None
    stats = data.get("stats", [])
    current_y = header.bottom + SPACING_MD

    if stats:
        stats_h = 65
        stats_rect = Rect(usable_left, current_y, usable_width, stats_h)
        current_y = stats_rect.bottom + SPACING_MD

    # Content: everything between stats/header and footer
    content_top = current_y + SPACING_SM
    content_bottom = footer.y - SPACING_MD
    content_h = max(200, content_bottom - content_top)
    content = Rect(usable_left, content_top, usable_width, content_h)

    return PageRegions(header=header, stats=stats_rect,
                       content=content, footer=footer)


# ─── Content-Aware Element Sizing ─────────────────────────────────────────

def _estimate_text_lines(text: str, chars_per_line: int) -> int:
    """Estimate how many wrapped lines a text will produce."""
    if not text:
        return 0
    words = text.split()
    lines = 1
    current_len = 0
    for word in words:
        if current_len + len(word) + (1 if current_len > 0 else 0) > chars_per_line:
            lines += 1
            current_len = len(word)
        else:
            current_len += len(word) + (1 if current_len > 0 else 0)
    return lines


def _calculate_element_size(el: Dict[str, Any], shape: str) -> Tuple[float, float]:
    """Calculate element dimensions based on size hint + content."""
    size_key = el.get("size", "medium")
    min_w, pref_w, min_h, pref_h = ELEMENT_SIZES.get(size_key, ELEMENT_SIZES["medium"])

    title = el.get("title", "")
    body = el.get("text", "")

    # Estimate required width from title
    title_chars = len(title)
    title_font = TYPESCALE["element_title"].size
    estimated_title_w = title_chars * title_font * 0.6 + ELEMENT_PADDING * 2
    w = max(min_w, min(pref_w, estimated_title_w))

    # Estimate required height from body text lines
    chars_per_line = max(10, int((w - ELEMENT_PADDING * 2) / (TYPESCALE["element_body"].size * 0.55)))
    body_lines = _estimate_text_lines(body, chars_per_line)
    body_lines = min(body_lines, 4)  # cap at 4 lines

    icon_h = 32 + SPACING_SM  # icon + gap
    title_h = title_font * 1.3
    body_h = body_lines * TYPESCALE["element_body"].size * TYPESCALE["element_body"].line_height
    needed_h = ELEMENT_PADDING + icon_h + title_h + SPACING_SM + body_h + ELEMENT_PADDING

    h = max(min_h, min(pref_h + 30, needed_h))

    # Shape adjustments: circles need w==h, diamonds need more space
    if shape == "circle":
        dim = max(w, h)
        return dim, dim
    elif shape == "diamond":
        # Diamond inscribes content in a rotated square, so needs ~40% more
        return w * 1.3, h * 1.3

    return w, h


# ─── Layout Algorithms ────────────────────────────────────────────────────

def _layout_flow(elements: List[Dict], content: Rect) -> Dict[str, ElementBox]:
    """Horizontal flow with automatic row wrapping."""
    boxes = {}
    n = len(elements)
    if n == 0:
        return boxes

    # Calculate sizes
    sizes = [_calculate_element_size(el, el["shape"]) for el in elements]
    gap = SPACING_LG

    # Determine rows: fit as many as possible per row
    rows: List[List[int]] = []
    current_row: List[int] = []
    current_w = 0

    for i, (w, h) in enumerate(sizes):
        needed = w + (gap if current_row else 0)
        if current_row and current_w + needed > content.w:
            rows.append(current_row)
            current_row = [i]
            current_w = w
        else:
            current_row.append(i)
            current_w += needed
    if current_row:
        rows.append(current_row)

    # Distribute rows vertically
    num_rows = len(rows)
    row_heights = []
    for row in rows:
        row_heights.append(max(sizes[i][1] for i in row))

    total_h = sum(row_heights) + (num_rows - 1) * gap
    start_y = content.cy - total_h / 2

    y_cursor = start_y
    for row_idx, row in enumerate(rows):
        rh = row_heights[row_idx]
        # Total width of this row
        row_total_w = sum(sizes[i][0] for i in row) + (len(row) - 1) * gap
        start_x = content.cx - row_total_w / 2

        x_cursor = start_x
        for i in row:
            w, h = sizes[i]
            cx = x_cursor + w / 2
            cy = y_cursor + rh / 2
            el = elements[i]
            boxes[el["id"]] = ElementBox(el["id"], cx, cy, w, h, el["shape"])
            x_cursor += w + gap

        y_cursor += rh + gap

    return boxes


def _layout_timeline(elements: List[Dict], content: Rect) -> Dict[str, ElementBox]:
    """Timeline: horizontal line with elements alternating above/below."""
    boxes = {}
    n = len(elements)
    if n == 0:
        return boxes

    sizes = [_calculate_element_size(el, el["shape"]) for el in elements]
    gap = SPACING_LG
    total_w = sum(s[0] for s in sizes) + (n - 1) * gap
    scale = min(1.0, content.w / total_w) if total_w > 0 else 1.0

    x_cursor = content.cx - (total_w * scale) / 2
    mid_y = content.cy

    for i, el in enumerate(elements):
        w, h = sizes[i][0] * scale, sizes[i][1] * scale
        w = max(ELEMENT_SIZES["small"][0], w)
        h = max(ELEMENT_SIZES["small"][2], h)
        cx = x_cursor + w / 2
        # Alternate above/below the center line
        offset = (h / 2 + SPACING_LG)
        cy = mid_y - offset if i % 2 == 0 else mid_y + offset
        boxes[el["id"]] = ElementBox(el["id"], cx, cy, w, h, el["shape"])
        x_cursor += w + gap * scale

    return boxes


def _layout_grid(elements: List[Dict], content: Rect) -> Dict[str, ElementBox]:
    """Balanced grid layout."""
    boxes = {}
    n = len(elements)
    if n == 0:
        return boxes

    cols = math.ceil(math.sqrt(n))
    row_count = math.ceil(n / cols)

    sizes = [_calculate_element_size(el, el["shape"]) for el in elements]
    max_w = max(s[0] for s in sizes)
    max_h = max(s[1] for s in sizes)

    gap = SPACING_LG
    grid_w = cols * max_w + (cols - 1) * gap
    grid_h = row_count * max_h + (row_count - 1) * gap

    # Scale down if needed
    scale_x = min(1.0, content.w / grid_w) if grid_w > 0 else 1.0
    scale_y = min(1.0, content.h / grid_h) if grid_h > 0 else 1.0
    scale = min(scale_x, scale_y)

    cell_w = max_w * scale
    cell_h = max_h * scale
    gap_s = gap * scale

    total_w = cols * cell_w + (cols - 1) * gap_s
    total_h = row_count * cell_h + (row_count - 1) * gap_s
    origin_x = content.cx - total_w / 2
    origin_y = content.cy - total_h / 2

    for i, el in enumerate(elements):
        col = i % cols
        row = i // cols
        cx = origin_x + col * (cell_w + gap_s) + cell_w / 2
        cy = origin_y + row * (cell_h + gap_s) + cell_h / 2
        boxes[el["id"]] = ElementBox(el["id"], cx, cy, cell_w, cell_h, el["shape"])

    return boxes


def _layout_two_column(elements: List[Dict], content: Rect) -> Dict[str, ElementBox]:
    """Two balanced columns."""
    boxes = {}
    n = len(elements)
    if n == 0:
        return boxes

    sizes = [_calculate_element_size(el, el["shape"]) for el in elements]
    col_gap = SPACING_XL
    col_w = (content.w - col_gap) / 2

    left_indices = list(range(0, n, 2))
    right_indices = list(range(1, n, 2))

    def place_column(indices, col_cx):
        row_gap = SPACING_LG
        col_heights = [sizes[i][1] for i in indices]
        total_h = sum(col_heights) + max(0, len(indices) - 1) * row_gap
        y_cursor = content.cy - total_h / 2

        for i in indices:
            w = min(sizes[i][0], col_w)
            h = sizes[i][1]
            cy = y_cursor + h / 2
            el = elements[i]
            boxes[el["id"]] = ElementBox(el["id"], col_cx, cy, w, h, el["shape"])
            y_cursor += h + row_gap

    left_cx = content.x + col_w / 2
    right_cx = content.right - col_w / 2
    place_column(left_indices, left_cx)
    place_column(right_indices, right_cx)

    return boxes


def _layout_hub_spoke(elements: List[Dict], content: Rect) -> Dict[str, ElementBox]:
    """Central hub with spokes radiating outward."""
    boxes = {}
    n = len(elements)
    if n == 0:
        return boxes

    sizes = [_calculate_element_size(el, el["shape"]) for el in elements]

    if n == 1:
        w, h = sizes[0]
        boxes[elements[0]["id"]] = ElementBox(
            elements[0]["id"], content.cx, content.cy, w, h, elements[0]["shape"])
        return boxes

    # Hub = first element at center
    hub = elements[0]
    hw, hh = sizes[0]
    boxes[hub["id"]] = ElementBox(hub["id"], content.cx, content.cy, hw, hh, hub["shape"])

    # Spokes
    spoke_count = n - 1
    radius_x = min(content.w / 2 - 80, 320)
    radius_y = min(content.h / 2 - 60, 240)

    for i in range(1, n):
        angle = (i - 1) * (2 * math.pi / spoke_count) - math.pi / 2
        w, h = sizes[i]
        cx = content.cx + radius_x * math.cos(angle)
        cy = content.cy + radius_y * math.sin(angle)
        el = elements[i]
        boxes[el["id"]] = ElementBox(el["id"], cx, cy, w, h, el["shape"])

    return boxes


def _layout_stacked(elements: List[Dict], content: Rect) -> Dict[str, ElementBox]:
    """Vertical stack."""
    boxes = {}
    n = len(elements)
    if n == 0:
        return boxes

    sizes = [_calculate_element_size(el, el["shape"]) for el in elements]
    gap = SPACING_LG
    total_h = sum(s[1] for s in sizes) + (n - 1) * gap
    scale = min(1.0, content.h / total_h) if total_h > 0 else 1.0

    y_cursor = content.cy - (total_h * scale) / 2

    for i, el in enumerate(elements):
        w, h = sizes[i][0], sizes[i][1] * scale
        h = max(ELEMENT_SIZES["small"][2], h)
        w = min(w, content.w * 0.7)  # don't span full width
        cy = y_cursor + h / 2
        boxes[el["id"]] = ElementBox(el["id"], content.cx, cy, w, h, el["shape"])
        y_cursor += h + gap * scale

    return boxes


def _layout_centered(elements: List[Dict], content: Rect) -> Dict[str, ElementBox]:
    """Centered layout with primary element prominent."""
    # Use grid but with wider spacing
    return _layout_grid(elements, content)


def _layout_comparison(elements: List[Dict], content: Rect) -> Dict[str, ElementBox]:
    """Comparison: same as two_column but ensures equal sizing."""
    return _layout_two_column(elements, content)


LAYOUT_DISPATCH = {
    "flow": _layout_flow,
    "timeline": _layout_timeline,
    "grid": _layout_grid,
    "two_column": _layout_two_column,
    "centered": _layout_centered,
    "hub_and_spoke": _layout_hub_spoke,
    "stacked": _layout_stacked,
    "comparison": _layout_comparison,
}


# ─── Connector Anchor Calculation ─────────────────────────────────────────

def _calculate_anchors(box1: ElementBox, box2: ElementBox) -> Tuple[ConnectorAnchor, ConnectorAnchor]:
    """Calculate connector endpoints at the boundary of each element."""
    dx = box2.x - box1.x
    dy = box2.y - box1.y
    dist = math.hypot(dx, dy)

    if dist < 1:
        return ConnectorAnchor(box1.x, box1.y), ConnectorAnchor(box2.x, box2.y)

    dir_x = dx / dist
    dir_y = dy / dist

    def _edge_point(box: ElementBox, dx: float, dy: float) -> ConnectorAnchor:
        hw = box.width / 2 + 4   # +4 padding so arrow doesn't touch shape
        hh = box.height / 2 + 4

        if box.shape == "circle":
            r = min(box.width, box.height) / 2 + 4
            return ConnectorAnchor(box.x + r * dx, box.y + r * dy)

        # For rectangles / diamonds / hexagons: ray-box intersection
        ts = []
        if abs(dx) > 1e-6:
            ts.append(hw / abs(dx))
        if abs(dy) > 1e-6:
            ts.append(hh / abs(dy))
        t = min(ts) if ts else 0
        return ConnectorAnchor(box.x + t * dx, box.y + t * dy)

    p1 = _edge_point(box1, dir_x, dir_y)
    p2 = _edge_point(box2, -dir_x, -dir_y)
    return p1, p2


# ─── Collision Detection ─────────────────────────────────────────────────

def _check_collisions(boxes: Dict[str, ElementBox]) -> List[Tuple[str, str]]:
    """Return list of (id1, id2) pairs whose bounding rects overlap."""
    ids = list(boxes.keys())
    collisions = []
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            r1 = boxes[ids[i]].rect.pad(4)
            r2 = boxes[ids[j]].rect.pad(4)
            if r1.intersects(r2):
                collisions.append((ids[i], ids[j]))
    return collisions


def _resolve_collisions(boxes: Dict[str, ElementBox], content: Rect):
    """Push overlapping elements apart. Simple iterative approach."""
    for _ in range(10):  # max iterations
        collisions = _check_collisions(boxes)
        if not collisions:
            break
        for id1, id2 in collisions:
            b1, b2 = boxes[id1], boxes[id2]
            dx = b2.x - b1.x
            dy = b2.y - b1.y
            dist = math.hypot(dx, dy)
            if dist < 1:
                dx, dy, dist = 1, 0, 1
            push = 10
            boxes[id1] = ElementBox(b1.id, b1.x - dx/dist*push, b1.y - dy/dist*push,
                                     b1.width, b1.height, b1.shape)
            boxes[id2] = ElementBox(b2.id, b2.x + dx/dist*push, b2.y + dy/dist*push,
                                     b2.width, b2.height, b2.shape)

    # Clamp to content bounds
    for eid, box in boxes.items():
        cx = max(content.x + box.width/2, min(content.right - box.width/2, box.x))
        cy = max(content.y + box.height/2, min(content.bottom - box.height/2, box.y))
        boxes[eid] = ElementBox(box.id, cx, cy, box.width, box.height, box.shape)


# ─── Main Entry Point ────────────────────────────────────────────────────

def do_layout(data: Dict[str, Any]) -> LayoutResult:
    layout_type = data["layout"]
    elements = data["elements"]
    connectors = data.get("connectors", [])

    regions = _calculate_regions(data)

    # Dispatch to layout algorithm
    layout_fn = LAYOUT_DISPATCH.get(layout_type, _layout_flow)
    boxes = layout_fn(elements, regions.content)

    # Collision resolution
    _resolve_collisions(boxes, regions.content)

    # Calculate connector anchors
    enriched_connectors = []
    for conn in connectors:
        if conn["type"] == "none":
            continue
        c_from, c_to = conn["from"], conn["to"]
        if c_from in boxes and c_to in boxes:
            p1, p2 = _calculate_anchors(boxes[c_from], boxes[c_to])
            new_conn = dict(conn)
            new_conn["x1"] = p1.x
            new_conn["y1"] = p1.y
            new_conn["x2"] = p2.x
            new_conn["y2"] = p2.y
            enriched_connectors.append(new_conn)

    return LayoutResult(elements=boxes, connectors=enriched_connectors,
                        regions=regions)
