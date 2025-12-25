"""
Kong API 路由
"""
import logging
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/kong", tags=["kong"])


class ServiceCreate(BaseModel):
    """创建服务请求"""
    name: str
    url: str


class RouteCreate(BaseModel):
    """创建路由请求"""
    name: Optional[str] = None
    paths: List[str]
    protocols: Optional[List[str]] = None


class PluginCreate(BaseModel):
    """创建插件请求"""
    name: str
    service_id: Optional[str] = None
    route_id: Optional[str] = None
    consumer_id: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


class ConsumerCreate(BaseModel):
    """创建消费者请求"""
    username: str


class KeyCreate(BaseModel):
    """创建 API Key 请求"""
    key: Optional[str] = None


def get_kong_manager(request: Request):
    """获取 Kong 管理器"""
    kong_manager = request.app.state.kong_manager
    if not kong_manager:
        raise HTTPException(status_code=503, detail="Kong integration is disabled")
    return kong_manager


@router.get("/status")
async def get_kong_status(request: Request) -> Dict[str, Any]:
    """获取 Kong 连接状态"""
    kong_manager = get_kong_manager(request)
    
    # 尝试重新连接（如果未连接）
    if not kong_manager.is_connected:
        try:
            await kong_manager.initialize()
        except Exception as e:
            logger.warning(f"重新连接 Kong 失败: {e}")
    
    return {
        "connected": kong_manager.is_connected,
        "version": kong_manager.version,
        "admin_url": kong_manager.admin_url,
        "error": None if kong_manager.is_connected else "Kong 未连接，请检查服务状态和配置"
    }


# ============ Services ============

