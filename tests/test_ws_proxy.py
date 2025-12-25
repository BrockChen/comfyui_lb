import asyncio
import websockets
import json
import sys

async def test_ws_proxy(client_id="closed_loop_client"):
    uri = f"ws://localhost:8100/ws?clientId={client_id}"
    print(f"Connecting to LB WebSocket at {uri}...")
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected! Waiting for messages (30 seconds)...")
            
            # 设置一个超时，防止脚本无限运行
            try:
                while True:
                    message = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                    if isinstance(message, str):
                        data = json.loads(message)
                        print(f"Received JSON: {json.dumps(data, indent=2, ensure_ascii=False)}")
                    else:
                        print(f"Received Binary message (size: {len(message)})")
            except asyncio.TimeoutError:
                print("Test finished (timeout reached).")
                
    except Exception as e:
        print(f"WebSocket Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_ws_proxy())
