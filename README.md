# GPU 利用率监控分析系统

基于 Prometheus + FastAPI 的 GPU 利用率智能监控分析系统，专为 Kubeflow GPU 出借场景设计。

## 📋 功能特性

- ✅ **多维度评分**：综合 GPU 利用率、显存使用、内存带宽、功率等多个指标计算综合评分
- ✅ **多线程并发**：支持同时监控大量 GPU，高效并发查询
- ✅ **租户关联**：自动关联 Pod/Namespace 信息，明确租户责任
- ✅ **智能判定**：区分 idle/low/normal/high 四种状态
- ✅ **自动调度**：定时轮询分析，支持手动触发
- ✅ **RESTful API**：提供完整的 API 接口
- ✅ **可扩展**：支持调用外部控制接口进行自动化操作

## 🏗️ 系统架构

```
┌────────────────────────────┐
│      Prometheus            │
│ (DCGM exporter GPU metrics)│
└──────────────┬─────────────┘
               │
       每隔 N 分钟拉取
               ▼
┌────────────────────────────┐
│ GPU Monitor Service        │
│  - 多线程拉取GPU数据        │
│  - 计算综合评分             │
│  - 关联租户信息             │
│  - 触发控制接口             │
└──────────────┬─────────────┘
               │
               ▼
┌────────────────────────────┐
│  外部控制系统               │
│  (成本优化/资源回收)        │
└────────────────────────────┘
```

## 📊 评分算法

综合利用率评分采用加权计算：

```
score = 0.5 × GPU核心利用率
      + 0.2 × 内存拷贝利用率
      + 0.2 × 显存使用率
      + 0.1 × 功率使用率
```

**状态分类**：
- `idle` (< 10%)：完全闲置
- `low` (10-20%)：低利用率
- `normal` (20-70%)：正常使用
- `high` (> 70%)：高负载

## 🚀 快速开始

### 1. 安装依赖

```powershell
# 创建虚拟环境（推荐）
python -m venv venv
.\venv\Scripts\Activate.ps1

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置服务

编辑 `gpu_monitor.py` 中的配置项，或使用环境变量：

```python
class Config:
    PROM_URL = "http://your-prometheus:9090"
    THRESHOLD = 20  # 低利用率阈值
    INTERVAL = 300  # 轮询周期（秒）
    MAX_WORKERS = 8  # 并发线程数
```

### 3. 启动服务

```powershell
# 直接运行
python gpu_monitor.py

# 或使用 uvicorn
uvicorn gpu_monitor:app --host 0.0.0.0 --port 8080
```

### 4. 访问服务

- **服务信息**：http://localhost:8080/
- **健康检查**：http://localhost:8080/health
- **手动触发分析**：http://localhost:8080/analyze
- **查看最新结果**：http://localhost:8080/results
- **低利用率 GPU**：http://localhost:8080/results/low
- **统计信息**：http://localhost:8080/results/stats

## 🔧 API 文档

### 1. 获取服务信息

```bash
GET http://localhost:8080/
```

响应示例：
```json
{
  "service": "GPU Utilization Monitor",
  "version": "1.0.0",
  "config": {
    "prometheus_url": "http://prometheus:9090",
    "threshold": 20,
    "interval": 300,
    "time_window_min": 10
  }
}
```

### 2. 手动触发分析

```bash
GET http://localhost:8080/analyze
```

响应示例：
```json
{
  "status": "triggered",
  "message": "GPU analysis started in background"
}
```

### 3. 获取分析结果

```bash
GET http://localhost:8080/results
```

响应示例：
```json
[
  {
    "gpu_id": "GPU-03cd1cf6-11f6-5ecc-feb0-af07406e1838",
    "pod": "comfyui-xuanwu-deploy-694d64fb5-jqs8w",
    "namespace": "comfyui",
    "hostname": "aigc-k8s-vn-master001",
    "model_name": "Tesla V100S-PCIE-32GB",
    "gpu_util": 78.5,
    "mem_copy": 45.2,
    "mem_used_mb": 18432.5,
    "power_usage": 185.3,
    "sm_clock": 1530.0,
    "score": 68.4,
    "status": "normal"
  }
]
```

### 4. 获取低利用率 GPU

```bash
GET http://localhost:8080/results/low
```

响应示例：
```json
{
  "count": 2,
  "threshold": 20,
  "gpus": [
    {
      "gpu_id": "GPU-xxx",
      "pod": "idle-pod",
      "namespace": "test",
      "score": 5.2,
      "status": "idle"
    }
  ]
}
```

### 5. 获取统计信息

```bash
GET http://localhost:8080/results/stats
```

响应示例：
```json
{
  "total_gpus": 24,
  "avg_score": 45.6,
  "min_score": 5.2,
  "max_score": 92.3,
  "low_utilization_count": 3,
  "idle_count": 1,
  "by_status": {
    "idle": 1,
    "low": 2,
    "normal": 15,
    "high": 6
  }
}
```

## 📈 监控指标说明

系统从 Prometheus 采集以下 GPU 指标：

| 指标名称 | 说明 | 权重 |
|---------|------|------|
| `DCGM_FI_DEV_GPU_UTIL` | GPU 核心利用率 (%) | 50% |
| `DCGM_FI_DEV_MEM_COPY_UTIL` | 内存带宽使用率 (%) | 20% |
| `DCGM_FI_DEV_FB_USED` | 显存使用量 (bytes) | 20% |
| `DCGM_FI_DEV_POWER_USAGE` | 功率 (W) | 10% |
| `DCGM_FI_DEV_SM_CLOCK` | SM 时钟频率 (MHz) | 辅助 |

**查询条件**：`{pod!=""}`（只监控已分配给 Pod 的 GPU）

## 🔌 控制接口集成

当检测到低利用率 GPU 时，系统可以自动调用外部控制接口：

### 启用控制接口

```python
class Config:
    CONTROL_API_ENABLED = True
    CONTROL_API = "http://your-control-service/api/optimize"
