"""
数据模型定义
"""
import uuid
from enum import Enum
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


class BackendStatus(str, Enum):
    """后端状态"""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class TaskStatus(str, Enum):
    """任务状态"""
    QUEUED = "queued"           # 在负载均衡器队列中等待
    DISPATCHED = "dispatched"   # 已分发到后端
    RUNNING = "running"         # 正在执行
    COMPLETED = "completed"     # 已完成
    FAILED = "failed"           # 失败
    CANCELLED = "cancelled"     # 已取消


class BackendState(BaseModel):
    """后端实例状态"""
    name: str
    host: str
    port: int
    base_url: str
    status: BackendStatus = BackendStatus.UNKNOWN
    queue_pending: int = 0          # 待处理任务数
    queue_running: int = 0          # 正在运行的任务数
    last_check: Optional[datetime] = None
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    enabled: bool = True
    weight: int = 1
    max_queue: int = 10

    @property
    def is_available(self) -> bool:
        """是否可用于接收新任务"""
        return (
            self.enabled 
            and self.status == BackendStatus.HEALTHY
            and self.total_queue < self.max_queue
        )

    @property
    def is_idle(self) -> bool:
        """是否完全空闲"""
        return self.is_available and self.total_queue == 0

    @property
    def total_queue(self) -> int:
        """总队列长度"""
        return self.queue_pending + self.queue_running

    class Config:
        use_enum_values = True


class Task(BaseModel):
    """任务"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    prompt: dict[str, Any]                    # ComfyUI prompt
    client_id: Optional[str] = None           # 客户端ID
    status: TaskStatus = TaskStatus.QUEUED
    backend_name: Optional[str] = None        # 分配的后端
    prompt_id: Optional[str] = None           # ComfyUI返回的prompt_id
    created_at: datetime = Field(default_factory=datetime.now)
    dispatched_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    retries: int = 0
    extra_data: Optional[dict[str, Any]] = None  # 额外数据(number等)

    class Config:
        use_enum_values = True


class QueueStatus(BaseModel):
    """队列状态"""
    pending: int = 0        # 等待分发的任务数
    dispatched: int = 0     # 已分发但未完成的任务数
    total: int = 0          # 总任务数


class PromptRequest(BaseModel):
    """提交任务请求 - 兼容ComfyUI格式"""
    prompt: dict[str, Any]
    client_id: Optional[str] = None
    extra_data: Optional[dict[str, Any]] = None


class PromptResponse(BaseModel):
    """提交任务响应 - 兼容ComfyUI格式"""
    prompt_id: str
    number: int
    node_errors: dict = Field(default_factory=dict)


class SystemStats(BaseModel):
    """系统统计信息"""
    total_backends: int = 0
    healthy_backends: int = 0
    available_backends: int = 0
    idle_backends: int = 0
    queue_status: QueueStatus = Field(default_factory=QueueStatus)
    backends: list[BackendState] = Field(default_factory=list)

