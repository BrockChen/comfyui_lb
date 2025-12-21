"""
Kong 网关管理 API 路由
"""
import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from kong_manager import KongError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/kong", tags=["Kong Gateway"])


def get_kong_manager(request: Request):
    """获取 Kong 管理器"""
    kong = getattr(request.app.state, "kong_manager", None)
    if not kong:
        raise HTTPException(status_code=503, detail="Kong 管理器未配置")
    return kong


# ============ 请求模型 ============

class ServiceCreate(BaseModel):
    name: str = Field(..., description="服务名称")
    url: str = Field(..., description="上游服务URL")
    retries: Optional[int] = Field(default=5, description="重试次数")
    connect_timeout: Optional[int] = Field(default=60000, description="连接超时(ms)")
    write_timeout: Optional[int] = Field(default=60000, description="写超时(ms)")
    read_timeout: Optional[int] = Field(default=60000, description="读超时(ms)")


class ServiceUpdate(BaseModel):
    url: Optional[str] = None
    retries: Optional[int] = None
    connect_timeout: Optional[int] = None
    write_timeout: Optional[int] = None
    read_timeout: Optional[int] = None
    enabled: Optional[bool] = None


class RouteCreate(BaseModel):
    name: str = Field(..., description="路由名称")
    paths: Optional[list[str]] = Field(default=None, description="路径列表")
    hosts: Optional[list[str]] = Field(default=None, description="主机列表")
    methods: Optional[list[str]] = Field(default=None, description="HTTP方法列表")
    strip_path: bool = Field(default=True, description="是否去除路径前缀")
    preserve_host: bool = Field(default=False, description="是否保留原始Host")


class RouteUpdate(BaseModel):
    paths: Optional[list[str]] = None
    hosts: Optional[list[str]] = None
    methods: Optional[list[str]] = None
    strip_path: Optional[bool] = None
    preserve_host: Optional[bool] = None


class PluginCreate(BaseModel):
    name: str = Field(..., description="插件名称")
    config: Optional[dict] = Field(default=None, description="插件配置")
    enabled: bool = Field(default=True, description="是否启用")


class PluginUpdate(BaseModel):
    config: Optional[dict] = None
    enabled: Optional[bool] = None


class ConsumerCreate(BaseModel):
    username: str = Field(..., description="用户名")
    custom_id: Optional[str] = Field(default=None, description="自定义ID")


class KeyAuthCreate(BaseModel):
    key: Optional[str] = Field(default=None, description="API密钥，不填则自动生成")


class QuickSetup(BaseModel):
    service_name: str = Field(..., description="服务名称")
    upstream_url: str = Field(..., description="上游URL")
    route_path: str = Field(..., description="路由路径")
    enable_key_auth: bool = Field(default=False, description="是否启用密钥认证")


# ============ Kong 状态 ============

@router.get("/status")
async def get_kong_status(request: Request) -> dict:
    """获取 Kong 状态"""
    kong = get_kong_manager(request)
    try:
        info = await kong.get_info()
        status = await kong.get_status()
        return {
            "connected": True,
            "admin_url": kong.admin_url,
            "version": info.get("version", "unknown"),
            "info": info,
            "status": status
        }
    except Exception as e:
        return {
            "connected": False,
            "admin_url": kong.admin_url,
            "error": str(e)
        }


# ============ Services ============

@router.get("/services")
async def list_services(request: Request) -> dict:
    """列出所有服务"""
    kong = get_kong_manager(request)
    try:
        return await kong.list_services()
    except KongError as e:
        raise HTTPException(status_code=e.status_code or 500, detail=e.message)


@router.get("/services/{name_or_id}")
async def get_service(request: Request, name_or_id: str) -> dict:
    """获取服务详情"""
    kong = get_kong_manager(request)
    try:
        return await kong.get_service(name_or_id)
    except KongError as e:
        raise HTTPException(status_code=e.status_code or 500, detail=e.message)


@router.post("/services")
async def create_service(request: Request, body: ServiceCreate) -> dict:
    """创建服务"""
    kong = get_kong_manager(request)
    try:
        return await kong.create_service(**body.model_dump(exclude_none=True))
    except KongError as e:
        raise HTTPException(status_code=e.status_code or 500, detail=e.message)


