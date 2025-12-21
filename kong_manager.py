"""
Kong 网关管理器
支持 Services、Routes、Plugins、Consumers 的增删改查
"""
import logging
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


class KongManager:
    """Kong 网关管理器"""
    
    def __init__(self, admin_url: str = "http://127.0.0.1:8001", timeout: float = 10.0):
        self.admin_url = admin_url.rstrip("/")
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
    
    async def initialize(self):
        """初始化"""
        self._client = httpx.AsyncClient(timeout=self.timeout)
        logger.info(f"Kong 管理器已初始化: {self.admin_url}")
    
    async def shutdown(self):
        """关闭"""
        if self._client:
            await self._client.aclose()
    
    async def _request(self, method: str, path: str, **kwargs) -> dict:
        """发送请求"""
        url = f"{self.admin_url}{path}"
        try:
            response = await self._client.request(method, url, **kwargs)
            if response.status_code == 204:
                return {"success": True}
            if response.status_code >= 400:
                error_data = response.json() if response.content else {}
                raise KongError(response.status_code, error_data.get("message", response.text))
            return response.json() if response.content else {"success": True}
        except httpx.RequestError as e:
            raise KongError(0, f"连接 Kong 失败: {e}")
    
    # ============ Services ============
    
    async def list_services(self) -> dict:
        """列出所有服务"""
        return await self._request("GET", "/services")
    
    async def get_service(self, name_or_id: str) -> dict:
        """获取服务详情"""
        return await self._request("GET", f"/services/{name_or_id}")
    
    async def create_service(self, name: str, url: str, **kwargs) -> dict:
        """
        创建服务
        
        Args:
            name: 服务名称
            url: 上游服务URL
            **kwargs: 其他参数 (retries, connect_timeout, write_timeout, read_timeout, etc.)
        """
        data = {"name": name, "url": url, **kwargs}
        return await self._request("POST", "/services", data=data)
    
    async def update_service(self, name_or_id: str, **kwargs) -> dict:
        """更新服务"""
        return await self._request("PATCH", f"/services/{name_or_id}", data=kwargs)
    
    async def delete_service(self, name_or_id: str) -> dict:
        """删除服务"""
        return await self._request("DELETE", f"/services/{name_or_id}")
    
    # ============ Routes ============
    
    async def list_routes(self, service_name: Optional[str] = None) -> dict:
        """列出路由"""
        if service_name:
            return await self._request("GET", f"/services/{service_name}/routes")
        return await self._request("GET", "/routes")
    
    async def get_route(self, name_or_id: str) -> dict:
        """获取路由详情"""
        return await self._request("GET", f"/routes/{name_or_id}")
    
    async def create_route(
        self, 
        service_name: str, 
        name: str,
        paths: Optional[list[str]] = None,
        hosts: Optional[list[str]] = None,
        methods: Optional[list[str]] = None,
        strip_path: bool = True,
        **kwargs
    ) -> dict:
        """
        创建路由
        
        Args:
            service_name: 服务名称
            name: 路由名称
            paths: 路径列表
            hosts: 主机列表
            methods: HTTP方法列表
            strip_path: 是否去除路径前缀
            **kwargs: 其他参数
        """
        data = {"name": name, "strip_path": strip_path, **kwargs}
        if paths:
            data["paths"] = paths
        if hosts:
            data["hosts"] = hosts
        if methods:
            data["methods"] = methods
        return await self._request("POST", f"/services/{service_name}/routes", json=data)
    
    async def update_route(self, name_or_id: str, **kwargs) -> dict:
        """更新路由"""
        return await self._request("PATCH", f"/routes/{name_or_id}", json=kwargs)
    
    async def delete_route(self, name_or_id: str) -> dict:
        """删除路由"""
        return await self._request("DELETE", f"/routes/{name_or_id}")
    
    # ============ Plugins ============
    
    async def list_plugins(self, service_name: Optional[str] = None, route_name: Optional[str] = None) -> dict:
        """列出插件"""
        if service_name:
            return await self._request("GET", f"/services/{service_name}/plugins")
        if route_name:
            return await self._request("GET", f"/routes/{route_name}/plugins")
        return await self._request("GET", "/plugins")
    
    async def get_plugin(self, plugin_id: str) -> dict:
        """获取插件详情"""
        return await self._request("GET", f"/plugins/{plugin_id}")
    
    async def create_plugin(
        self,
        name: str,
        service_name: Optional[str] = None,
        route_name: Optional[str] = None,
        config: Optional[dict] = None,
        enabled: bool = True,
        **kwargs
    ) -> dict:
        """
        创建插件
        
        Args:
            name: 插件名称 (key-auth, rate-limiting, cors, etc.)
            service_name: 关联的服务名称
            route_name: 关联的路由名称
            config: 插件配置
            enabled: 是否启用
        """
        data = {"name": name, "enabled": enabled, **kwargs}
        if config:
            data["config"] = config
        
        if service_name:
            return await self._request("POST", f"/services/{service_name}/plugins", json=data)
        if route_name:
            return await self._request("POST", f"/routes/{route_name}/plugins", json=data)
        return await self._request("POST", "/plugins", json=data)
    
    async def update_plugin(self, plugin_id: str, **kwargs) -> dict:
        """更新插件"""
        return await self._request("PATCH", f"/plugins/{plugin_id}", json=kwargs)
    
    async def delete_plugin(self, plugin_id: str) -> dict:
        """删除插件"""
        return await self._request("DELETE", f"/plugins/{plugin_id}")
    
    # ============ Consumers ============
    
    async def list_consumers(self) -> dict:
        """列出所有消费者"""
        return await self._request("GET", "/consumers")
    
    async def get_consumer(self, username_or_id: str) -> dict:
        """获取消费者详情"""
        return await self._request("GET", f"/consumers/{username_or_id}")
    
    async def create_consumer(self, username: str, custom_id: Optional[str] = None, **kwargs) -> dict:
        """创建消费者"""
        data = {"username": username, **kwargs}
        if custom_id:
            data["custom_id"] = custom_id
        return await self._request("POST", "/consumers", data=data)
    
    async def update_consumer(self, username_or_id: str, **kwargs) -> dict:
        """更新消费者"""
        return await self._request("PATCH", f"/consumers/{username_or_id}", data=kwargs)
    
    async def delete_consumer(self, username_or_id: str) -> dict:
        """删除消费者"""
        return await self._request("DELETE", f"/consumers/{username_or_id}")
    
    # ============ Key-Auth ============
    
    async def list_consumer_keys(self, username: str) -> dict:
        """列出消费者的所有密钥"""
        return await self._request("GET", f"/consumers/{username}/key-auth")
    
    async def create_consumer_key(self, username: str, key: Optional[str] = None) -> dict:
        """
        为消费者创建密钥
        
        Args:
            username: 消费者用户名
            key: 指定密钥值，不指定则自动生成
        """
        data = {}
        if key:
            data["key"] = key
        return await self._request("POST", f"/consumers/{username}/key-auth", data=data)
    
    async def delete_consumer_key(self, username: str, key_id: str) -> dict:
        """删除消费者密钥"""
        return await self._request("DELETE", f"/consumers/{username}/key-auth/{key_id}")
    
    # ============ 状态检查 ============
    
    async def get_status(self) -> dict:
        """获取 Kong 状态"""
        try:
            return await self._request("GET", "/status")
        except Exception:
            return {"status": "unreachable"}
    
    async def get_info(self) -> dict:
        """获取 Kong 信息"""
        try:
            return await self._request("GET", "/")
        except Exception:
            return {"status": "unreachable"}
    
    # ============ 便捷方法 ============
    
    async def setup_comfyui_service(
        self,
        service_name: str,
        upstream_url: str,
        route_path: str,
        enable_key_auth: bool = False
    ) -> dict:
        """
        快速设置 ComfyUI 服务
        
        Args:
            service_name: 服务名称
            upstream_url: 上游URL (如 http://127.0.0.1:8188)
            route_path: 路由路径 (如 /comfyui)
            enable_key_auth: 是否启用 key-auth 插件
        """
        result = {"service": None, "route": None, "plugin": None}
        
        # 创建服务
        try:
            result["service"] = await self.create_service(service_name, upstream_url)
        except KongError as e:
            if "unique constraint" in str(e).lower() or "already exists" in str(e).lower():
                result["service"] = await self.get_service(service_name)
            else:
                raise
        
        # 创建路由
        try:
            result["route"] = await self.create_route(
                service_name,
                name=service_name,
                paths=[route_path],
                strip_path=True
            )
        except KongError as e:
            if "unique constraint" in str(e).lower() or "already exists" in str(e).lower():
                result["route"] = await self.get_route(service_name)
            else:
                raise
        
        # 启用 key-auth
        if enable_key_auth:
            try:
                result["plugin"] = await self.create_plugin("key-auth", service_name=service_name)
            except KongError:
                pass  # 插件可能已存在
        
        return result


class KongError(Exception):
    """Kong API 错误"""
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"Kong Error ({status_code}): {message}")

