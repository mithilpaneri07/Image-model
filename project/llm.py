import urllib.request
import json
from config import LLAMA_API_URL, GRAMMAR_FILE, PROMPT_FILE

def generate_infographic_json(topic: str) -> str:
    """
    Calls the local llama-server API to generate the JSON.
    """
    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        prompt_template = f.read()
        
    with open(GRAMMAR_FILE, "r", encoding="utf-8") as f:
        grammar_content = f.read()
        
    prompt = prompt_template.format(topic=topic)
    
    print(f"Running LLM generation for topic: '{topic}' (via {LLAMA_API_URL})")
    
    payload = {
        "prompt": prompt,
        "n_predict": 4096,
        "temperature": 0.05,
        "grammar": grammar_content
    }
    
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        LLAMA_API_URL,
        data=data,
        headers={"Content-Type": "application/json"}
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result.get("content", "")
    except urllib.error.HTTPError as e:
        error_msg = e.read().decode("utf-8")
        raise RuntimeError(f"Server returned HTTP {e.code}: {error_msg}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"Failed to connect to server at {LLAMA_API_URL}: {e.reason}")
