"""
API 路由 - 兼容 ComfyUI API
"""
import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse
import httpx

from models import (
    PromptRequest, PromptResponse, SystemStats, QueueStatus, 
    BackendState, Task, TaskStatus
)
from config import BackendConfig

logger = logging.getLogger(__name__)

router = APIRouter()


def get_app_state(request: Request):
    """获取应用状态"""
    return request.app.state


# ============ ComfyUI 兼容 API ============

@router.post("/prompt")
async def submit_prompt(request: Request, body: dict[str, Any]) -> dict:
    """
    提交prompt - 兼容ComfyUI API
    任务会被添加到负载均衡队列,然后分发到空闲后端
    """
    state = get_app_state(request)
    
    prompt = body.get("prompt")
    if not prompt:
        raise HTTPException(status_code=400, detail="Missing prompt")
    
    client_id = body.get("client_id")
    extra_data = body.get("extra_data")
    
    try:
        # 添加到队列
        task = await state.task_queue.add_task(
            prompt=prompt,
            client_id=client_id,
            extra_data=extra_data
        )
        
        # 返回兼容ComfyUI的响应
        return {
            "prompt_id": task.id,
            "number": task.extra_data.get("number", 0) if task.extra_data else 0,
            "node_errors": {}
        }
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/queue")
async def get_queue(request: Request) -> dict:
    """
    获取队列状态 - 兼容ComfyUI API
    返回负载均衡器的队列状态
    """
    state = get_app_state(request)
    
    tasks = state.task_queue.get_all_tasks()
    
    # 转换为ComfyUI格式
    queue_running = []
    queue_pending = []
    
    for task in tasks["dispatched"]:
        queue_running.append([
            task.extra_data.get("number", 0) if task.extra_data else 0,
            task.id,
            task.prompt,
            {"client_id": task.client_id}
        ])
    
    for task in tasks["pending"]:
        queue_pending.append([
            task.extra_data.get("number", 0) if task.extra_data else 0,
            task.id,
            task.prompt,
            {"client_id": task.client_id}
        ])
    
    return {
        "queue_running": queue_running,
        "queue_pending": queue_pending
    }


@router.post("/queue")
async def manage_queue(request: Request, body: dict[str, Any]) -> Response:
    """
    管理队列 - 兼容ComfyUI API
    支持删除/取消任务
    """
    state = get_app_state(request)
    
    # 删除任务
    delete_ids = body.get("delete", [])
    for task_id in delete_ids:
        task = state.task_queue.get_task(task_id)
        if task:
            await state.task_queue.cancel_task(task_id)
            # 如果已分发,通知后端取消
            if task.backend_name and task.prompt_id:
                try:
                    await state.backend_manager.cancel_prompt(
                        task.backend_name, task.prompt_id
                    )
                except Exception as e:
                    logger.warning(f"取消后端任务失败: {e}")
    
    # 清空队列
    if body.get("clear"):
        tasks = state.task_queue.get_all_tasks()
        for task in tasks["pending"]:
            await state.task_queue.cancel_task(task.id)
    
    return Response(status_code=200)


@router.get("/history")
async def get_history(request: Request) -> dict:
    """
    获取历史记录 - 兼容ComfyUI API
    聚合所有后端的历史记录
    """
    state = get_app_state(request)
    
    # 获取本地完成的任务
    all_history = {}
    tasks = state.task_queue.get_all_tasks()
    
    for task in tasks["completed"]:
        all_history[task.id] = {
            "prompt": [
                task.extra_data.get("number", 0) if task.extra_data else 0,
                task.id,
                task.prompt,
                {"client_id": task.client_id},
                []
            ],
            "outputs": {},
            "status": {
                "status_str": "success" if task.status == TaskStatus.COMPLETED else "error",
                "completed": True,
                "messages": []
            }
        }
    
    return all_history


