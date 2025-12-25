"""
Kong API Gateway 管理器
"""
import logging
from typing import Optional, Dict, Any, List
import httpx

logger = logging.getLogger(__name__)


class KongManager:
    """Kong Admin API 客户端"""
    
    def __init__(self, admin_url: str, timeout: float = 10.0):
        self.admin_url = admin_url.rstrip('/')
        self.timeout = timeout
        self.client: Optional[httpx.AsyncClient] = None
        self._connected = False
        self._version = None
    
    async def initialize(self):
        """初始化并验证 Kong 连接"""
        self.client = httpx.AsyncClient(timeout=self.timeout)
        try:
            response = await self.client.get(f"{self.admin_url}/")
            if response.status_code == 200:
                data = response.json()
                self._version = data.get("version", "unknown")
                self._connected = True
                logger.info(f"Kong 连接成功: {self._version} (Admin URL: {self.admin_url})")
            else:
                self._connected = False
                logger.warning(f"Kong 连接失败: HTTP {response.status_code} (Admin URL: {self.admin_url})")
        except httpx.ConnectError as e:
            self._connected = False
            logger.error(f"Kong 初始化失败 - 无法连接: {self.admin_url}. 错误: {e}")
            logger.error("提示: 如果应用在 Docker 容器中运行，请使用 'http://kong:8001' 而不是 'http://localhost:8001'")
        except httpx.TimeoutException as e:
            self._connected = False
            logger.error(f"Kong 初始化失败 - 连接超时: {self.admin_url}. 错误: {e}")
        except Exception as e:
            self._connected = False
            logger.error(f"Kong 初始化失败: {e} (Admin URL: {self.admin_url})")
    
    async def shutdown(self):
        """关闭连接"""
        if self.client:
            await self.client.aclose()
    
    @property
    def is_connected(self) -> bool:
        """是否已连接"""
        return self._connected
    
    @property
    def version(self) -> Optional[str]:
        """Kong 版本"""
        return self._version
    
    # ============ Services ============
    
    async def get_services(self) -> Dict[str, Any]:
        """获取所有服务"""
        if not self.client:
            raise RuntimeError("Kong client not initialized")
        
        if not self._connected:
            raise RuntimeError(f"Kong not connected. Admin URL: {self.admin_url}")
        
        try:
            response = await self.client.get(f"{self.admin_url}/services")
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError as e:
            logger.error(f"无法连接到 Kong Admin API ({self.admin_url}): {e}")
            raise RuntimeError(f"无法连接到 Kong Admin API: {self.admin_url}. 请检查 Kong 服务是否运行。") from e
        except httpx.TimeoutException as e:
            logger.error(f"连接 Kong Admin API 超时 ({self.admin_url}): {e}")
            raise RuntimeError(f"连接 Kong Admin API 超时: {self.admin_url}") from e
        except httpx.HTTPStatusError as e:
            logger.error(f"Kong Admin API 返回错误状态码: {e.response.status_code}")
            raise RuntimeError(f"Kong Admin API 错误: {e.response.status_code} - {e.response.text}") from e
        except Exception as e:
            logger.error(f"获取服务列表失败: {e}")
            raise RuntimeError(f"获取服务列表失败: {str(e)}") from e
    
    async def create_service(self, name: str, url: str, **kwargs) -> Dict[str, Any]:
        """创建服务"""
        if not self.client:
            raise RuntimeError("Kong client not initialized")
        
        data = {"name": name, "url": url, **kwargs}
        response = await self.client.post(
            f"{self.admin_url}/services",
            json=data
        )
        response.raise_for_status()
        return response.json()
    
    async def delete_service(self, service_id: str) -> bool:
        """删除服务"""
        if not self.client:
            raise RuntimeError("Kong client not initialized")
        
        response = await self.client.delete(
            f"{self.admin_url}/services/{service_id}"
        )
        return response.status_code == 204
    
    # ============ Routes ============
    
    async def get_routes(self, service_id: Optional[str] = None) -> Dict[str, Any]:
        """获取路由"""
        if not self.client:
            raise RuntimeError("Kong client not initialized")
        
        if service_id:
            url = f"{self.admin_url}/services/{service_id}/routes"
        else:
            url = f"{self.admin_url}/routes"
        
        response = await self.client.get(url)
        response.raise_for_status()
        return response.json()
    
    async def create_route(
        self, 
        service_id: str, 
        paths: List[str],
        name: Optional[str] = None,
        protocols: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """创建路由"""
        if not self.client:
            raise RuntimeError("Kong client not initialized")
        
        data = {"paths": paths, **kwargs}
        if name:
            data["name"] = name
        if protocols:
            data["protocols"] = protocols
        
        try:
            response = await self.client.post(
                f"{self.admin_url}/services/{service_id}/routes",
                json=data
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            # 尝试获取详细的错误信息
            error_detail = "Unknown error"
            try:
                error_data = e.response.json()
                if isinstance(error_data, dict):
                    if "message" in error_data:
                        error_detail = error_data["message"]
                    elif "fields" in error_data:
                        # Kong 返回字段错误
                        fields_errors = []
                        for field, errors in error_data["fields"].items():
                            if isinstance(errors, list):
                                fields_errors.append(f"{field}: {', '.join(errors)}")
                            else:
                                fields_errors.append(f"{field}: {errors}")
                        error_detail = "; ".join(fields_errors) if fields_errors else str(error_data)
                    else:
                        error_detail = str(error_data)
                else:
                    error_detail = e.response.text[:500]  # 限制长度
            except:
                error_detail = e.response.text[:500] if e.response.text else f"HTTP {e.response.status_code}"
            
            logger.error(f"Kong API 错误 ({e.response.status_code}): {error_detail}")
            raise RuntimeError(f"Kong API 错误 ({e.response.status_code}): {error_detail}") from e
        except httpx.RequestError as e:
            logger.error(f"请求 Kong API 失败: {e}")
            raise RuntimeError(f"请求 Kong API 失败: {e}") from e
    
    async def delete_route(self, route_id: str) -> bool:
        """删除路由"""
        if not self.client:
            raise RuntimeError("Kong client not initialized")
        
        response = await self.client.delete(
            f"{self.admin_url}/routes/{route_id}"
        )
        response.raise_for_status()
        return response.status_code == 204
    
    # ============ Plugins ============
    
    async def get_plugins(self) -> Dict[str, Any]:
        """获取所有插件"""
        if not self.client:
            raise RuntimeError("Kong client not initialized")
        
        response = await self.client.get(f"{self.admin_url}/plugins")
        response.raise_for_status()
        return response.json()
    
    async def create_plugin(
        self,
        name: str,
        service_id: Optional[str] = None,
        route_id: Optional[str] = None,
        consumer_id: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """创建插件"""
        if not self.client:
            raise RuntimeError("Kong client not initialized")
        
        data = {"name": name, **kwargs}
        
        if service_id:
            data["service"] = {"id": service_id}
        if route_id:
            data["route"] = {"id": route_id}
        if consumer_id:
            data["consumer"] = {"id": consumer_id}
        if config:
            data["config"] = config
        
        response = await self.client.post(
            f"{self.admin_url}/plugins",
            json=data
        )
        response.raise_for_status()
        return response.json()
    
    async def delete_plugin(self, plugin_id: str) -> bool:
        """删除插件"""
        if not self.client:
            raise RuntimeError("Kong client not initialized")
        
        response = await self.client.delete(
            f"{self.admin_url}/plugins/{plugin_id}"
        )
        return response.status_code == 204
    
    # ============ Consumers ============
    
    async def get_consumers(self) -> Dict[str, Any]:
        """获取所有消费者"""
        if not self.client:
            raise RuntimeError("Kong client not initialized")
        
        response = await self.client.get(f"{self.admin_url}/consumers")
        response.raise_for_status()
        return response.json()
    
    async def create_consumer(self, username: str, **kwargs) -> Dict[str, Any]:
        """创建消费者"""
        if not self.client:
            raise RuntimeError("Kong client not initialized")
        
        data = {"username": username, **kwargs}
        response = await self.client.post(
            f"{self.admin_url}/consumers",
            json=data
        )
        response.raise_for_status()
        return response.json()
    
    async def delete_consumer(self, consumer_id: str) -> bool:
        """删除消费者"""
        if not self.client:
            raise RuntimeError("Kong client not initialized")
        
        response = await self.client.delete(
            f"{self.admin_url}/consumers/{consumer_id}"
        )
        return response.status_code == 204
    
    # ============ Credentials (key-auth) ============
    
    async def get_consumer_keys(self, consumer_id: str) -> Dict[str, Any]:
        """获取消费者的 API Key"""
        if not self.client:
            raise RuntimeError("Kong client not initialized")
        
        response = await self.client.get(
            f"{self.admin_url}/consumers/{consumer_id}/key-auth"
        )
        response.raise_for_status()
        return response.json()
    
    async def create_consumer_key(self, consumer_id: str, key: Optional[str] = None) -> Dict[str, Any]:
        """为消费者创建 API Key"""
        if not self.client:
            raise RuntimeError("Kong client not initialized")
        
        data = {}
        if key:
            data["key"] = key
            
        response = await self.client.post(
            f"{self.admin_url}/consumers/{consumer_id}/key-auth",
            json=data
        )
        response.raise_for_status()
        return response.json()
    
    async def delete_consumer_key(self, consumer_id: str, key_id_or_key: str) -> bool:
        """删除消费者的 API Key"""
        if not self.client:
            raise RuntimeError("Kong client not initialized")
        
        response = await self.client.delete(
            f"{self.admin_url}/consumers/{consumer_id}/key-auth/{key_id_or_key}"
        )
        return response.status_code == 204
