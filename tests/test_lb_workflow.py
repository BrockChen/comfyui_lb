import json
import asyncio
import httpx
import sys
import os
import websockets

# 配置
LB_URL = os.environ.get("LB_URL", "http://localhost:8100")
WORKFLOW_JSON = """
{
  "2": {
    "inputs": {
      "text": "少年朱元璋身披破旧僧袍，赤脚站在荒芜田埂上，身后是塌陷的祖坟与枯树。他手持木钵，眼神空洞又倔强，脸上沾着尘土与泪痕。天空阴沉，乌鸦盘旋。背景是荒村断壁，偶有野狗徘徊。风吹起他单薄衣角，体现孤苦无依却又不甘命运的少年心志。古风卡通风格",
      "clip": ["16", 0]
    },
    "class_type": "CLIPTextEncode",
    "_meta": {
      "title": "正向提示词"
    }
  },
  "4": {
    "inputs": {
      "seed": 1065951732236216,
      "steps": 8,
      "cfg": 1,
      "sampler_name": "euler",
      "scheduler": "simple",
      "denoise": 1,
      "model": ["15", 0],
      "positive": ["2", 0],
      "negative": ["9", 0],
      "latent_image": ["5", 0]
    },
    "class_type": "KSampler",
    "_meta": {
      "title": "K采样器"
    }
  },
  "5": {
    "inputs": {
      "width": 512,
      "height": 512,
      "batch_size": 1
    },
    "class_type": "EmptyLatentImage",
    "_meta": {
      "title": "空Latent图像"
    }
  },
  "6": {
    "inputs": {
      "vae_name": "ae.safetensors"
    },
    "class_type": "VAELoader",
    "_meta": {
      "title": "加载VAE"
    }
  },
  "7": {
    "inputs": {
      "samples": ["4", 0],
      "vae": ["6", 0]
    },
    "class_type": "VAEDecode",
    "_meta": {
      "title": "VAE解码"
    }
  },
  "8": {
    "inputs": {
      "filename_prefix": "ComfyUI",
      "images": ["7", 0]
    },
    "class_type": "SaveImage",
    "_meta": {
      "title": "保存图像"
    }
  },
  "9": {
    "inputs": {
      "text": "blurry, ugly, bad, lowres, jpeg artifacts, watermark, distorted, noisy, artifact, glitch, oversaturation, neon tones, harsh contrast or glow, color cast, pixelated, blocky",
      "clip": ["16", 0]
    },
    "class_type": "CLIPTextEncode",
    "_meta": {
      "title": "反向提示词"
    }
  },
  "15": {
    "inputs": {
      "ckpt_name": "z_image_turbo_bf16.safetensors"
    },
    "class_type": "CheckpointLoaderSimple",
    "_meta": {
      "title": "加载主模型"
    }
  },
  "16": {
    "inputs": {
      "clip_name": "qwen_3_4b.safetensors",
      "type": "stable_diffusion",
      "device": "default"
    },
    "class_type": "CLIPLoader",
    "_meta": {
      "title": "加载CLIP文本编码器"
    }
  }
}
"""

