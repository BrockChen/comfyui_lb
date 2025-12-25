"""
ComfyUI 负载均衡器配置管理
"""
import yaml
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class BackendConfig(BaseModel):
    """单个ComfyUI后端配置"""
    name: str = Field(..., description="后端名称")
    host: str = Field(default="127.0.0.1", description="后端地址")
    port: int = Field(..., description="后端端口")
    weight: int = Field(default=1, description="权重,用于加权调度")
    max_queue: int = Field(default=10, description="最大队列长度,超过则认为忙碌")
    enabled: bool = Field(default=True, description="是否启用")

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    @property
    def ws_url(self) -> str:
        return f"ws://{self.host}:{self.port}/ws"


class SchedulerConfig(BaseModel):
    """调度器配置"""
    strategy: str = Field(
        default="least_busy",
        description="调度策略: least_busy(最少忙碌), round_robin(轮询), weighted(加权)"
    )
    prefer_idle: bool = Field(default=True, description="优先选择完全空闲的实例")


class HealthCheckConfig(BaseModel):
    """健康检查配置"""
    interval: float = Field(default=5.0, description="检查间隔(秒)")
    timeout: float = Field(default=3.0, description="超时时间(秒)")
    unhealthy_threshold: int = Field(default=3, description="连续失败多少次标记为不健康")
    healthy_threshold: int = Field(default=1, description="连续成功多少次标记为健康")


class QueueConfig(BaseModel):
    """任务队列配置"""
    max_size: int = Field(default=1000, description="最大队列大小")
    retry_interval: float = Field(default=1.0, description="重试间隔(秒)")
    max_retries: int = Field(default=3, description="最大重试次数")


class ServerConfig(BaseModel):
    """服务器配置"""
    host: str = Field(default="0.0.0.0", description="监听地址")
    port: int = Field(default=8100, description="监听端口")
    debug: bool = Field(default=False, description="调试模式")


class KongConfig(BaseModel):
    """Kong API Gateway配置"""
    enabled: bool = Field(default=False, description="是否启用Kong集成")
    admin_url: str = Field(default="http://localhost:8001", description="Kong Admin API地址")
    timeout: float = Field(default=10.0, description="请求超时时间(秒)")


class Settings(BaseSettings):
    """全局设置"""
    server: ServerConfig = Field(default_factory=ServerConfig)
    scheduler: SchedulerConfig = Field(default_factory=SchedulerConfig)
    health_check: HealthCheckConfig = Field(default_factory=HealthCheckConfig)
    queue: QueueConfig = Field(default_factory=QueueConfig)
    kong: KongConfig = Field(default_factory=KongConfig)
    backends: list[BackendConfig] = Field(default_factory=list)

    class Config:
        env_prefix = "COMFYUI_LB_"

    @classmethod
    def from_yaml(cls, path: str | Path) -> "Settings":
        """从YAML文件加载配置"""
        path = Path(path)
        if not path.exists():
            return cls()
        
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        
        return cls(**data)


def load_config(config_path: Optional[str] = None) -> Settings:
    """加载配置"""
    if config_path:
        return Settings.from_yaml(config_path)
    
    # 尝试默认配置文件
    default_paths = [
        Path("config.yaml"),
        Path("config.yml"),
        Path(__file__).parent / "config.yaml",
    ]
    
    for path in default_paths:
        if path.exists():
            return Settings.from_yaml(path)
    
    return Settings()