@router.get("/services")
async def list_services(request: Request) -> Dict[str, Any]:
    """列出所有服务"""
    kong_manager = get_kong_manager(request)
    
    # 检查连接状态
    if not kong_manager.is_connected:
        raise HTTPException(
            status_code=503, 
            detail=f"Kong 未连接。请检查 Kong 服务是否运行，以及 Admin URL 配置是否正确: {kong_manager.admin_url}"
        )
    
    try:
        return await kong_manager.get_services()
    except RuntimeError as e:
        logger.error(f"获取服务列表失败: {e}")
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        logger.error(f"获取服务列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail=f"获取服务列表失败: {str(e)}")


@router.post("/services")
async def create_service(request: Request, service: ServiceCreate) -> Dict[str, Any]:
    """创建服务"""
    kong_manager = get_kong_manager(request)
    try:
        return await kong_manager.create_service(
            name=service.name,
            url=service.url
        )
    except Exception as e:
        logger.error(f"创建服务失败: {e}")
        raise HTTPException(status_code=502, detail=str(e))


@router.delete("/services/{service_id}")
async def delete_service(request: Request, service_id: str) -> Dict[str, bool]:
    """删除服务"""
    kong_manager = get_kong_manager(request)
    try:
        success = await kong_manager.delete_service(service_id)
        return {"success": success}
    except Exception as e:
        logger.error(f"删除服务失败: {e}")
        raise HTTPException(status_code=502, detail=str(e))


# ============ Routes ============

@router.get("/routes")
async def list_routes(request: Request) -> Dict[str, Any]:
    """列出所有路由"""
    kong_manager = get_kong_manager(request)
    try:
        return await kong_manager.get_routes()
    except Exception as e:
        logger.error(f"获取路由列表失败: {e}")
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/services/{service_id}/routes")
async def list_service_routes(request: Request, service_id: str) -> Dict[str, Any]:
    """列出服务的路由"""
    kong_manager = get_kong_manager(request)
    try:
        return await kong_manager.get_routes(service_id)
    except Exception as e:
        logger.error(f"获取服务路由失败: {e}")
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/services/{service_id}/routes")
async def create_route(
    request: Request,
    service_id: str,
    route: RouteCreate
) -> Dict[str, Any]:
    """创建路由"""
    kong_manager = get_kong_manager(request)
    try:
        return await kong_manager.create_route(
            service_id=service_id,
            paths=route.paths,
            name=route.name,
            protocols=route.protocols
        )
    except RuntimeError as e:
        # RuntimeError 包含详细的 Kong API 错误信息
        error_msg = str(e)
        logger.error(f"创建路由失败: {error_msg}")
        # 如果是 400 错误，返回 400 而不是 502
        if "400" in error_msg or "Bad Request" in error_msg:
            raise HTTPException(status_code=400, detail=error_msg)
        raise HTTPException(status_code=502, detail=error_msg)
    except Exception as e:
        logger.error(f"创建路由失败: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail=str(e))


@router.delete("/routes/{route_id}")
async def delete_route(request: Request, route_id: str) -> Dict[str, bool]:
    """删除路由"""
    kong_manager = get_kong_manager(request)
    try:
        success = await kong_manager.delete_route(route_id)
        return {"success": success}
    except Exception as e:
        logger.error(f"删除路由失败: {e}")
        raise HTTPException(status_code=502, detail=str(e))


# ============ Plugins ============

@router.get("/plugins")
async def list_plugins(request: Request) -> Dict[str, Any]:
    """列出所有插件"""
    kong_manager = get_kong_manager(request)
    try:
        return await kong_manager.get_plugins()
    except Exception as e:
        logger.error(f"获取插件列表失败: {e}")
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/plugins")
async def create_plugin(request: Request, plugin: PluginCreate) -> Dict[str, Any]:
    """创建插件"""
    kong_manager = get_kong_manager(request)
    try:
        return await kong_manager.create_plugin(
            name=plugin.name,
            service_id=plugin.service_id,
            route_id=plugin.route_id,
            consumer_id=plugin.consumer_id,
            config=plugin.config
        )
    except Exception as e:
        logger.error(f"创建插件失败: {e}")
        raise HTTPException(status_code=502, detail=str(e))


@router.delete("/plugins/{plugin_id}")
async def delete_plugin(request: Request, plugin_id: str) -> Dict[str, bool]:
    """删除插件"""
    kong_manager = get_kong_manager(request)
    try:
        success = await kong_manager.delete_plugin(plugin_id)
        return {"success": success}
    except Exception as e:
        logger.error(f"删除插件失败: {e}")
        raise HTTPException(status_code=502, detail=str(e))


# ============ Consumers ============

@router.get("/consumers")
async def list_consumers(request: Request) -> Dict[str, Any]:
    """列出所有消费者"""
    kong_manager = get_kong_manager(request)
    try:
        return await kong_manager.get_consumers()
    except Exception as e:
        logger.error(f"获取消费者列表失败: {e}")
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/consumers")
async def create_consumer(request: Request, consumer: ConsumerCreate) -> Dict[str, Any]:
    """创建消费者"""
    kong_manager = get_kong_manager(request)
    try:
        return await kong_manager.create_consumer(username=consumer.username)
    except Exception as e:
        logger.error(f"创建消费者失败: {e}")
        raise HTTPException(status_code=502, detail=str(e))


@router.delete("/consumers/{consumer_id}")
async def delete_consumer(request: Request, consumer_id: str) -> Dict[str, bool]:
    """删除消费者"""
    kong_manager = get_kong_manager(request)
    try:
        success = await kong_manager.delete_consumer(consumer_id)
        return {"success": success}
    except Exception as e:
        logger.error(f"删除消费者失败: {e}")
        raise HTTPException(status_code=502, detail=str(e))


# ============ Credentials (key-auth) ============

@router.get("/consumers/{consumer_id}/keys")
async def list_consumer_keys(request: Request, consumer_id: str) -> Dict[str, Any]:
    """列出消费者的 API Key"""
    kong_manager = get_kong_manager(request)
    try:
        return await kong_manager.get_consumer_keys(consumer_id)
    except Exception as e:
        logger.error(f"获取 API Key 列表失败: {e}")
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/consumers/{consumer_id}/keys")
async def create_consumer_key(
    request: Request, 
    consumer_id: str, 
    key_data: Optional[KeyCreate] = None
) -> Dict[str, Any]:
    """为消费者创建 API Key"""
    kong_manager = get_kong_manager(request)
    try:
        key = key_data.key if key_data else None
        return await kong_manager.create_consumer_key(consumer_id, key)
    except Exception as e:
        logger.error(f"创建 API Key 失败: {e}")
        raise HTTPException(status_code=502, detail=str(e))


@router.delete("/consumers/{consumer_id}/keys/{key_id}")
async def delete_consumer_key(
    request: Request, 
    consumer_id: str, 
    key_id: str
) -> Dict[str, bool]:
    """删除消费者的 API Key"""
    kong_manager = get_kong_manager(request)
    try:
        success = await kong_manager.delete_consumer_key(consumer_id, key_id)
        return {"success": success}
    except Exception as e:
        logger.error(f"删除 API Key 失败: {e}")
        raise HTTPException(status_code=502, detail=str(e))
