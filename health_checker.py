"""
健康检查器
"""
import asyncio
import logging
from typing import Callable, Optional, Awaitable

from config import Settings
from backend_manager import BackendManager

logger = logging.getLogger(__name__)


class HealthChecker:
    """后端健康检查器"""
    
    def __init__(self, settings: Settings, backend_manager: BackendManager):
        self.settings = settings
        self.backend_manager = backend_manager
        self._running = False
        self._check_task: Optional[asyncio.Task] = None
        self._on_status_change: Optional[Callable[[str, bool], Awaitable[None]]] = None
    
    def set_status_change_callback(self, callback: Callable[[str, bool], Awaitable[None]]):
        """设置状态变化回调"""
        self._on_status_change = callback
    
    async def start(self):
        """启动健康检查"""
        self._running = True
        self._check_task = asyncio.create_task(self._check_loop())
        logger.info(f"健康检查已启动, 间隔: {self.settings.health_check.interval}秒")
    
    async def stop(self):
        """停止健康检查"""
        self._running = False
        if self._check_task:
            self._check_task.cancel()
            try:
                await self._check_task
            except asyncio.CancelledError:
                pass
        logger.info("健康检查已停止")
    
    async def _check_loop(self):
        """检查循环"""
        while self._running:
            try:
                await self._do_check()
                await asyncio.sleep(self.settings.health_check.interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"健康检查错误: {e}")
                await asyncio.sleep(self.settings.health_check.interval)
    
    async def _do_check(self):
        """执行健康检查"""
        backends = self.backend_manager.get_all_backends()
        if not backends:
            return
        
        # 记录检查前状态
        old_status = {b.name: b.status for b in backends}
        
        # 并发检查所有后端
        await self.backend_manager.check_all_backends()
        
        # 检查状态变化
        if self._on_status_change:
            for backend in self.backend_manager.get_all_backends():
                if backend.name in old_status:
                    if old_status[backend.name] != backend.status:
                        try:
                            await self._on_status_change(
                                backend.name, 
                                backend.status.value == "healthy"
                            )
                        except Exception as e:
                            logger.warning(f"状态变化回调错误: {e}")
    
    async def check_now(self):
        """立即执行一次检查"""
        await self._do_check()