@router.get("/history/{prompt_id}")
async def get_history_by_id(request: Request, prompt_id: str) -> dict:
    """获取特定任务的历史记录"""
    state = get_app_state(request)
    
    task = state.task_queue.get_task(prompt_id)
    if not task:
        # 尝试从后端获取
        task = state.task_queue.get_task_by_prompt_id(prompt_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # 如果任务已分发到后端,尝试从后端获取详细信息
    if task.backend_name and task.prompt_id:
        try:
            history = await state.backend_manager.get_backend_history(
                task.backend_name, task.prompt_id
            )
            # 将后端的 prompt_id 映射回 LB 的 prompt_id
            if task.prompt_id in history:
                history[prompt_id] = history.pop(task.prompt_id)
            return history
        except Exception as e:
            logger.warning(f"获取后端历史失败: {e}")
    
    return {
        prompt_id: {
            "prompt": [
                task.extra_data.get("number", 0) if task.extra_data else 0,
                task.id,
                task.prompt,
                {"client_id": task.client_id},
                []
            ],
            "outputs": {},
            "status": {
                "status_str": task.status.value if hasattr(task.status, 'value') else str(task.status),
                "completed": task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED],
                "messages": [task.error] if task.error else []
            }
        }
    }


@router.get("/object_info")
async def get_object_info(request: Request) -> dict:
    """
    获取节点信息 - 代理到后端
    从第一个健康后端获取
    """
    state = get_app_state(request)
    
    backends = state.backend_manager.get_healthy_backends()
    if not backends:
        raise HTTPException(status_code=503, detail="No healthy backend available")
    
    backend = backends[0]
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{backend.base_url}/object_info")
        return response.json()


@router.get("/system_stats")
async def get_comfy_system_stats(request: Request) -> dict:
    """
    获取系统状态 - 代理到后端
    从第一个健康后端获取
    """
    state = get_app_state(request)
    
    backends = state.backend_manager.get_healthy_backends()
    if not backends:
        raise HTTPException(status_code=503, detail="No healthy backend available")
    
    backend = backends[0]
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(f"{backend.base_url}/system_stats")
        return response.json()


@router.get("/embeddings")
async def get_embeddings(request: Request) -> list:
    """获取embeddings列表 - 代理到后端"""
    state = get_app_state(request)
    
    backends = state.backend_manager.get_healthy_backends()
    if not backends:
        raise HTTPException(status_code=503, detail="No healthy backend available")
    
    backend = backends[0]
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(f"{backend.base_url}/embeddings")
        return response.json()


@router.get("/extensions")
async def get_extensions(request: Request) -> list:
    """获取扩展列表 - 代理到后端"""
    state = get_app_state(request)
    
    backends = state.backend_manager.get_healthy_backends()
    if not backends:
        raise HTTPException(status_code=503, detail="No healthy backend available")
    
    backend = backends[0]
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(f"{backend.base_url}/extensions")
        return response.json()


@router.get("/view")
async def view_image(
    request: Request, 
    filename: str, 
    subfolder: str = "", 
    type: str = "output",
    backend: Optional[str] = None
) -> Response:
    """获取/预览图像 - 代理到后端"""
    state = get_app_state(request)
    
    # 如果指定了后端,直接使用
    if backend:
        backend_obj = state.backend_manager.get_backend(backend)
    else:
        # 如果未指定,尝试从所有健康后端中搜索(这里简单处理,默认取第一个或基于其它逻辑)
        # 实际生产中,客户端应该根据history中的信息知道去哪个后端取,或者LB全局维护文件索引
        backends = state.backend_manager.get_healthy_backends()
        if not backends:
            raise HTTPException(status_code=503, detail="No healthy backend available")
        backend_obj = backends[0]
        
    if not backend_obj:
        raise HTTPException(status_code=404, detail=f"Backend {backend} not found")
        
    params = {
        "filename": filename,
        "subfolder": subfolder,
        "type": type
    }
    
    # 代理请求到后端
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.get(f"{backend_obj.base_url}/view", params=params)
            
            if response.status_code != 200:
                return Response(
                    content=response.content, 
                    status_code=response.status_code,
                    media_type=response.headers.get("content-type")
                )
            
            return Response(
                content=response.content,
                status_code=response.status_code,
                media_type=response.headers.get("content-type"),
                headers={k: v for k, v in response.headers.items() if k.lower() not in ["content-length", "content-encoding"]}
            )
        except Exception as e:
            logger.error(f"代理图像请求失败: {e}")
            raise HTTPException(status_code=502, detail=f"Failed to fetch image from backend: {e}")