```

### 请求格式

```json
{
  "gpu_id": "GPU-03cd1cf6-11f6-5ecc-feb0-af07406e1838",
  "pod": "pod-name",
  "namespace": "namespace-name",
  "hostname": "node-name",
  "score": 5.2,
  "status": "idle",
  "timestamp": "2025-10-26T10:30:00"
}
```

## 🐳 Docker 部署

### 构建镜像

```powershell
docker build -t gpu-monitor:latest .
```

### 运行容器

```powershell
docker run -d \
  --name gpu-monitor \
  -p 8080:8080 \
  -e PROM_URL=http://prometheus:9090 \
  -e THRESHOLD=20 \
  -e INTERVAL=300 \
  gpu-monitor:latest
```

### Kubernetes 部署

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: gpu-monitor
  namespace: monitoring
spec:
  replicas: 1
  selector:
    matchLabels:
      app: gpu-monitor
  template:
    metadata:
      labels:
        app: gpu-monitor
    spec:
      containers:
      - name: gpu-monitor
        image: gpu-monitor:latest
        ports:
        - containerPort: 8080
        env:
        - name: PROM_URL
          value: "http://prometheus.monitoring:9090"
        - name: THRESHOLD
          value: "20"
        - name: INTERVAL
          value: "300"
```

## ⚙️ 配置说明

### 核心配置项

| 配置项 | 默认值 | 说明 |
|-------|-------|------|
| `PROM_URL` | `http://prometheus:9090` | Prometheus 地址 |
| `THRESHOLD` | `20` | 低利用率阈值（%） |
| `INTERVAL` | `300` | 轮询周期（秒） |
| `MAX_WORKERS` | `8` | 最大并发线程数 |
| `TIME_WINDOW_MIN` | `10` | 时间窗口（分钟） |
| `STEP` | `30s` | 查询步长 |

### 评分权重配置

```python
GPU_UTIL_WEIGHT = 0.5    # GPU 核心使用率权重
MEM_COPY_WEIGHT = 0.2    # 内存拷贝使用率权重
MEM_USED_WEIGHT = 0.2    # 显存使用权重
POWER_WEIGHT = 0.1       # 功率权重
```

## 📝 日志输出

系统会输出详细的分析日志：

```
2025-10-26 10:30:00 - __main__ - INFO - ============================================================
2025-10-26 10:30:00 - __main__ - INFO - GPU Utilization Analysis Results
2025-10-26 10:30:00 - __main__ - INFO - ============================================================
2025-10-26 10:30:00 - __main__ - INFO - Namespace/Pod                            GPU                                          Score     Util   Mem(MB)   Status
2025-10-26 10:30:00 - __main__ - INFO - ------------------------------------------------------------
2025-10-26 10:30:00 - __main__ - INFO - comfyui/comfyui-xuanwu-deploy-xxx        GPU-03cd1cf6-11f6-5ecc-feb0-af07406e1838    68.4%    78.5%   18432.5  normal
2025-10-26 10:30:00 - __main__ - INFO - test/idle-pod-xxx                        GPU-abc123-...                                5.2%     2.1%      128.0  idle

2025-10-26 10:30:00 - __main__ - WARNING - ⚠️  Found 1 GPU(s) with utilization below 20%:
2025-10-26 10:30:00 - __main__ - WARNING -   - test/idle-pod-xxx (5.2%) - GPU-abc123-...
```

## 🔍 故障排查

### 1. 连接 Prometheus 失败

检查 Prometheus 地址配置：
```python
PROM_URL = "http://prometheus:9090"
```

测试连接：
```powershell
curl http://prometheus:9090/api/v1/status/config
```

### 2. 查询不到 GPU 数据

检查查询条件：
```python
QUERY_CONDITION = '{pod!=""}'
```

手动测试查询：
```
http://prometheus:9090/graph
DCGM_FI_DEV_GPU_UTIL{pod!=""}
```

### 3. 评分异常

检查指标是否存在：
- `DCGM_FI_DEV_GPU_UTIL`
- `DCGM_FI_DEV_MEM_COPY_UTIL`
- `DCGM_FI_DEV_FB_USED`
- `DCGM_FI_DEV_POWER_USAGE`

## 🚀 扩展功能

### 1. 接入 AI 判断

可以将指标数据传递给 AI 模型进行智能判断：

```python
def ai_judge_utilization(metrics_series):
    """
    使用 AI 模型判断 GPU 利用率
    metrics_series: 最近10分钟的指标时序数据
    """
    prompt = f"""
    根据以下 GPU 指标判断是否在有效使用：
    - GPU 利用率序列: {metrics_series['gpu_util']}
    - 显存使用序列: {metrics_series['mem_used']}
    - 功率序列: {metrics_series['power']}
    
    请输出: {{"status": "active|idle", "confidence": 0-1, "reason": "..."}}
    """
    # 调用 LLM API
    response = call_llm(prompt)
    return response
```

### 2. Grafana 可视化

导入 Dashboard 模板展示：
- GPU 利用率趋势
- 租户使用情况
- 低利用率告警

### 3. 通知集成

添加告警通知：
```python
def send_notification(low_util_gpus):
    # 飞书通知
    # Slack 通知
    # 邮件通知
    pass
```

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📧 联系方式

如有问题请联系项目维护者。