@router.patch("/services/{name_or_id}")
async def update_service(request: Request, name_or_id: str, body: ServiceUpdate) -> dict:
    """更新服务"""
    kong = get_kong_manager(request)
    try:
        return await kong.update_service(name_or_id, **body.model_dump(exclude_none=True))
    except KongError as e:
        raise HTTPException(status_code=e.status_code or 500, detail=e.message)


@router.delete("/services/{name_or_id}")
async def delete_service(request: Request, name_or_id: str) -> dict:
    """删除服务"""
    kong = get_kong_manager(request)
    try:
        await kong.delete_service(name_or_id)
        return {"success": True, "message": f"服务 {name_or_id} 已删除"}
    except KongError as e:
        raise HTTPException(status_code=e.status_code or 500, detail=e.message)


# ============ Routes ============

@router.get("/routes")
async def list_routes(request: Request, service: Optional[str] = None) -> dict:
    """列出路由"""
    kong = get_kong_manager(request)
    try:
        return await kong.list_routes(service)
    except KongError as e:
        raise HTTPException(status_code=e.status_code or 500, detail=e.message)


@router.get("/routes/{name_or_id}")
async def get_route(request: Request, name_or_id: str) -> dict:
    """获取路由详情"""
    kong = get_kong_manager(request)
    try:
        return await kong.get_route(name_or_id)
    except KongError as e:
        raise HTTPException(status_code=e.status_code or 500, detail=e.message)


@router.post("/services/{service_name}/routes")
async def create_route(request: Request, service_name: str, body: RouteCreate) -> dict:
    """创建路由"""
    kong = get_kong_manager(request)
    try:
        return await kong.create_route(service_name, **body.model_dump(exclude_none=True))
    except KongError as e:
        raise HTTPException(status_code=e.status_code or 500, detail=e.message)


@router.patch("/routes/{name_or_id}")
async def update_route(request: Request, name_or_id: str, body: RouteUpdate) -> dict:
    """更新路由"""
    kong = get_kong_manager(request)
    try:
        return await kong.update_route(name_or_id, **body.model_dump(exclude_none=True))
    except KongError as e:
        raise HTTPException(status_code=e.status_code or 500, detail=e.message)


@router.delete("/routes/{name_or_id}")
async def delete_route(request: Request, name_or_id: str) -> dict:
    """删除路由"""
    kong = get_kong_manager(request)
    try:
        await kong.delete_route(name_or_id)
        return {"success": True, "message": f"路由 {name_or_id} 已删除"}
    except KongError as e:
        raise HTTPException(status_code=e.status_code or 500, detail=e.message)


# ============ Plugins ============

@router.get("/plugins")
async def list_plugins(request: Request, service: Optional[str] = None, route: Optional[str] = None) -> dict:
    """列出插件"""
    kong = get_kong_manager(request)
    try:
        return await kong.list_plugins(service, route)
    except KongError as e:
        raise HTTPException(status_code=e.status_code or 500, detail=e.message)


@router.get("/plugins/{plugin_id}")
async def get_plugin(request: Request, plugin_id: str) -> dict:
    """获取插件详情"""
    kong = get_kong_manager(request)
    try:
        return await kong.get_plugin(plugin_id)
    except KongError as e:
        raise HTTPException(status_code=e.status_code or 500, detail=e.message)


@router.post("/services/{service_name}/plugins")
async def create_service_plugin(request: Request, service_name: str, body: PluginCreate) -> dict:
    """为服务创建插件"""
    kong = get_kong_manager(request)
    try:
        return await kong.create_plugin(
            body.name,
            service_name=service_name,
            config=body.config,
            enabled=body.enabled
        )
    except KongError as e:
        raise HTTPException(status_code=e.status_code or 500, detail=e.message)


@router.post("/routes/{route_name}/plugins")
async def create_route_plugin(request: Request, route_name: str, body: PluginCreate) -> dict:
    """为路由创建插件"""
    kong = get_kong_manager(request)
    try:
        return await kong.create_plugin(
            body.name,
            route_name=route_name,
            config=body.config,
            enabled=body.enabled
        )
    except KongError as e:
        raise HTTPException(status_code=e.status_code or 500, detail=e.message)