# ============ 负载均衡器管理 API ============

@router.get("/lb/stats", response_model=SystemStats)
async def get_lb_stats(request: Request) -> SystemStats:
    """获取负载均衡器统计信息"""
    state = get_app_state(request)
    
    backends = state.backend_manager.get_all_backends()
    healthy = state.backend_manager.get_healthy_backends()
    available = state.backend_manager.get_available_backends()
    idle = state.backend_manager.get_idle_backends()
    
    return SystemStats(
        total_backends=len(backends),
        healthy_backends=len(healthy),
        available_backends=len(available),
        idle_backends=len(idle),
        queue_status=state.task_queue.get_status(),
        backends=backends
    )


@router.get("/lb/backends")
async def list_backends(request: Request) -> list[BackendState]:
    """列出所有后端"""
    state = get_app_state(request)
    return state.backend_manager.get_all_backends()


@router.post("/lb/backends")
async def add_backend(request: Request, config: BackendConfig) -> BackendState:
    """添加后端"""
    state = get_app_state(request)
    backend = await state.backend_manager.register_backend(config)
    
    # 同时添加WS桥接
    if backend.enabled:
        await state.ws_manager.add_backend(backend.name, backend.base_url)
        
    # 立即检查健康状态
    await state.backend_manager.check_backend_health(config.name)
    return backend


@router.delete("/lb/backends/{name}")
async def remove_backend(request: Request, name: str) -> dict:
    """移除后端"""
    state = get_app_state(request)
    
    # 同时移除WS桥接
    await state.ws_manager.remove_backend(name)
    
    success = await state.backend_manager.unregister_backend(name)
    if not success:
        raise HTTPException(status_code=404, detail="Backend not found")
    return {"success": True}


@router.post("/lb/backends/{name}/enable")
async def enable_backend(request: Request, name: str) -> dict:
    """启用后端"""
    state = get_app_state(request)
    success = state.backend_manager.enable_backend(name)
    if not success:
        raise HTTPException(status_code=404, detail="Backend not found")
    return {"success": True}


@router.post("/lb/backends/{name}/disable")
async def disable_backend(request: Request, name: str) -> dict:
    """禁用后端"""
    state = get_app_state(request)
    success = state.backend_manager.disable_backend(name)
    if not success:
        raise HTTPException(status_code=404, detail="Backend not found")
    return {"success": True}


@router.get("/lb/tasks")
async def list_tasks(request: Request) -> dict:
    """列出所有任务"""
    state = get_app_state(request)
    return state.task_queue.get_all_tasks()


@router.get("/lb/tasks/{task_id}")
async def get_task(request: Request, task_id: str) -> Task:
    """获取任务详情"""
    state = get_app_state(request)
    task = state.task_queue.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.delete("/lb/tasks/{task_id}")
async def cancel_task(request: Request, task_id: str) -> dict:
    """取消任务"""
    state = get_app_state(request)
    success = await state.task_queue.cancel_task(task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"success": True}


@router.post("/lb/health-check")
async def trigger_health_check(request: Request) -> dict:
    """触发健康检查"""
    state = get_app_state(request)
    await state.health_checker.check_now()
    return {"success": True}


@router.get("/lb/scheduler")
async def get_scheduler_info(request: Request) -> dict:
    """获取调度器信息"""
    state = get_app_state(request)
    return {
        "strategy": state.scheduler.strategy_name,
        "prefer_idle": state.scheduler.prefer_idle,
        "has_available_backend": state.scheduler.has_available_backend(),
        "has_idle_backend": state.scheduler.has_idle_backend()
    }


@router.post("/lb/scheduler/strategy/{strategy}")
async def set_scheduler_strategy(request: Request, strategy: str) -> dict:
    """设置调度策略"""
    state = get_app_state(request)
    valid_strategies = ["least_busy", "round_robin", "weighted"]
    if strategy not in valid_strategies:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid strategy. Must be one of: {valid_strategies}"
        )
    state.scheduler.set_strategy(strategy)
    return {"success": True, "strategy": strategy}


