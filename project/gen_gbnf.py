def generate_list(rule_name, min_items, max_items):
    lines = []
    for i in range(min_items, max_items + 1):
        if i == 0:
            lines.append("ws") # Actually empty list handled separately
        else:
            line = rule_name + (" \",\" ws " + rule_name) * (i - 1)
            lines.append(line)
    return " | ".join(lines)

gbnf = f"""root ::= "{{" ws "\\"title\\"" ws ":" ws string "," ws "\\"subtitle\\"" ws ":" ws string "," ws "\\"layout\\"" ws ":" ws layout_enum "," ws "\\"stats\\"" ws ":" ws stats_array "," ws "\\"elements\\"" ws ":" ws elements_array "," ws "\\"connectors\\"" ws ":" ws connectors_array "," ws "\\"footer\\"" ws ":" ws string "}}"

ws ::= [ \\t\\n\\r]*

string ::= "\\"" chars "\\""
chars ::= [^"\\\\]*

layout_enum ::= "\\"flow\\"" | "\\"timeline\\"" | "\\"grid\\"" | "\\"two_column\\"" | "\\"centered\\"" | "\\"hub_and_spoke\\"" | "\\"stacked\\"" | "\\"comparison\\""
shape_enum ::= "\\"rectangle\\"" | "\\"rounded_rectangle\\"" | "\\"circle\\"" | "\\"diamond\\"" | "\\"hexagon\\"" | "\\"pill\\""
icon_enum ::= "\\"clock\\"" | "\\"shield\\"" | "\\"code\\"" | "\\"user\\"" | "\\"database\\"" | "\\"server\\"" | "\\"api\\"" | "\\"cloud\\""
size_enum ::= "\\"small\\"" | "\\"medium\\"" | "\\"large\\""
emphasis_enum ::= "\\"normal\\"" | "\\"primary\\"" | "\\"highlighted\\"" | "\\"secondary\\""
connector_type_enum ::= "\\"none\\"" | "\\"line\\"" | "\\"arrow\\"" | "\\"dashed_arrow\\""

stats_array ::= "[" ws stats_list "]" | "[" ws "]"
stats_list ::= {generate_list('stat_obj', 1, 4)}
stat_obj ::= "{{" ws "\\"label\\"" ws ":" ws string "," ws "\\"value\\"" ws ":" ws string ws "}}"

elements_array ::= "[" ws elements_list "]"
elements_list ::= {generate_list('element_obj', 2, 8)}
element_obj ::= "{{" ws "\\"id\\"" ws ":" ws string "," ws "\\"title\\"" ws ":" ws string "," ws "\\"text\\"" ws ":" ws string "," ws "\\"shape\\"" ws ":" ws shape_enum "," ws "\\"icon\\"" ws ":" ws icon_enum "," ws "\\"size\\"" ws ":" ws size_enum "," ws "\\"emphasis\\"" ws ":" ws emphasis_enum ws "}}"

connectors_array ::= "[" ws connectors_list "]" | "[" ws "]"
connectors_list ::= {generate_list('connector_obj', 1, 10)}
connector_obj ::= "{{" ws "\\"from\\"" ws ":" ws string "," ws "\\"to\\"" ws ":" ws string "," ws "\\"type\\"" ws ":" ws connector_type_enum ws "}}"
"""

with open("infographic.gbnf", "w") as f:
    f.write(gbnf)

print("Generated foolproof infographic.gbnf")
