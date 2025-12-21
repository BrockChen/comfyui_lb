"""
任务调度器
"""
import logging
from typing import Optional
from abc import ABC, abstractmethod

from models import BackendState, Task
from backend_manager import BackendManager

logger = logging.getLogger(__name__)


class SchedulerStrategy(ABC):
    """调度策略基类"""
    
    @abstractmethod
    def select(self, backends: list[BackendState], task: Task) -> Optional[BackendState]:
        """选择后端"""
        pass


class LeastBusyStrategy(SchedulerStrategy):
    """最少忙碌策略 - 选择队列最短的后端"""
    
    def select(self, backends: list[BackendState], task: Task) -> Optional[BackendState]:
        if not backends:
            return None
        
        # 按队列长度排序
        sorted_backends = sorted(backends, key=lambda b: b.total_queue)
        return sorted_backends[0]


class RoundRobinStrategy(SchedulerStrategy):
    """轮询策略"""
    
    def __init__(self):
        self._index = 0
    
    def select(self, backends: list[BackendState], task: Task) -> Optional[BackendState]:
        if not backends:
            return None
        
        # 轮询选择
        backend = backends[self._index % len(backends)]
        self._index = (self._index + 1) % len(backends)
        return backend


class WeightedStrategy(SchedulerStrategy):
    """加权策略 - 考虑权重和队列长度"""
    
    def select(self, backends: list[BackendState], task: Task) -> Optional[BackendState]:
        if not backends:
            return None
        
        # 计算得分: 权重越高越好, 队列越短越好
        def score(backend: BackendState) -> float:
            # 避免除零
            queue_factor = 1.0 / (1.0 + backend.total_queue)
            return backend.weight * queue_factor
        
        sorted_backends = sorted(backends, key=score, reverse=True)
        return sorted_backends[0]


class Scheduler:
    """任务调度器"""
    
    STRATEGIES = {
        "least_busy": LeastBusyStrategy,
        "round_robin": RoundRobinStrategy,
        "weighted": WeightedStrategy,
    }
    
    def __init__(self, backend_manager: BackendManager, strategy: str = "least_busy", prefer_idle: bool = True):
        self.backend_manager = backend_manager
        self.prefer_idle = prefer_idle
        self._strategy = self._create_strategy(strategy)
        self._strategy_name = strategy
    
    def _create_strategy(self, name: str) -> SchedulerStrategy:
        """创建调度策略"""
        strategy_class = self.STRATEGIES.get(name)
        if not strategy_class:
            logger.warning(f"未知调度策略: {name}, 使用 least_busy")
            strategy_class = LeastBusyStrategy
        return strategy_class()
    
    def set_strategy(self, name: str):
        """设置调度策略"""
        self._strategy = self._create_strategy(name)
        self._strategy_name = name
        logger.info(f"调度策略已更改为: {name}")
    
    @property
    def strategy_name(self) -> str:
        return self._strategy_name
    
    def select_backend(self, task: Task) -> Optional[BackendState]:
        """为任务选择后端"""
        # 优先选择空闲后端
        if self.prefer_idle:
            idle_backends = self.backend_manager.get_idle_backends()
            if idle_backends:
                backend = self._strategy.select(idle_backends, task)
                if backend:
                    logger.debug(f"选择空闲后端: {backend.name}")
                    return backend
        
        # 选择可用后端
        available_backends = self.backend_manager.get_available_backends()
        if available_backends:
            backend = self._strategy.select(available_backends, task)
            if backend:
                logger.debug(f"选择可用后端: {backend.name}")
                return backend
        
        # 没有可用后端
        logger.debug("没有可用后端")
        return None
    
    def has_available_backend(self) -> bool:
        """是否有可用后端"""
        return len(self.backend_manager.get_available_backends()) > 0
    
    def has_idle_backend(self) -> bool:
        """是否有空闲后端"""
        return len(self.backend_manager.get_idle_backends()) > 0

