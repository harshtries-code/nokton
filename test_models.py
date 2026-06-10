from pathlib import Path
import json, requests

config = json.loads((Path.home() / ".nokton" / "nokton.json").read_text())
api_key = config["providers"]["openrouter"]["api_key"]
resp = requests.get("https://openrouter.ai/api/v1/models", headers={"Authorization": f"Bearer {api_key}"}, timeout=15)
data = resp.json()
free_models = [m for m in data.get("data", []) if m["id"].endswith(":free")]
print(f"Total free models: {len(free_models)}")
for m in free_models[:20]:
    mid = m["id"]
    name = m.get("name", "")
    print(f"  {mid}  ({name})")
