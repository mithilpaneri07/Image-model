# These are SVG paths for a 24x24 viewBox.
# We scale and color them appropriately in the renderer.

ICONS = {
    "clock": '<circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" stroke-width="2"/><polyline points="12 6 12 12 16 14" fill="none" stroke="currentColor" stroke-width="2"/>',
    "shield": '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" fill="none" stroke="currentColor" stroke-width="2"/>',
    "code": '<polyline points="16 18 22 12 16 6" fill="none" stroke="currentColor" stroke-width="2"/><polyline points="8 6 2 12 8 18" fill="none" stroke="currentColor" stroke-width="2"/>',
    "user": '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" fill="none" stroke="currentColor" stroke-width="2"/><circle cx="12" cy="7" r="4" fill="none" stroke="currentColor" stroke-width="2"/>',
    "database": '<ellipse cx="12" cy="5" rx="9" ry="3" fill="none" stroke="currentColor" stroke-width="2"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" fill="none" stroke="currentColor" stroke-width="2"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" fill="none" stroke="currentColor" stroke-width="2"/>',
    "server": '<rect x="2" y="2" width="20" height="8" rx="2" ry="2" fill="none" stroke="currentColor" stroke-width="2"/><rect x="2" y="14" width="20" height="8" rx="2" ry="2" fill="none" stroke="currentColor" stroke-width="2"/><line x1="6" y1="6" x2="6.01" y2="6" stroke="currentColor" stroke-width="2"/><line x1="6" y1="18" x2="6.01" y2="18" stroke="currentColor" stroke-width="2"/>',
    "api": '<path d="M8 9l3 3-3 3" fill="none" stroke="currentColor" stroke-width="2"/><line x1="13" y1="15" x2="16" y2="15" stroke="currentColor" stroke-width="2"/><rect x="3" y="4" width="18" height="16" rx="2" ry="2" fill="none" stroke="currentColor" stroke-width="2"/>',
    "cloud": '<path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z" fill="none" stroke="currentColor" stroke-width="2"/>',
}

def get_icon_svg(name: str, x: float, y: float, size: float, color: str) -> str:
    """
    Returns an SVG group containing the icon with stroke set to color.
    The icon is originally 24x24. We scale and translate it.
    """
    if name not in ICONS:
        return ""
    
    scale = size / 24.0
    path_data = ICONS[name].replace("currentColor", color)
    
    return f'<g transform="translate({x:.1f}, {y:.1f}) scale({scale:.3f})">{path_data}</g>'
