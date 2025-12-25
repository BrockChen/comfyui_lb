"""
ComfyUI 负载均衡器 - 主入口
"""
import sys
import logging
import argparse
from contextlib import asynccontextmanager

from pathlib import Path

import uvicorn
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from config import load_config, Settings
from backend_manager import BackendManager
from scheduler import Scheduler
from task_queue import TaskQueue
from health_checker import HealthChecker
from api.routes import router
from api.kong_routes import router as kong_router
from api.websocket import WebSocketManager, websocket_endpoint
from kong_manager import KongManager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


async def dispatch_task(task, app_state) -> bool:
    """
    分发任务到后端
    返回True表示成功分发,False表示没有可用后端
    """
    # 选择后端
    backend = app_state.scheduler.select_backend(task)
    if not backend:
        return False
    
    try:
        # 获取该后端的桥接ID，用于向后端“伪装”身份
        bridge_sid = app_state.ws_manager.get_backend_bridge_id(backend.name)
        
        # 预先记录关联，确保能收到该后端的启动消息
        if task.client_id:
            await app_state.ws_manager.associate_client_with_backend(task.client_id, backend.name)
            
        # 提交到后端 (使用桥接SID以便LB能收到消息)
        result = await app_state.backend_manager.submit_prompt(
            backend.name,
            task.prompt,
            bridge_sid or task.client_id
        )
        
        backend_prompt_id = result.get("prompt_id")
        if backend_prompt_id and task.client_id:
            # 建立由后端任务ID到用户ID的映射
            await app_state.ws_manager.register_prompt(backend_prompt_id, task.client_id, task.id)
            
        await app_state.task_queue.mark_dispatched(task, backend.name, backend_prompt_id)
        
        # 更新后端队列状态
        backend.queue_pending += 1
        
        return True
        
    except Exception as e:
        logger.error(f"分发任务失败: {task.id} -> {backend.name}, 错误: {e}")
        await app_state.task_queue.mark_failed(task, str(e))
        return True  # 返回True因为任务已处理(失败)


async def on_backend_status_change(name: str, is_healthy: bool, app_state):
    """后端状态变化回调"""
    if is_healthy:
        # 后端恢复健康,触发任务分发
        app_state.task_queue.trigger_dispatch()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    settings: Settings = app.state.settings
    
    # 初始化后端管理器
    backend_manager = BackendManager(settings)
    await backend_manager.initialize()
    app.state.backend_manager = backend_manager
    
    # 初始化调度器
    scheduler = Scheduler(
        backend_manager,
        strategy=settings.scheduler.strategy,
        prefer_idle=settings.scheduler.prefer_idle
    )
    app.state.scheduler = scheduler
    
    # 初始化WebSocket管理器
    ws_manager = WebSocketManager()
    app.state.ws_manager = ws_manager

    # 初始化后端WS桥接
    for backend_config in settings.backends:
        if backend_config.enabled:
            await ws_manager.add_backend(backend_config.name, backend_config.base_url)

    # 初始化任务队列
    task_queue = TaskQueue(settings, ws_manager)
    app.state.task_queue = task_queue
    
    # 设置分发回调
    async def dispatch_callback(task):
        return await dispatch_task(task, app.state)
    task_queue.set_dispatch_callback(dispatch_callback)
    
    # 初始化健康检查器
    health_checker = HealthChecker(settings, backend_manager, ws_manager)
    app.state.health_checker = health_checker
    
    # 初始化Kong管理器
    if settings.kong.enabled:
        kong_manager = KongManager(
            admin_url=settings.kong.admin_url,
            timeout=settings.kong.timeout
        )
        await kong_manager.initialize()
        app.state.kong_manager = kong_manager
        logger.info(f"Kong 管理器已启用: {settings.kong.admin_url}")
    else:
        app.state.kong_manager = None
    
    # 启动服务
    await health_checker.start()
    await task_queue.start()
    
    # 初始健康检查
    await health_checker.check_now()
    
    logger.info("=" * 50)
    logger.info("ComfyUI 负载均衡器已启动")
    logger.info(f"监听地址: {settings.server.host}:{settings.server.port}")
    logger.info(f"管理界面: http://localhost:{settings.server.port}/")
    logger.info(f"后端数量: {len(settings.backends)}")
    logger.info(f"调度策略: {settings.scheduler.strategy}")
    logger.info("=" * 50)
    
    yield
    
    # 停止服务
    await task_queue.stop()
    await health_checker.stop()
    await backend_manager.shutdown()
    
    # 关闭Kong管理器
    if app.state.kong_manager:
        await app.state.kong_manager.shutdown()
    
    logger.info("ComfyUI 负载均衡器已停止")


def create_app(settings: Settings = None) -> FastAPI:
    """创建FastAPI应用"""
    if settings is None:
        settings = load_config()
    
    app = FastAPI(
        title="ComfyUI Load Balancer",
        description="ComfyUI 负载均衡器 - 支持多后端任务分发和队列管理",
        version="1.0.0",
        lifespan=lifespan
    )
    
    # 保存设置
    app.state.settings = settings
    
    # 添加CORS中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 注册路由
    app.include_router(router)
    app.include_router(kong_router)
    
    # WebSocket端点
    @app.websocket("/ws")
    async def ws_endpoint(websocket: WebSocket, clientId: str = ""):
        await websocket_endpoint(websocket, clientId)
    
    # 健康检查端点
    @app.get("/health")
    async def health():
        return {"status": "ok"}
    
    # 静态文件和管理界面
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
        
        @app.get("/")
        async def index():
            """管理界面"""
            return FileResponse(static_dir / "index.html")
    
    return app


# 创建全局应用实例
app = create_app()


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(description="ComfyUI 负载均衡器")
    parser.add_argument(
        "-c", "--config",
        type=str,
        default=None,
        help="配置文件路径 (默认: config.yaml)"
    )
    parser.add_argument(
        "-H", "--host",
        type=str,
        default=None,
        help="监听地址 (默认: 0.0.0.0)"
    )
    parser.add_argument(
        "-p", "--port",
        type=int,
        default=None,
        help="监听端口 (默认: 8100)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="调试模式"
    )
    
    args = parser.parse_args()
    
    # 加载配置
    settings = load_config(args.config)
    
    # 命令行参数覆盖
    if args.host:
        settings.server.host = args.host
    if args.port:
        settings.server.port = args.port
    if args.debug:
        settings.server.debug = True
        logging.getLogger().setLevel(logging.DEBUG)
    
    # 更新全局应用
    global app
    app = create_app(settings)
    
    # 启动服务
    uvicorn.run(
        app,
        host=settings.server.host,
        port=settings.server.port,
        log_level="debug" if settings.server.debug else "info"
    )


if __name__ == "__main__":
    main()


