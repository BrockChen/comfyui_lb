"""
ComfyUI 后端实例管理器
"""
import asyncio
import logging
from typing import Optional
from datetime import datetime

import httpx

from config import BackendConfig, Settings
from models import BackendState, BackendStatus

logger = logging.getLogger(__name__)


class BackendManager:
    """后端实例管理器"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self._backends: dict[str, BackendState] = {}
        self._http_client: Optional[httpx.AsyncClient] = None
        self._lock = asyncio.Lock()
    
    async def initialize(self):
        """初始化"""
        self._http_client = httpx.AsyncClient(timeout=self.settings.health_check.timeout)
        
        # 注册配置的后端
        for backend_config in self.settings.backends:
            await self.register_backend(backend_config)
    
    async def shutdown(self):
        """关闭"""
        if self._http_client:
            await self._http_client.aclose()
    
    async def register_backend(self, config: BackendConfig) -> BackendState:
        """注册后端实例"""
        async with self._lock:
            state = BackendState(
                name=config.name,
                host=config.host,
                port=config.port,
                base_url=config.base_url,
                enabled=config.enabled,
                weight=config.weight,
                max_queue=config.max_queue,
            )
            self._backends[config.name] = state
            logger.info(f"注册后端: {config.name} ({config.base_url})")
            return state
    
    async def unregister_backend(self, name: str) -> bool:
        """注销后端实例"""
        async with self._lock:
            if name in self._backends:
                del self._backends[name]
                logger.info(f"注销后端: {name}")
                return True
            return False
    
    def get_backend(self, name: str) -> Optional[BackendState]:
        """获取后端状态"""
        return self._backends.get(name)
    
    def get_all_backends(self) -> list[BackendState]:
        """获取所有后端"""
        return list(self._backends.values())
    
    def get_available_backends(self) -> list[BackendState]:
        """获取所有可用后端"""
        return [b for b in self._backends.values() if b.is_available]
    
    def get_idle_backends(self) -> list[BackendState]:
        """获取空闲后端"""
        return [b for b in self._backends.values() if b.is_idle]
    
    def get_healthy_backends(self) -> list[BackendState]:
        """获取健康后端"""
        return [
            b for b in self._backends.values() 
            if b.status == BackendStatus.HEALTHY and b.enabled
        ]
    
    async def check_backend_health(self, name: str) -> bool:
        """检查单个后端健康状态"""
        backend = self._backends.get(name)
        if not backend:
            return False
        
        try:
            # 获取队列状态
            response = await self._http_client.get(f"{backend.base_url}/queue")
            response.raise_for_status()
            queue_data = response.json()
            
            # 解析队列信息
            queue_running = queue_data.get("queue_running", [])
            queue_pending = queue_data.get("queue_pending", [])
            
            async with self._lock:
                backend.queue_running = len(queue_running)
                backend.queue_pending = len(queue_pending)
                backend.last_check = datetime.now()
                backend.consecutive_successes += 1
                backend.consecutive_failures = 0
                
                # 更新健康状态
                if backend.consecutive_successes >= self.settings.health_check.healthy_threshold:
                    if backend.status != BackendStatus.HEALTHY:
                        logger.info(f"后端恢复健康: {name}")
                    backend.status = BackendStatus.HEALTHY
            
            return True
            
        except Exception as e:
            async with self._lock:
                backend.consecutive_failures += 1
                backend.consecutive_successes = 0
                backend.last_check = datetime.now()
                
                # 更新健康状态
                if backend.consecutive_failures >= self.settings.health_check.unhealthy_threshold:
                    if backend.status != BackendStatus.UNHEALTHY:
                        logger.warning(f"后端不健康: {name}, 错误: {e}")
                    backend.status = BackendStatus.UNHEALTHY
            
            return False
    
    async def check_all_backends(self) -> dict[str, bool]:
        """检查所有后端健康状态"""
        results = {}
        tasks = []
        
        for name in self._backends:
            tasks.append(self._check_backend_with_name(name))
        
        if tasks:
            check_results = await asyncio.gather(*tasks, return_exceptions=True)
            for name, result in check_results:
                results[name] = result if isinstance(result, bool) else False
        
        return results
    
    async def _check_backend_with_name(self, name: str) -> tuple[str, bool]:
        """检查后端并返回名称"""
        result = await self.check_backend_health(name)
        return (name, result)
    
    async def submit_prompt(self, backend_name: str, prompt: dict, client_id: Optional[str] = None) -> dict:
        """向后端提交prompt"""
        backend = self._backends.get(backend_name)
        if not backend:
            raise ValueError(f"后端不存在: {backend_name}")
        
        if not backend.is_available:
            raise ValueError(f"后端不可用: {backend_name}")
        
        payload = {"prompt": prompt}
        if client_id:
            payload["client_id"] = client_id
        
        response = await self._http_client.post(
            f"{backend.base_url}/prompt",
            json=payload
        )
        response.raise_for_status()
        return response.json()
    
    async def get_backend_queue(self, backend_name: str) -> dict:
        """获取后端队列状态"""
        backend = self._backends.get(backend_name)
        if not backend:
            raise ValueError(f"后端不存在: {backend_name}")
        
        response = await self._http_client.get(f"{backend.base_url}/queue")
        response.raise_for_status()
        return response.json()
    
    async def get_backend_history(self, backend_name: str, prompt_id: Optional[str] = None) -> dict:
        """获取后端历史记录"""
        backend = self._backends.get(backend_name)
        if not backend:
            raise ValueError(f"后端不存在: {backend_name}")
        
        url = f"{backend.base_url}/history"
        if prompt_id:
            url += f"/{prompt_id}"
        
        response = await self._http_client.get(url)
        response.raise_for_status()
        return response.json()
    
    async def cancel_prompt(self, backend_name: str, prompt_id: str) -> bool:
        """取消后端任务"""
        backend = self._backends.get(backend_name)
        if not backend:
            return False
        
        try:
            response = await self._http_client.post(
                f"{backend.base_url}/queue",
                json={"delete": [prompt_id]}
            )
            return response.status_code == 200
        except Exception:
            return False
    
    def enable_backend(self, name: str) -> bool:
        """启用后端"""
        backend = self._backends.get(name)
        if backend:
            backend.enabled = True
            logger.info(f"启用后端: {name}")
            return True
        return False
    
    def disable_backend(self, name: str) -> bool:
        """禁用后端"""
        backend = self._backends.get(name)
        if backend:
            backend.enabled = False
            logger.info(f"禁用后端: {name}")
            return True
        return False


