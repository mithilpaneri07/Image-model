"""
Systematic GBNF feature test against llama-server.
Tests each feature in isolation to find what breaks.
"""
import urllib.request
import json
import sys

URL = "http://127.0.0.1:8080/completion"

def test_grammar(label, grammar_str):
    payload = json.dumps({"prompt": "test", "n_predict": 10, "grammar": grammar_str}).encode("utf-8")
    req = urllib.request.Request(URL, data=payload, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=10)
        print(f"  PASS: {label}")
        return True
    except urllib.error.HTTPError as e:
        msg = e.read().decode("utf-8")
        print(f"  FAIL: {label}")
        return False
    except Exception as e:
        print(f"  ERROR: {label} -> {e}")
        return False

print("=== BASIC FEATURES ===")
test_grammar("literal string", 'root ::= "hello"')
test_grammar("two literals", 'root ::= "a" "b"')
test_grammar("alternatives", 'root ::= "a" | "b"')
test_grammar("char class [a-z]", 'root ::= [a-z]')
test_grammar("negated class [^x]", 'root ::= [^"]*')
test_grammar("negated class [^\"\\\\]", 'root ::= [^"\\\\]*')

print("\n=== WHITESPACE RULES ===")
test_grammar("ws space only", 'root ::= " "*')
test_grammar("ws [ ]*", 'root ::= [ ]*')
test_grammar("ws [ \\t]*", 'root ::= [ \\t]*')
test_grammar("ws [ \\t\\n]*", 'root ::= [ \\t\\n]*')
test_grammar("ws [ \\t\\n\\r]*", 'root ::= [ \\t\\n\\r]*')

print("\n=== MULTI-RULE ===")
test_grammar("two rules", 'root ::= a\na ::= "x"')
test_grammar("three rules", 'root ::= a b\na ::= "x"\nb ::= "y"')

print("\n=== REPETITION ===")
test_grammar("star on literal", 'root ::= "a"*')
test_grammar("plus on literal", 'root ::= "a"+')
test_grammar("question on literal", 'root ::= "a"?')
test_grammar("star on group", 'root ::= ("a" "b")*')
test_grammar("question on group", 'root ::= ("a" "b")?')
test_grammar("nested group star", 'root ::= "x" ("," "x")*')

print("\n=== COMMENTS ===")
test_grammar("hash comment", '# comment\nroot ::= "a"')
test_grammar("inline comment", 'root ::= "a" # comment')

print("\n=== RULE NAME CHARS ===")
test_grammar("underscore in name", 'root ::= foo_bar\nfoo_bar ::= "x"')
test_grammar("hyphen in name", 'root ::= foo-bar\nfoo-bar ::= "x"')
test_grammar("digits in name", 'root ::= foo1\nfoo1 ::= "x"')

print("\n=== EMPTY ALTERNATIVES ===")
test_grammar("empty alt with quotes", 'root ::= "" | "a"')
test_grammar("empty alt no quotes", 'root ::= "a" | ')

print("\n=== MULTI-LINE RULE ===")
test_grammar("continuation line", 'root ::= "a"\n       | "b"')

print("\n=== JSON PATTERNS ===")
test_grammar("json key-value", 'root ::= "{" "\\\"title\\\"" ":" "\\\"hello\\\"" "}"')
test_grammar("quoted key ws",
    'root ::= "{" ws "\\\"title\\\"" ws ":" ws str ws "}"\nws ::= [ ]*\nstr ::= "\\\"" [^"]* "\\\"" ')
test_grammar("json full mini",
    'root ::= "{" ws "\\\"a\\\"" ws ":" ws str "," ws "\\\"b\\\"" ws ":" ws str ws "}"\nws ::= [ \\t\\n\\r]*\nstr ::= "\\\"" [^"\\\\]* "\\\"" ')

print("\n=== ENUM PATTERN ===")
test_grammar("enum alternatives",
    'root ::= e\ne ::= "\\\"flow\\\"" | "\\\"grid\\\"" | "\\\"stacked\\\"" ')

print("\n=== ARRAY PATTERNS ===")
test_grammar("fixed 2-item array",
    'root ::= "[" item "," item "]"\nitem ::= "\\\"" [a-z]+ "\\\"" ')
test_grammar("fixed 3-item array",
    'root ::= "[" item "," item "," item "]"\nitem ::= "\\\"" [a-z]+ "\\\"" ')
test_grammar("variable array with star",
    'root ::= "[" item ("," item)* "]"\nitem ::= "\\\"" [a-z]+ "\\\"" ')
test_grammar("optional group in array",
    'root ::= "[" (item ("," item)*)? "]"\nitem ::= "\\\"" [a-z]+ "\\\"" ')

print("\n=== FULL OBJECT TEST ===")
test_grammar("element-like object",
    'root ::= "{" ws "\\\"id\\\"" ws ":" ws str "," ws "\\\"title\\\"" ws ":" ws str ws "}"\nws ::= [ \\t\\n\\r]*\nstr ::= "\\\"" [^"\\\\]* "\\\"" ')

print("\n=== COMBINED: OBJECT ARRAY ===")
test_grammar("array of objects fixed 2",
    'root ::= "[" ws obj "," ws obj ws "]"\nobj ::= "{" ws "\\\"a\\\"" ws ":" ws str ws "}"\nws ::= [ \\t\\n\\r]*\nstr ::= "\\\"" [^"\\\\]* "\\\"" ')

print("\n=== COMBINED: FULL SCHEMA MINI ===")
g = ('root ::= "{" ws "\\\"title\\\"" ws ":" ws str "," ws '
     '"\\\"layout\\\"" ws ":" ws lay "," ws '
     '"\\\"items\\\"" ws ":" ws "[" ws obj "," ws obj ws "]" "," ws '
     '"\\\"footer\\\"" ws ":" ws str ws "}"\n'
     'lay ::= "\\\"flow\\\"" | "\\\"grid\\\""\n'
     'obj ::= "{" ws "\\\"id\\\"" ws ":" ws str "," ws "\\\"shape\\\"" ws ":" ws sh ws "}"\n'
     'sh ::= "\\\"circle\\\"" | "\\\"rect\\\""\n'
     'ws ::= [ \\t\\n\\r]*\n'
     'str ::= "\\\"" [^"\\\\]* "\\\""\n')
test_grammar("mini full schema", g)

print("\nDone.")