@router.patch("/plugins/{plugin_id}")
async def update_plugin(request: Request, plugin_id: str, body: PluginUpdate) -> dict:
    """更新插件"""
    kong = get_kong_manager(request)
    try:
        return await kong.update_plugin(plugin_id, **body.model_dump(exclude_none=True))
    except KongError as e:
        raise HTTPException(status_code=e.status_code or 500, detail=e.message)


@router.delete("/plugins/{plugin_id}")
async def delete_plugin(request: Request, plugin_id: str) -> dict:
    """删除插件"""
    kong = get_kong_manager(request)
    try:
        await kong.delete_plugin(plugin_id)
        return {"success": True, "message": f"插件 {plugin_id} 已删除"}
    except KongError as e:
        raise HTTPException(status_code=e.status_code or 500, detail=e.message)


# ============ Consumers ============

@router.get("/consumers")
async def list_consumers(request: Request) -> dict:
    """列出所有消费者"""
    kong = get_kong_manager(request)
    try:
        return await kong.list_consumers()
    except KongError as e:
        raise HTTPException(status_code=e.status_code or 500, detail=e.message)


@router.get("/consumers/{username_or_id}")
async def get_consumer(request: Request, username_or_id: str) -> dict:
    """获取消费者详情"""
    kong = get_kong_manager(request)
    try:
        return await kong.get_consumer(username_or_id)
    except KongError as e:
        raise HTTPException(status_code=e.status_code or 500, detail=e.message)


@router.post("/consumers")
async def create_consumer(request: Request, body: ConsumerCreate) -> dict:
    """创建消费者"""
    kong = get_kong_manager(request)
    try:
        return await kong.create_consumer(**body.model_dump(exclude_none=True))
    except KongError as e:
        raise HTTPException(status_code=e.status_code or 500, detail=e.message)


@router.delete("/consumers/{username_or_id}")
async def delete_consumer(request: Request, username_or_id: str) -> dict:
    """删除消费者"""
    kong = get_kong_manager(request)
    try:
        await kong.delete_consumer(username_or_id)
        return {"success": True, "message": f"消费者 {username_or_id} 已删除"}
    except KongError as e:
        raise HTTPException(status_code=e.status_code or 500, detail=e.message)


# ============ Key-Auth ============

@router.get("/consumers/{username}/key-auth")
async def list_consumer_keys(request: Request, username: str) -> dict:
    """列出消费者的所有密钥"""
    kong = get_kong_manager(request)
    try:
        return await kong.list_consumer_keys(username)
    except KongError as e:
        raise HTTPException(status_code=e.status_code or 500, detail=e.message)


@router.post("/consumers/{username}/key-auth")
async def create_consumer_key(request: Request, username: str, body: KeyAuthCreate = None) -> dict:
    """为消费者创建密钥"""
    kong = get_kong_manager(request)
    try:
        key = body.key if body else None
        return await kong.create_consumer_key(username, key)
    except KongError as e:
        raise HTTPException(status_code=e.status_code or 500, detail=e.message)


@router.delete("/consumers/{username}/key-auth/{key_id}")
async def delete_consumer_key(request: Request, username: str, key_id: str) -> dict:
    """删除消费者密钥"""
    kong = get_kong_manager(request)
    try:
        await kong.delete_consumer_key(username, key_id)
        return {"success": True, "message": f"密钥 {key_id} 已删除"}
    except KongError as e:
        raise HTTPException(status_code=e.status_code or 500, detail=e.message)


# ============ 快捷操作 ============

@router.post("/quick-setup")
async def quick_setup(request: Request, body: QuickSetup) -> dict:
    """快速设置 ComfyUI 服务"""
    kong = get_kong_manager(request)
    try:
        return await kong.setup_comfyui_service(
            service_name=body.service_name,
            upstream_url=body.upstream_url,
            route_path=body.route_path,
            enable_key_auth=body.enable_key_auth
        )
    except KongError as e:
        raise HTTPException(status_code=e.status_code or 500, detail=e.message)

