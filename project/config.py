import os
from dataclasses import dataclass

# ─── Canvas ───────────────────────────────────────────────────────────────
CANVAS_WIDTH = 1600
CANVAS_HEIGHT = 1000

# ─── Page Margins ─────────────────────────────────────────────────────────
MARGIN_TOP = 40
MARGIN_BOTTOM = 40
MARGIN_LEFT = 60
MARGIN_RIGHT = 60

# ─── Spacing Scale ────────────────────────────────────────────────────────
SPACING_XS = 8
SPACING_SM = 16
SPACING_MD = 24
SPACING_LG = 40
SPACING_XL = 56

# ─── Element Sizing ──────────────────────────────────────────────────────
# (min_width, preferred_width, min_height, preferred_height)
ELEMENT_SIZES = {
    "small":  (140, 200, 100, 130),
    "medium": (180, 260, 120, 160),
    "large":  (220, 340, 140, 200),
}

ELEMENT_PADDING = 16
ELEMENT_CORNER_RADIUS = 12
ELEMENT_STROKE_WIDTH = 2
ICON_SIZE = 28

# ─── Typography Scale ────────────────────────────────────────────────────
FONT_FAMILY = "'Inter', 'Segoe UI', system-ui, sans-serif"

@dataclass(frozen=True)
class TypeStyle:
    size: int
    weight: str
    line_height: float  # multiplier
    color_key: str      # key into COLORS

TYPESCALE = {
    "title":         TypeStyle(38, "700", 1.2, "text_primary"),
    "subtitle":      TypeStyle(18, "400", 1.4, "text_secondary"),
    "stat_value":    TypeStyle(28, "700", 1.1, "accent"),
    "stat_label":    TypeStyle(13, "500", 1.3, "text_secondary"),
    "element_title": TypeStyle(15, "700", 1.2, "text_primary"),
    "element_body":  TypeStyle(12, "400", 1.4, "text_secondary"),
    "footer":        TypeStyle(12, "400", 1.3, "text_muted"),
}

MIN_FONT_SIZE = 10

# ─── Color Palette ────────────────────────────────────────────────────────
COLORS = {
    "background":     "#F0F4F8",
    "surface":        "#FFFFFF",
    "surface_alt":    "#F8FAFC",
    "text_primary":   "#1E293B",
    "text_secondary": "#475569",
    "text_muted":     "#94A3B8",
    "border":         "#CBD5E1",
    "border_light":   "#E2E8F0",
    "accent":         "#3B82F6",
    "accent_dark":    "#2563EB",
    "accent_light":   "#DBEAFE",
    "secondary":      "#64748B",
    "secondary_light":"#F1F5F9",
    "highlighted":    "#F59E0B",
    "highlight_light":"#FEF3C7",
    "success":        "#10B981",
    "connector":      "#94A3B8",
    "connector_arrow":"#64748B",
    "shadow":         "rgba(15,23,42,0.08)",
}

# Emphasis → fill/stroke/text mapping
EMPHASIS_STYLES = {
    "primary": {
        "fill": COLORS["accent"],
        "stroke": COLORS["accent_dark"],
        "text": "#FFFFFF",
        "icon": "#FFFFFF",
    },
    "highlighted": {
        "fill": COLORS["highlighted"],
        "stroke": "#D97706",
        "text": "#FFFFFF",
        "icon": "#FFFFFF",
    },
    "secondary": {
        "fill": COLORS["secondary_light"],
        "stroke": COLORS["border"],
        "text": COLORS["text_primary"],
        "icon": COLORS["secondary"],
    },
    "normal": {
        "fill": COLORS["surface"],
        "stroke": COLORS["border"],
        "text": COLORS["text_primary"],
        "icon": COLORS["accent"],
    },
}

# ─── Text Limits ──────────────────────────────────────────────────────────
LIMITS = {
    "max_stats": 4,
    "max_elements": 8,
    "max_connectors": 10,
    "max_title_len": 80,
    "max_subtitle_len": 150,
    "max_element_title_len": 50,
    "max_element_text_len": 200,
    "max_footer_len": 120,
    "max_stat_label_len": 40,
    "max_stat_value_len": 40,
}

# ─── Model Settings ──────────────────────────────────────────────────────
MODEL_PATH = r"D:\Qwen\models\qwen2.5-coder-3b-instruct-q4_k_m.gguf"
LLAMA_API_URL = "http://127.0.0.1:8080/completion"

# ─── Paths ────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(BASE_DIR, "results")
RESULTS_PNG_DIR = os.path.join(BASE_DIR, "result-png")
GRAMMAR_FILE = os.path.join(BASE_DIR, "infographic.gbnf")
PROMPT_FILE = os.path.join(BASE_DIR, "prompt.txt")
