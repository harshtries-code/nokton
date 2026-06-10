"""Test with a fast free model to verify the streaming pipeline works."""
import json
from pathlib import Path
from openai import OpenAI

config = json.loads((Path.home() / ".nokton" / "nokton.json").read_text())
api_key = config["providers"]["openrouter"]["api_key"]

# Use a FAST free model instead of the slow 550B nemotron
model = "deepseek/deepseek-v4-flash:free"

client = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")

print(f"Model: {model}")
print("Sending request with stream=True...")

try:
    stream = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "say hello in one word"}],
        stream=True,
        max_tokens=50,
        temperature=0.7,
    )
    
    chunk_count = 0
    full_text = ""
    for chunk in stream:
        chunk_count += 1
        delta = chunk.choices[0].delta if chunk.choices else None
        if delta and delta.content:
            full_text += delta.content
            print(f"  chunk {chunk_count}: {repr(delta.content)}")
        elif chunk.choices and chunk.choices[0].finish_reason:
            print(f"  chunk {chunk_count}: finish_reason={chunk.choices[0].finish_reason}")
        
        if chunk_count > 50:
            break
    
    print(f"\nTotal chunks: {chunk_count}")
    print(f"Full response: {full_text}")
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
