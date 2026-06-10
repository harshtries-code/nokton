import asyncio, json

async def test():
    import websockets
    async with websockets.connect('ws://127.0.0.1:8765/ws') as ws:
        msg = json.dumps({"type": "user_message", "text": "say hello in one word", "images": []})
        print(f"Sending: {msg}")
        await ws.send(msg)
        
        for i in range(30):
            try:
                resp = await asyncio.wait_for(ws.recv(), timeout=30)
                data = json.loads(resp)
                evt_type = data.get("type", "?")
                print(f"  [{evt_type}] {json.dumps(data)[:300]}")
                if evt_type == "assistant_done":
                    print("SUCCESS!")
                    break
                if evt_type == "status" and data.get("state") == "idle":
                    print("Got idle status")
                    break
                if evt_type == "error":
                    print(f"ERROR: {data}")
                    break
            except asyncio.TimeoutError:
                print("  TIMEOUT - no response in 30s")
                break

asyncio.run(test())
