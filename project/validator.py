import json
from typing import Dict, Any
from config import LIMITS
from icons import ICONS

class ValidationError(Exception):
    pass

def _truncate(text: str, max_len: int) -> str:
    """Truncate text to max_len, adding ellipsis if needed."""
    if len(text) <= max_len:
        return text
    return text[:max_len - 3] + "..."

def validate_infographic_data(data_str: str) -> Dict[str, Any]:
    try:
        data = json.loads(data_str)
    except json.JSONDecodeError as e:
        raise ValidationError(f"Invalid JSON: {e}")
    
    if not isinstance(data, dict):
        raise ValidationError("Root must be a JSON object")

    # Required keys at root
    required_keys = {"title", "subtitle", "layout", "stats", "elements", "connectors", "footer"}
    actual_keys = set(data.keys())
    
    if not required_keys.issubset(actual_keys):
        missing = required_keys - actual_keys
        raise ValidationError(f"Missing required keys at root: {missing}")
        
    if not actual_keys.issubset(required_keys):
        extra = actual_keys - required_keys
        raise ValidationError(f"Unknown keys at root: {extra}")

    # Truncate overlong root strings instead of rejecting
    data["title"] = _truncate(data.get("title", ""), LIMITS["max_title_len"])
    data["subtitle"] = _truncate(data.get("subtitle", ""), LIMITS["max_subtitle_len"])
    data["footer"] = _truncate(data.get("footer", ""), LIMITS["max_footer_len"])

    # Enum validation
    valid_layouts = {"flow", "timeline", "grid", "two_column", "centered", "hub_and_spoke", "stacked", "comparison"}
    if data["layout"] not in valid_layouts:
        raise ValidationError(f"Invalid layout: {data['layout']}")

    # Stats validation
    stats = data.get("stats", [])
    if not isinstance(stats, list):
        raise ValidationError("Stats must be a list")
    if len(stats) > LIMITS["max_stats"]:
        stats = stats[:LIMITS["max_stats"]]
        data["stats"] = stats
        
    for i, stat in enumerate(stats):
        if not isinstance(stat, dict):
            raise ValidationError(f"Stat {i} must be an object")
        if "label" not in stat or "value" not in stat:
            raise ValidationError(f"Stat {i} missing label or value")
        stat["label"] = _truncate(str(stat["label"]), LIMITS["max_stat_label_len"])
        stat["value"] = _truncate(str(stat["value"]), LIMITS["max_stat_value_len"])

    # Elements validation
    elements = data.get("elements", [])
    if not isinstance(elements, list):
        raise ValidationError("Elements must be a list")
    if len(elements) > LIMITS["max_elements"]:
        elements = elements[:LIMITS["max_elements"]]
        data["elements"] = elements
    
    valid_shapes = {"rectangle", "rounded_rectangle", "circle", "diamond", "hexagon", "pill"}
    valid_icons = set(ICONS.keys())
    valid_sizes = {"small", "medium", "large"}
    valid_emphasis = {"normal", "primary", "highlighted", "secondary"}
    
    element_ids = set()
    for i, el in enumerate(elements):
        req_el_keys = {"id", "title", "text", "shape", "icon", "size", "emphasis"}
        if not isinstance(el, dict) or not req_el_keys.issubset(set(el.keys())):
            raise ValidationError(f"Element {i} missing required keys")
            
        el_id = el["id"]
        if not isinstance(el_id, str) or not el_id.strip():
            raise ValidationError(f"Element {i} has invalid ID")
        if el_id in element_ids:
            raise ValidationError(f"Duplicate element ID: {el_id}")
        element_ids.add(el_id)
        
        # Truncate text fields instead of rejecting
        el["title"] = _truncate(el["title"], LIMITS["max_element_title_len"])
        el["text"] = _truncate(el["text"], LIMITS["max_element_text_len"])
            
        if el["shape"] not in valid_shapes:
            raise ValidationError(f"Element '{el_id}' has invalid shape: {el['shape']}")
        if el["icon"] not in valid_icons:
            raise ValidationError(f"Element '{el_id}' has invalid icon: {el['icon']}")
        if el["size"] not in valid_sizes:
            raise ValidationError(f"Element '{el_id}' has invalid size: {el['size']}")
        if el["emphasis"] not in valid_emphasis:
            raise ValidationError(f"Element '{el_id}' has invalid emphasis: {el['emphasis']}")

    # Connectors validation
    connectors = data.get("connectors", [])
    if not isinstance(connectors, list):
        raise ValidationError("Connectors must be a list")
    if len(connectors) > LIMITS["max_connectors"]:
        connectors = connectors[:LIMITS["max_connectors"]]
        data["connectors"] = connectors
        
    valid_conn_types = {"none", "line", "arrow", "dashed_arrow"}
    for i, conn in enumerate(connectors):
        if not isinstance(conn, dict):
            raise ValidationError(f"Connector {i} must be an object")
        req_conn_keys = {"from", "to", "type"}
        if not req_conn_keys.issubset(set(conn.keys())):
            raise ValidationError(f"Connector {i} missing required keys")
            
        if conn["type"] not in valid_conn_types:
            raise ValidationError(f"Connector {i} has invalid type: {conn['type']}")
            
        if conn["from"] not in element_ids:
            raise ValidationError(f"Connector {i} 'from' references unknown ID: {conn['from']}")
        if conn["to"] not in element_ids:
            raise ValidationError(f"Connector {i} 'to' references unknown ID: {conn['to']}")

    return data
