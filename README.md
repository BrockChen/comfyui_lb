# ComfyUI 负载均衡器

一个用于管理多个 ComfyUI 实例的负载均衡器,支持任务自动分发和队列管理。

## 功能特性

- ✅ **多后端管理**: 支持注册和管理多个 ComfyUI 实例
- ✅ **智能调度**: 自动选择空闲的后端执行任务
- ✅ **任务队列**: 所有后端忙碌时自动排队等待
- ✅ **健康检查**: 定期检测后端健康状态
- ✅ **API 兼容**: 完全兼容 ComfyUI API,客户端无需修改
- ✅ **动态配置**: 支持运行时添加/移除后端
- ✅ **WebSocket 支持**: 支持实时状态推送

## 快速开始

### 1. 安装依赖

```bash
cd comfyui_lb
pip install -r requirements.txt
```

### 2. 配置后端

编辑 `config.yaml`,添加你的 ComfyUI 实例:

```yaml
backends:
  - name: "comfy-1"
    host: "127.0.0.1"
    port: 8188
    weight: 1
    max_queue: 10
    enabled: true
  
  - name: "comfy-2"
    host: "127.0.0.1"
    port: 8189
    weight: 1
    max_queue: 10
    enabled: true
```

### 3. 启动负载均衡器

```bash
python main.py
```

或使用命令行参数:

```bash
python main.py -c config.yaml -H 0.0.0.0 -p 8100
```

### 4. 使用

- **管理界面**: 打开 `http://localhost:8100/` 查看实时状态和管理后端
- **API 接入**: 将你的 ComfyUI 客户端指向负载均衡器地址 `http://localhost:8100`

## API 文档

### ComfyUI 兼容 API

负载均衡器完全兼容 ComfyUI 原生 API:

| 端点 | 方法 | 说明 |
|------|------|------|
| `/prompt` | POST | 提交任务 |
| `/queue` | GET | 获取队列状态 |
| `/queue` | POST | 管理队列(取消任务) |
| `/history` | GET | 获取历史记录 |
| `/history/{prompt_id}` | GET | 获取特定任务历史 |
| `/object_info` | GET | 获取节点信息 |
| `/system_stats` | GET | 获取系统状态 |
| `/embeddings` | GET | 获取 embeddings 列表 |
| `/extensions` | GET | 获取扩展列表 |
| `/ws` | WebSocket | 实时状态推送 |

### 负载均衡器管理 API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/lb/stats` | GET | 获取负载均衡器统计信息 |
| `/lb/backends` | GET | 列出所有后端 |
| `/lb/backends` | POST | 添加新后端 |
| `/lb/backends/{name}` | DELETE | 移除后端 |
| `/lb/backends/{name}/enable` | POST | 启用后端 |
| `/lb/backends/{name}/disable` | POST | 禁用后端 |
| `/lb/tasks` | GET | 列出所有任务 |
| `/lb/tasks/{task_id}` | GET | 获取任务详情 |
| `/lb/tasks/{task_id}` | DELETE | 取消任务 |
| `/lb/health-check` | POST | 触发健康检查 |
| `/lb/scheduler` | GET | 获取调度器信息 |
| `/lb/scheduler/strategy/{strategy}` | POST | 设置调度策略 |

### 示例

#### 提交任务

```bash
curl -X POST http://localhost:8100/prompt \
  -H "Content-Type: application/json" \
  -d '{"prompt": {...}}'
```

#### 获取统计信息

```bash
curl http://localhost:8100/lb/stats
```

#### 添加新后端

```bash
curl -X POST http://localhost:8100/lb/backends \
  -H "Content-Type: application/json" \
  -d '{
    "name": "comfy-3",
    "host": "127.0.0.1",
    "port": 8190,
    "weight": 1,
    "max_queue": 10,
    "enabled": true
  }'
```

## 调度策略

支持三种调度策略:

1. **least_busy** (默认): 选择队列最短的后端
2. **round_robin**: 轮询选择后端
3. **weighted**: 根据权重和队列长度综合选择

## 配置说明

```yaml
# 服务器配置
server:
  host: "0.0.0.0"      # 监听地址
  port: 8100           # 监听端口
  debug: false         # 调试模式

# 调度器配置
scheduler:
  strategy: "least_busy"  # 调度策略
  prefer_idle: true       # 优先选择空闲实例

# 健康检查配置
health_check:
  interval: 5.0            # 检查间隔(秒)
  timeout: 3.0             # 超时时间(秒)
  unhealthy_threshold: 3   # 不健康阈值
  healthy_threshold: 1     # 健康阈值

# 任务队列配置
queue:
  max_size: 1000        # 最大队列大小
  retry_interval: 1.0   # 重试间隔(秒)
  max_retries: 3        # 最大重试次数

# 后端配置
backends:
  - name: "comfy-1"     # 后端名称(唯一)
    host: "127.0.0.1"   # 后端地址
    port: 8188          # 后端端口
    weight: 1           # 权重
    max_queue: 10       # 最大队列长度
    enabled: true       # 是否启用
```

## 架构说明

```
┌─────────────────────────────────────────────────────────────┐
│                      客户端请求                               │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                  负载均衡器 (FastAPI)                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  任务队列    │  │  调度器      │  │  健康检查 & 状态监控  │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────┬───────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
   ┌────────────┐  ┌────────────┐  ┌────────────┐
   │ ComfyUI:1  │  │ ComfyUI:2  │  │ ComfyUI:N  │
   │  :8188     │  │  :8189     │  │  :819X     │
   └────────────┘  └────────────┘  └────────────┘
```

## License

MIT