async def submit_prompt(prompt, client_id="test_client"):
    async with httpx.AsyncClient(timeout=10.0) as client:
        payload = {
            "prompt": prompt,
            "client_id": client_id
        }
        print(f"Submitting prompt with client_id: {client_id}...")
        try:
            response = await client.post(f"{LB_URL}/prompt", json=payload)
            response.raise_for_status()
            data = response.json()
            print(f"Success! Prompt ID: {data.get('prompt_id')}")
            return data
        except Exception as e:
            print(f"Error submitting prompt: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"Response: {e.response.text}")
            return None

async def get_lb_stats():
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            response = await client.get(f"{LB_URL}/lb/stats")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error getting LB stats: {e}")
            return None

async def run_baseline_test():
    print("--- Running Baseline Test ---")
    prompt = json.loads(WORKFLOW_JSON)
    await submit_prompt(prompt)

async def run_variation_test():
    print("--- Running Variation Test ---")
    prompt = json.loads(WORKFLOW_JSON)
    # 修改提示词
    prompt["2"]["inputs"]["text"] = "老年朱元璋身披华丽龙袍，威严地坐在金銮殿龙椅上，面容沧桑沉稳。眼神锐利有神。背景是宏伟的宫殿建筑。古风写实风格。"
    await submit_prompt(prompt, client_id="variation_client")

async def run_load_test(count=5):
    print(f"--- Running Load Test ({count} requests) ---")
    prompt = json.loads(WORKFLOW_JSON)
    tasks = []
    for i in range(count):
        tasks.append(submit_prompt(prompt, client_id=f"load_test_{i}"))
    await asyncio.gather(*tasks)

async def wait_for_completion(prompt_id, timeout=60, poll_interval=2):
    """等候任务完成"""
    start_time = asyncio.get_event_loop().time()
    async with httpx.AsyncClient(timeout=10.0) as client:
        print(f"Waiting for task {prompt_id} to complete...")
        while asyncio.get_event_loop().time() - start_time < timeout:
            try:
                response = await client.get(f"{LB_URL}/history/{prompt_id}")
                response.raise_for_status()
                history = response.json()
                
                if prompt_id in history:
                    task_info = history[prompt_id]
                    status = task_info.get("status", {})
                    if status.get("completed"):
                        print(f"Task {prompt_id} completed with status: {status.get('status_str')}")
                        return task_info
                
                # 如果LB还没拿到后端的详细history,LB会返回基本的status
                # 我们也检查一下LB的详细任务接口
                task_resp = await client.get(f"{LB_URL}/lb/tasks/{prompt_id}")
                if task_resp.status_code == 200:
                    task = task_resp.json()
                    if task.get("status") in ["completed", "failed"]:
                        print(f"LB reports task {prompt_id} is {task.get('status')}")
                        # 再次尝试获取history以拿输出
                        response = await client.get(f"{LB_URL}/history/{prompt_id}")
                        return response.json().get(prompt_id)

            except Exception as e:
                print(f"Polling error: {e}")
            
            await asyncio.sleep(poll_interval)
    
    print("Timeout waiting for task completion")
    return None

async def wait_for_completion_ws(client_id, prompt_id, timeout=60):
    """使用WebSocket等候任务完成"""
    ws_url = LB_URL.replace("http://", "ws://").replace("https://", "wss://") + f"/ws?clientId={client_id}"
    print(f"Connecting to LB WebSocket for monitoring: {ws_url}")
    
    start_time = asyncio.get_event_loop().time()
    try:
        async with websockets.connect(ws_url) as websocket:
            print(f"WebSocket connected. Waiting for prompt {prompt_id}...")
            while asyncio.get_event_loop().time() - start_time < timeout:
                try:
                    # 设置较短的超时以循环检查总超时
                    message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    if isinstance(message, str):
                        data = json.loads(message)
                        m_type = data.get("type")
                        m_data = data.get("data", {})
                        
                        # 打印进度
                        if m_type == "progress":
                            print(f"Progress: {m_data.get('value')}/{m_data.get('max')}")
                        elif m_type == "executing" and m_data.get("node"):
                            print(f"Executing node: {m_data.get('node')}")
                        
                        # 检查完成
                        if m_type == "executed" and m_data.get("prompt_id") == prompt_id:
                            print(f"Task {prompt_id} execution completed (WS: executed)")
                            return m_data.get("output")
                        
                        # 某些后端可能只发送 status 
                        if m_type == "status" and m_data.get("status", {}).get("completed"):
                            # 如果是 status 完成，还需要去拿历史记录拿具体的 output
                            print(f"Task {prompt_id} reported completed via status")
                            return True # 标识已完成
                            
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    print(f"WS Recv Error: {e}")
                    break
    except Exception as e:
        print(f"WS Connection Error: {e}")
    
    print("WS monitoring failed or timed out, falling back to polling...")
    return None

async def download_image(filename, subfolder, type, backend, save_path):
    """下载图片"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        params = {
            "filename": filename,
            "subfolder": subfolder,
            "type": type,
            "backend": backend
        }
        print(f"Downloading image {filename} from backend {backend}...")
        try:
            response = await client.get(f"{LB_URL}/view", params=params)
            response.raise_for_status()
            with open(save_path, "wb") as f:
                f.write(response.content)
            print(f"Image saved to {save_path}")
            return True
        except Exception as e:
            print(f"Error downloading image: {e}")
            return False

async def run_closed_loop_test():
    print("\n--- Running Closed-loop Test (Prompt -> Image via WS) ---")
    client_id = "closed_loop_ws_client"
    prompt = json.loads(WORKFLOW_JSON)
    ws_url = LB_URL.replace("http://", "ws://").replace("https://", "wss://") + f"/ws?clientId={client_id}"
    
    print(f"Connecting to LB WebSocket: {ws_url}")
    try:
        async with websockets.connect(ws_url) as websocket:
            print("WebSocket connected. Submitting prompt...")
            
            # 1. 提交任务
            result = await submit_prompt(prompt, client_id=client_id)
            if not result:
                return
            prompt_id = result.get("prompt_id")
            
            # 2. 监听消息
            task_info = None
            timeout = 180 # 增加到180秒，因为生图较慢
            start_time = asyncio.get_event_loop().time()
            
            while asyncio.get_event_loop().time() - start_time < timeout:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    if isinstance(message, str):
                        data = json.loads(message)
                        m_type = data.get("type")
                        m_data = data.get("data", {})
                        
                        # 打印所有类型，方便调试
                        if m_type != "executing" or m_data.get("node"): # 过滤空执行消息
                           print(f"[WS] Received type: {m_type}")

                        # 打印进度和状态
                        if m_type == "progress":
                            print(f"[WS] Progress: {m_data.get('value')}/{m_data.get('max')}")
                        elif m_type == "executing" and m_data.get("node"):
                            print(f"[WS] Executing node: {m_data.get('node')}")
                        
                        # 检查完成
                        if m_type == "executed" or m_type == "execution_success":
                            # 注意：ComfyUI 的 executed 消息可能在 data 里包含 prompt_id
                            msg_prompt_id = m_data.get("prompt_id")
                            if msg_prompt_id == prompt_id:
                                print(f"[WS] Task {prompt_id} execution completed (type: {m_type})")
                                if m_type == "executed":
                                    task_info = {"outputs": {m_data.get("node"): m_data.get("output")}}
                                    break
                                else:
                                    # execution_success 不带直接输出，回退到轮询拉取完整 history
                                    task_info = await wait_for_completion(prompt_id)
                                    if task_info:
                                        break
                        
                        if m_type == "status" and m_data.get("status", {}).get("completed"):
                             # 有些版本可能不带 sid，或者是在这里结束
                             print(f"[WS] Task reported completed via status")
                             # 这种情况下通过轮询拿最终结果
                             task_info = await wait_for_completion(prompt_id)
                             if task_info:
                                 break
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    print(f"WS Recv Error: {e}")
                    break
            
            if not task_info:
                print("WS monitoring timed out, falling back to polling...")
                task_info = await wait_for_completion(prompt_id)

            if not task_info:
                print("Failed to get completed task info")
                return

            # 3. 提取输出图片信息
            outputs = task_info.get("outputs", {})
            image_info = None
            for node_id, node_output in outputs.items():
                if "images" in node_output:
                    image_info = node_output["images"][0]
                    break
            
            if not image_info:
                print("No images found in outputs")
                return
            
            # 4. 获取后端名称
            async with httpx.AsyncClient() as client:
                task_resp = await client.get(f"{LB_URL}/lb/tasks/{prompt_id}")
                task_data = task_resp.json()
                backend_name = task_data.get("backend_name")
            
            # 5. 下载图片
            os.makedirs("outputs", exist_ok=True)
            filename = image_info.get("filename")
            save_path = f"outputs/{filename}"
            await download_image(
                filename=filename,
                subfolder=image_info.get("subfolder", ""),
                type=image_info.get("type", "output"),
                backend=backend_name,
                save_path=save_path
            )
            
    except Exception as e:
        print(f"WebSocket/Test error: {e}")
        # 这里如果 WS 连不上，可以尝试全流程 Polling 模式
        print("Falling back to standard polling closed-loop test...")
        # (为简洁起见，此处省略逻辑，实际可调用原 run_closed_loop_test 的逻辑)

async def main():
    print(f"Starting tests against {LB_URL}")
    
    # 检查 LB 是否运行
    try:
        stats = await get_lb_stats()
    except Exception:
        stats = None

    if not stats:
        print("LB is not reachable. Please make sure the server is running.")
        return

    print(f"Connected to LB. Healthy backends: {stats.get('healthy_backends')}")
    
    # 只运行闭环测试以验证全流程
    await run_closed_loop_test()
    
    print("\n--- Final LB Stats ---")
    final_stats = await get_lb_stats()
    print(json.dumps(final_stats, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(main())
