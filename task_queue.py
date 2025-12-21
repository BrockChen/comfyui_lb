"""
任务队列管理
"""
import asyncio
import logging
from typing import Any, Optional, Callable, Awaitable
from datetime import datetime
from collections import OrderedDict

from config import Settings
from models import Task, TaskStatus, QueueStatus

logger = logging.getLogger(__name__)


class TaskQueue:
    """任务队列"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self._pending: OrderedDict[str, Task] = OrderedDict()  # 等待分发
        self._dispatched: dict[str, Task] = {}                  # 已分发
        self._completed: dict[str, Task] = {}                   # 已完成 (保留最近的)
        self._lock = asyncio.Lock()
        self._task_counter = 0
        self._dispatch_event = asyncio.Event()
        self._running = False
        self._dispatch_task: Optional[asyncio.Task] = None
        self._on_dispatch: Optional[Callable[[Task], Awaitable[bool]]] = None
    
    def set_dispatch_callback(self, callback: Callable[[Task], Awaitable[bool]]):
        """设置分发回调"""
        self._on_dispatch = callback
    
    async def start(self):
        """启动队列处理"""
        self._running = True
        self._dispatch_task = asyncio.create_task(self._dispatch_loop())
        logger.info("任务队列已启动")
    
    async def stop(self):
        """停止队列处理"""
        self._running = False
        self._dispatch_event.set()  # 唤醒循环
        if self._dispatch_task:
            self._dispatch_task.cancel()
            try:
                await self._dispatch_task
            except asyncio.CancelledError:
                pass
        logger.info("任务队列已停止")
    
    async def add_task(self, prompt: dict[str, Any], client_id: Optional[str] = None, 
                       extra_data: Optional[dict] = None) -> Task:
        """添加任务到队列"""
        async with self._lock:
            if len(self._pending) >= self.settings.queue.max_size:
                raise ValueError("队列已满")
            
            self._task_counter += 1
            task = Task(
                prompt=prompt,
                client_id=client_id,
                extra_data=extra_data or {"number": self._task_counter},
            )
            self._pending[task.id] = task
            logger.info(f"任务入队: {task.id}, 队列长度: {len(self._pending)}")
        
        # 通知分发循环
        self._dispatch_event.set()
        return task
    
    async def get_pending_task(self) -> Optional[Task]:
        """获取下一个待处理任务(不移除)"""
        async with self._lock:
            if self._pending:
                return next(iter(self._pending.values()))
            return None
    
    async def pop_pending_task(self) -> Optional[Task]:
        """取出下一个待处理任务"""
        async with self._lock:
            if self._pending:
                task_id, task = self._pending.popitem(last=False)
                return task
            return None
    
    async def mark_dispatched(self, task: Task, backend_name: str, prompt_id: str):
        """标记任务已分发"""
        async with self._lock:
            task.status = TaskStatus.DISPATCHED
            task.backend_name = backend_name
            task.prompt_id = prompt_id
            task.dispatched_at = datetime.now()
            self._dispatched[task.id] = task
            logger.info(f"任务已分发: {task.id} -> {backend_name} (prompt_id: {prompt_id})")
    
    async def mark_completed(self, task_id: str, success: bool = True, error: Optional[str] = None):
        """标记任务完成"""
        async with self._lock:
            task = self._dispatched.pop(task_id, None)
            if task:
                task.status = TaskStatus.COMPLETED if success else TaskStatus.FAILED
                task.completed_at = datetime.now()
                task.error = error
                self._completed[task_id] = task
                
                # 限制完成任务缓存大小
                while len(self._completed) > 1000:
                    self._completed.pop(next(iter(self._completed)))
                
                logger.info(f"任务完成: {task_id}, 状态: {task.status}")
    
    async def mark_failed(self, task: Task, error: str):
        """标记任务失败并决定是否重试"""
        async with self._lock:
            task.retries += 1
            task.error = error
            
            if task.retries < self.settings.queue.max_retries:
                # 重新入队
                task.status = TaskStatus.QUEUED
                task.backend_name = None
                task.prompt_id = None
                self._pending[task.id] = task
                logger.warning(f"任务重试: {task.id}, 第{task.retries}次, 错误: {error}")
            else:
                # 放弃重试
                task.status = TaskStatus.FAILED
                task.completed_at = datetime.now()
                self._completed[task.id] = task
                logger.error(f"任务失败: {task.id}, 已重试{task.retries}次, 错误: {error}")
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        async with self._lock:
            # 尝试从待处理队列移除
            if task_id in self._pending:
                task = self._pending.pop(task_id)
                task.status = TaskStatus.CANCELLED
                task.completed_at = datetime.now()
                self._completed[task_id] = task
                logger.info(f"任务已取消: {task_id}")
                return True
            
            # 已分发的任务需要通知后端取消
            if task_id in self._dispatched:
                task = self._dispatched[task_id]
                task.status = TaskStatus.CANCELLED
                # 注意: 实际取消后端任务需要在外部处理
                return True
        
        return False
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        if task_id in self._pending:
            return self._pending[task_id]
        if task_id in self._dispatched:
            return self._dispatched[task_id]
        if task_id in self._completed:
            return self._completed[task_id]
        return None
    
    def get_task_by_prompt_id(self, prompt_id: str) -> Optional[Task]:
        """通过prompt_id获取任务"""
        for task in self._dispatched.values():
            if task.prompt_id == prompt_id:
                return task
        for task in self._completed.values():
            if task.prompt_id == prompt_id:
                return task
        return None
    
    def get_status(self) -> QueueStatus:
        """获取队列状态"""
        return QueueStatus(
            pending=len(self._pending),
            dispatched=len(self._dispatched),
            total=len(self._pending) + len(self._dispatched),
        )
    
    def get_all_tasks(self) -> dict[str, list[Task]]:
        """获取所有任务"""
        return {
            "pending": list(self._pending.values()),
            "dispatched": list(self._dispatched.values()),
            "completed": list(self._completed.values())[-100:],  # 最近100个
        }
    
    async def _dispatch_loop(self):
        """分发循环"""
        while self._running:
            try:
                # 等待事件或超时
                try:
                    await asyncio.wait_for(
                        self._dispatch_event.wait(),
                        timeout=self.settings.queue.retry_interval
                    )
                except asyncio.TimeoutError:
                    pass
                
                self._dispatch_event.clear()
                
                if not self._running:
                    break
                
                # 尝试分发任务
                if self._on_dispatch:
                    while True:
                        task = await self.get_pending_task()
                        if not task:
                            break
                        
                        # 尝试分发
                        success = await self._on_dispatch(task)
                        if success:
                            # 从pending移除(已在回调中处理)
                            async with self._lock:
                                self._pending.pop(task.id, None)
                        else:
                            # 没有可用后端,等待
                            break
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"分发循环错误: {e}")
                await asyncio.sleep(1)
    
    def trigger_dispatch(self):
        """触发分发检查"""
        self._dispatch_event.set()

