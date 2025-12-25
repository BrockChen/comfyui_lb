"""
WebSocket 处理 - 代理和聚合多个后端的WebSocket连接
"""
import json
import asyncio
import logging
from typing import Optional, Any

from fastapi import WebSocket, WebSocketDisconnect
import websockets

logger = logging.getLogger(__name__)


class WebSocketManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        self._clients: dict[str, WebSocket] = {}  # client_id -> websocket
        self._bridges: dict[str, 'BackendWebSocketBridge'] = {} # backend_name -> bridge
        self._client_backends: dict[str, set[str]] = {} # client_id -> set of backend_names
        self._prompt_clients: dict[str, str] = {} # backend_prompt_id -> client_id
        self._prompt_lb_ids: dict[str, str] = {}  # backend_prompt_id -> lb_task_id
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
    
    async def add_backend(self, name: str, base_url: str):
        """添加后端WebSocket桥接"""
        async with self._lock:
            if name in self._bridges:
                return
            
            # 将 http(s):// 转换为 ws(s)://
            ws_url = base_url.replace("http://", "ws://").replace("https://", "wss://") + "/ws"
            bridge = BackendWebSocketBridge(name, ws_url, self)
            self._bridges[name] = bridge
            await bridge.start()
            logger.info(f"启动后端WS桥接: {name} -> {ws_url}")
            
    async def remove_backend(self, name: str):
        """移除后端WebSocket桥接"""
        async with self._lock:
            bridge = self._bridges.pop(name, None)
            if bridge:
                await bridge.stop()
                logger.info(f"停止后端WS桥接: {name}")

    def get_backend_bridge_id(self, name: str) -> Optional[str]:
        """获取后端的桥接客户端ID"""
        bridge = self._bridges.get(name)
        return bridge.bridge_id if bridge else None

    async def associate_client_with_backend(self, client_id: str, backend_name: str):
        """记录客户端正在使用的后端"""
        async with self._lock:
            if client_id not in self._client_backends:
                self._client_backends[client_id] = set()
            self._client_backends[client_id].add(backend_name)
            logger.debug(f"关联客户端 {client_id} -> 后端 {backend_name}")

    async def register_prompt(self, backend_prompt_id: str, client_id: str, lb_task_id: str):
        """记录任务ID与客户端及LB任务ID的关联"""
        async with self._lock:
            self._prompt_clients[backend_prompt_id] = client_id
            self._prompt_lb_ids[backend_prompt_id] = lb_task_id
            logger.debug(f"注册任务关联: 后端ID={backend_prompt_id} -> 客户端={client_id}, LB任务ID={lb_task_id}")
            
    async def get_client_by_prompt(self, backend_prompt_id: str) -> Optional[str]:
        """通过任务ID查找客户端"""
        async with self._lock:
            return self._prompt_clients.get(backend_prompt_id)

    async def get_lb_id_by_prompt(self, backend_prompt_id: str) -> Optional[str]:
        """通过任务ID查找LB任务ID"""
        async with self._lock:
            return self._prompt_lb_ids.get(backend_prompt_id)

    async def send_to_client(self, client_id: str, message: Any):
        """发送消息给特定客户端"""
        async with self._lock:
            ws = self._clients.get(client_id)
        
        if ws:
            try:
                if isinstance(message, dict):
                    await ws.send_json(message)
                else:
                    await ws.send_text(message)
            except Exception as e:
                logger.warning(f"发送消息失败: {client_id}, {e}")
    
    async def broadcast(self, message: Any):
        """广播消息给所有客户端"""
        async with self._lock:
            clients = list(self._clients.items())
        
        for client_id, ws in clients:
            try:
                if isinstance(message, dict):
                    await ws.send_json(message)
                else:
                    await ws.send_text(message)
            except Exception as e:
                logger.warning(f"广播消息失败: {client_id}, {e}")

    async def broadcast_to_backend_users(self, backend_name: str, message: Any):
        """广播给在该后端有活跃任务的客户端"""
        async with self._lock:
            # 找到在该后端有任务的客户端
            target_ids = [
                cid for cid, backends in self._client_backends.items()
                if backend_name in backends and cid in self._clients
            ]
            # 如果没有特定用户，且消息是系统级别的，可以考虑是否广播给所有人
            # 在 ComfyUI 中，系统状态等消息通常对所有人都有意义
            if not target_ids:
                #  fallback: 如果没有人关联，默认不发或者发给所有人？
                # 对于负载均衡器，如果没有人关联该后端，发给所有人可能会造成干扰
                # 但预览图之类如果没有 sid，通常是广播
                target_ids = list(self._clients.keys()) if self._is_system_message(message) else []

        for client_id in target_ids:
            await self.send_to_client(client_id, message)

    def _is_system_message(self, message: Any) -> bool:
        """判断是否为系统级消息 (需要广播或广泛关注的消息)"""
        if isinstance(message, dict):
            m_type = message.get("type", "")
            return m_type in [
                "status", "execution_start", "exec_info", 
                "progress", "executed", "execution_success", "execution_error",
                "executing"
            ]
        return False


