"""
WebSocket 处理 - 代理和聚合多个后端的WebSocket连接
"""
import json
import asyncio
import logging
from typing import Optional

from fastapi import WebSocket, WebSocketDisconnect
import websockets

logger = logging.getLogger(__name__)


class WebSocketManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        self._clients: dict[str, WebSocket] = {}  # client_id -> websocket
        self._backend_connections: dict[str, websockets.WebSocketClientProtocol] = {}
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, client_id: str):
        """接受客户端WebSocket连接"""
        await websocket.accept()
        async with self._lock:
            self._clients[client_id] = websocket
        logger.info(f"WebSocket客户端连接: {client_id}")
    
    async def disconnect(self, client_id: str):
        """断开客户端连接"""
        async with self._lock:
            if client_id in self._clients:
                del self._clients[client_id]
        logger.info(f"WebSocket客户端断开: {client_id}")
    
    async def send_to_client(self, client_id: str, message: dict):
        """发送消息给特定客户端"""
        async with self._lock:
            ws = self._clients.get(client_id)
        
        if ws:
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.warning(f"发送消息失败: {client_id}, {e}")
    
    async def broadcast(self, message: dict):
        """广播消息给所有客户端"""
        async with self._lock:
            clients = list(self._clients.items())
        
        for client_id, ws in clients:
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.warning(f"广播消息失败: {client_id}, {e}")


class BackendWebSocketBridge:
    """后端WebSocket桥接器 - 连接到后端并转发消息"""
    
    def __init__(self, backend_name: str, ws_url: str, manager: WebSocketManager):
        self.backend_name = backend_name
        self.ws_url = ws_url
        self.manager = manager
        self._connection: Optional[websockets.WebSocketClientProtocol] = None
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._client_ids: set[str] = set()  # 关联的客户端
    
    async def start(self):
        """启动桥接"""
        self._running = True
        self._task = asyncio.create_task(self._connection_loop())
    
    async def stop(self):
        """停止桥接"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self._connection:
            await self._connection.close()
    
    def add_client(self, client_id: str):
        """添加关联客户端"""
        self._client_ids.add(client_id)
    
    def remove_client(self, client_id: str):
        """移除关联客户端"""
        self._client_ids.discard(client_id)
    
    async def _connection_loop(self):
        """连接循环"""
        while self._running:
            try:
                async with websockets.connect(self.ws_url) as ws:
                    self._connection = ws
                    logger.info(f"已连接到后端WebSocket: {self.backend_name}")
                    
                    async for message in ws:
                        if not self._running:
                            break
                        await self._handle_message(message)
                        
            except websockets.exceptions.ConnectionClosed:
                logger.warning(f"后端WebSocket连接关闭: {self.backend_name}")
            except Exception as e:
                logger.warning(f"后端WebSocket错误: {self.backend_name}, {e}")
            
            if self._running:
                await asyncio.sleep(1)  # 重连延迟
    
    async def _handle_message(self, message: str):
        """处理后端消息"""
        try:
            data = json.loads(message)
            
            # 添加后端信息
            data["_backend"] = self.backend_name
            
            # 获取目标客户端ID
            target_client_id = data.get("data", {}).get("sid")
            
            if target_client_id and target_client_id in self._client_ids:
                # 发送给特定客户端
                await self.manager.send_to_client(target_client_id, data)
            else:
                # 广播给所有关联客户端
                for client_id in self._client_ids:
                    await self.manager.send_to_client(client_id, data)
                    
        except json.JSONDecodeError:
            logger.warning(f"无效的WebSocket消息: {message[:100]}")
        except Exception as e:
            logger.warning(f"处理WebSocket消息错误: {e}")


async def websocket_endpoint(websocket: WebSocket, client_id: str = ""):
    """WebSocket端点处理"""
    from main import app
    
    if not client_id:
        client_id = str(id(websocket))
    
    manager = app.state.ws_manager
    await manager.connect(websocket, client_id)
    
    try:
        while True:
            # 接收客户端消息(保持连接)
            try:
                data = await websocket.receive_text()
                # 可以处理客户端发送的消息
                logger.debug(f"收到客户端消息: {client_id}, {data[:100]}")
            except WebSocketDisconnect:
                break
    finally:
        await manager.disconnect(client_id)