class BackendWebSocketBridge:
    """后端WebSocket桥接器 - 连接到后端并转发消息"""
    
    def __init__(self, backend_name: str, ws_url: str, manager: WebSocketManager):
        self.backend_name = backend_name
        # 使用固定ClientId连接后端，确保能收到所有该连接下提交的任务消息
        self.bridge_id = f"LB_BRIDGE_{backend_name}"
        self.url = f"{ws_url}?clientId={self.bridge_id}"
        self.manager = manager
        self._connection: Optional[websockets.WebSocketClientProtocol] = None
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
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
            try:
                await self._connection.close()
            except:
                pass
    
    async def _connection_loop(self):
        """连接循环"""
        logger.info(f"开始后端WS连接循环: {self.backend_name}")
        while self._running:
            try:
                async with websockets.connect(self.url) as ws:
                    self._connection = ws
                    logger.info(f"已连接到后端WebSocket: {self.backend_name}")
                    
                    async for message in ws:
                        if not self._running:
                            break
                        await self._handle_message(message)
                        
            except (websockets.exceptions.ConnectionClosed, ConnectionRefusedError):
                if self._running:
                    logger.debug(f"后端WebSocket连接断开/被拒: {self.backend_name}")
            except Exception as e:
                if self._running:
                    logger.warning(f"后端WebSocket错误: {self.backend_name}, {e}")
            
            if self._running:
                self._connection = None
                await asyncio.sleep(2)  # 重连延迟
    
    async def _handle_message(self, message: Any):
        """处理后端消息"""
        try:
            # logger.debug(f"收到后端WS消息: {self.backend_name}, content={message[:100]}...")
            
            # ComfyUI消息可能是JSON字符串或二进制
            if isinstance(message, str):
                data = json.loads(message)
                m_type = data.get("type")
                m_data = data.get("data", {})
                
                if isinstance(data, dict):
                    data["_backend"] = self.backend_name
                    
                    # 尝试通过 prompt_id 进行路由 (最准确的多路复用方式)
                    prompt_id = m_data.get("prompt_id") if isinstance(m_data, dict) else None
                    target_client_id = None
                    
                    if prompt_id:
                        target_client_id = await self.manager.get_client_by_prompt(prompt_id)
                    
                    # 如果没有 prompt_id，或者没找到关联，尝试通过 sid 路由
                    if not target_client_id:
                        target_client_id = m_data.get("sid") if isinstance(m_data, dict) else data.get("sid")
                        
                    if target_client_id and target_client_id != self.bridge_id:
                        # 转换 prompt_id 为 LB 的任务 ID，保持客户端视角一致
                        lb_task_id = await self.manager.get_lb_id_by_prompt(prompt_id) if prompt_id else None
                        if lb_task_id:
                            if isinstance(m_data, dict) and "prompt_id" in m_data:
                                m_data["prompt_id"] = lb_task_id
                            elif "prompt_id" in data:
                                data["prompt_id"] = lb_task_id
                        
                        # 修正消息中的 sid 为目标客户端，避免前端混淆
                        if isinstance(m_data, dict) and "sid" in m_data:
                            m_data["sid"] = target_client_id
                        elif "sid" in data:
                            data["sid"] = target_client_id
                            
                        logger.debug(f"转发WS消息到客户端 {target_client_id}: {m_type} (ID: {lb_task_id or prompt_id})")
                        await self.manager.send_to_client(target_client_id, data)
                        await self.manager.associate_client_with_backend(target_client_id, self.backend_name)
                    else:
                        # 如果是发给 Bridge 的消息或者是无 SID 的消息，根据关联广播
                        # logger.debug(f"广播后端消息 {self.backend_name}: {m_type}")
                        await self.manager.broadcast_to_backend_users(self.backend_name, data)
                else:
                    await self.manager.broadcast_to_backend_users(self.backend_name, data)
            else:
                # 二进制消息 (通常是预览图)
                # 预览图通常不带 prompt_id，我们根据 association 广播给所有在该后端有任务的用户
                await self.manager.broadcast_to_backend_users(self.backend_name, message)
                    
        except json.JSONDecodeError:
            # 可能是非JSON文本
            await self.manager.broadcast_to_backend_users(self.backend_name, message)
        except Exception as e:
            logger.warning(f"处理WebSocket消息错误: {e}")


async def websocket_endpoint(websocket: WebSocket, client_id: str = ""):
    """WebSocket端点处理"""
    if not client_id:
        client_id = str(id(websocket))
    
    manager = websocket.app.state.ws_manager
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


