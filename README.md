# GPU 利用率监控分析系统

基于 Prometheus + FastAPI 的 GPU 利用率智能监控分析系统，专为 Kubeflow GPU 出借场景设计。

## 🌟 v2.0 新特性

- 🤖 **AI 智能分析**：集成 LLM（GPT-4/Claude）进行智能判断
- 📊 **Prometheus Metrics**：完整的 metrics 导出，可被 Prometheus 抓取
- 🔧 **模块化架构**：代码拆分为独立模块，易于维护和扩展
- ⚙️ **灵活配置**：支持 YAML 配置文件 + 环境变量覆盖
- 🔍 **增强健康检查**：实时监控服务和 Prometheus 连接状态

## 📋 核心功能

- ✅ **多维度评分**：综合 GPU 利用率、显存使用、内存带宽、功率等多个指标计算综合评分
- ✅ **多线程并发**：支持同时监控大量 GPU，高效并发查询
- ✅ **租户关联**：自动关联 Pod/Namespace 信息，明确租户责任
- ✅ **智能判定**：区分 idle/low/normal/high 四种状态
- ✅ **AI 辅助**：可选启用 AI 模型进行智能分析和判断
- ✅ **自动调度**：定时轮询分析，支持手动触发
- ✅ **RESTful API**：提供完整的 API 接口
- ✅ **Metrics 导出**：支持 Prometheus 抓取监控数据
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
# 克隆项目
git clone <repository-url>
cd gpu-oour

# 创建虚拟环境（推荐）
python -m venv venv
.\venv\Scripts\Activate.ps1

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置服务

编辑 `config.yaml` 文件：

```yaml
# config.yaml
prometheus:
  url: "http://your-prometheus:9090"  # 修改为你的 Prometheus 地址

thresholds:
  low_utilization: 20  # 低利用率阈值

scheduler:
  interval: 300  # 轮询周期（秒）
  max_workers: 8  # 并发线程数

# 可选：启用 AI 分析
ai:
  enabled: false  # 改为 true 启用
  api_url: "https://api.openai.com/v1/chat/completions"
  model: "gpt-4"
```

**敏感信息使用环境变量：**
```powershell
$env:AI_API_KEY="sk-your-api-key"  # 如果启用 AI
```

### 3. 启动服务

```powershell
# 方式 1：直接运行
python main.py

# 方式 2：使用 uvicorn（推荐生产环境）
uvicorn main:app --host 0.0.0.0 --port 8080

# 方式 3：后台运行
Start-Process python -ArgumentList "main.py" -WindowStyle Hidden
```

### 4. 验证服务

```powershell
# 查看服务信息
curl http://localhost:8080/

# 健康检查
curl http://localhost:8080/health

# 手动触发分析
curl http://localhost:8080/analyze

# 查看结果
curl http://localhost:8080/results

# 查看 Prometheus metrics
curl http://localhost:8080/metrics
```

### 5. 访问 API 文档

浏览器打开：http://localhost:8080/docs

FastAPI 自动生成的交互式 API 文档。

## 🔧 API 文档

### 核心端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 服务信息 |
| `/health` | GET | 健康检查（增强版） |
| `/analyze` | GET | 手动触发分析 |
| `/results` | GET | 获取分析结果 |
| `/results/low` | GET | 低利用率 GPU |
| `/results/stats` | GET | 统计信息 |
| **`/metrics`** | **GET** | **Prometheus metrics** ⭐ |
| `/config` | GET | 查看当前配置 |
| `/config/update` | POST | 动态更新配置 |

### 1. 获取服务信息

```bash
GET http://localhost:8080/
```

响应示例：
```json
{
  "service": "GPU Utilization Monitor",
  "version": "1.0.0",
  "features": {
    "ai_analysis": true,
    "prometheus_metrics": true,
    "control_api": false
  },
  "config": {
    "prometheus_url": "http://prometheus:9090",
    "threshold": 20,
    "interval": 300
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

### 3. 获取分析结果（含 AI 分析）

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
    "status": "normal",
    "timestamp": "2025-10-26T10:30:00",
    "ai_analysis": {
      "status": "active",
      "confidence": 0.92,
      "reason": "GPU利用率稳定在70%以上，显存占用合理，功率正常，判断为训练任务",
      "recommendation": "继续保持当前使用状态",
      "ai_adjusted_score": 70.5
    }
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
  },
  "by_namespace": {
    "ml-team": {
      "count": 10,
      "avg_score": 75.2,
      "low_util_count": 0
    },
    "dev-team": {
      "count": 8,
      "avg_score": 15.3,
      "low_util_count": 3
    }
  }
}
```

### 6. Prometheus Metrics（新增 ⭐）

```bash
GET http://localhost:8080/metrics
```

导出的 metrics：
```
# GPU 评分
gpu_utilization_score{gpu_id="GPU-xxx",pod="...",namespace="...",status="high"} 78.4

# GPU 利用率
gpu_core_utilization{gpu_id="GPU-xxx",pod="...",namespace="..."} 75.2

# AI 分析结果
gpu_ai_analysis_confidence{gpu_id="GPU-xxx",ai_status="active"} 0.92
gpu_ai_adjusted_score{gpu_id="GPU-xxx",pod="...",namespace="..."} 70.5

# 统计指标
gpu_total_count 24
gpu_low_utilization_count 3
gpu_idle_count 1
gpu_average_score 45.6

# 状态分布
gpu_status_count{status="high"} 6
gpu_status_count{status="normal"} 15

# 命名空间统计
gpu_namespace_count{namespace="ml-team"} 10
gpu_namespace_average_score{namespace="ml-team"} 75.2

# 服务指标
gpu_analysis_total 156
gpu_analysis_errors_total 2
gpu_analysis_duration_seconds{quantile="0.5"} 2.35
```

## 📈 监控指标说明

### Prometheus 采集指标

系统从 Prometheus 采集以下 GPU 指标：

| 指标名称 | 说明 | 权重 |
|---------|------|------|
| `DCGM_FI_DEV_GPU_UTIL` | GPU 核心利用率 (%) | 50% |
| `DCGM_FI_DEV_MEM_COPY_UTIL` | 内存带宽使用率 (%) | 20% |
| `DCGM_FI_DEV_FB_USED` | 显存使用量 (bytes) | 20% |
| `DCGM_FI_DEV_POWER_USAGE` | 功率 (W) | 10% |
| `DCGM_FI_DEV_SM_CLOCK` | SM 时钟频率 (MHz) | 辅助 |

**查询条件**：`{pod!=""}`（只监控已分配给 Pod 的 GPU）

### 导出的 Prometheus Metrics

服务通过 `/metrics` 端点导出以下指标供 Prometheus 抓取：

#### GPU 核心指标
- `gpu_utilization_score` - GPU 综合利用率评分 (0-100)
- `gpu_core_utilization` - GPU 核心利用率 (%)
- `gpu_memory_used_mb` - 显存使用量 (MB)
- `gpu_power_usage_watts` - 功率使用 (W)
- `gpu_memory_copy_utilization` - 内存带宽利用率 (%)
- `gpu_sm_clock_mhz` - SM 时钟频率 (MHz)

#### AI 分析指标（如启用）
- `gpu_ai_analysis_confidence` - AI 分析置信度 (0-1)
- `gpu_ai_adjusted_score` - AI 调整后的评分 (0-100)

#### 统计指标
- `gpu_total_count` - GPU 总数
- `gpu_low_utilization_count` - 低利用率 GPU 数量
- `gpu_idle_count` - 闲置 GPU 数量
- `gpu_average_score` - 平均 GPU 评分
- `gpu_status_count{status}` - GPU 状态分布
- `gpu_namespace_count{namespace}` - 各命名空间 GPU 数量
- `gpu_namespace_average_score{namespace}` - 各命名空间平均评分

#### 服务指标
- `gpu_analysis_total` - GPU 分析总次数
- `gpu_analysis_errors_total` - GPU 分析错误次数
- `gpu_analysis_duration_seconds` - GPU 分析耗时直方图

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
# 基础运行
docker run -d \
  --name gpu-monitor \
  -p 8080:8080 \
  -v ${PWD}/config.yaml:/app/config.yaml \
  gpu-monitor:latest

# 使用环境变量覆盖配置
docker run -d \
  --name gpu-monitor \
  -p 8080:8080 \
  -v ${PWD}/config.yaml:/app/config.yaml \
  -e PROM_URL=http://prometheus:9090 \
  -e THRESHOLD=20 \
  -e AI_ENABLED=true \
  -e AI_API_KEY=sk-your-key \
  gpu-monitor:latest
```

### Kubernetes 部署

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: gpu-monitor-config
  namespace: monitoring
data:
  config.yaml: |
    prometheus:
      url: "http://prometheus.monitoring:9090"
    thresholds:
      low_utilization: 20
    scheduler:
      interval: 300
      max_workers: 8
    ai:
      enabled: true
      api_url: "https://api.openai.com/v1/chat/completions"
      model: "gpt-4"

---
apiVersion: v1
kind: Secret
metadata:
  name: gpu-monitor-secret
  namespace: monitoring
type: Opaque
stringData:
  ai-api-key: "sk-your-secret-key"

---
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
        - name: http
          containerPort: 8080
        volumeMounts:
        - name: config
          mountPath: /app/config.yaml
          subPath: config.yaml
        env:
        - name: AI_API_KEY
          valueFrom:
            secretKeyRef:
              name: gpu-monitor-secret
              key: ai-api-key
        livenessProbe:
          httpGet:
            path: /health
            port: http
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: http
          initialDelaySeconds: 5
          periodSeconds: 10
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
      volumes:
      - name: config
        configMap:
          name: gpu-monitor-config

---
apiVersion: v1
kind: Service
metadata:
  name: gpu-monitor
  namespace: monitoring
  labels:
    app: gpu-monitor
spec:
  type: ClusterIP
  ports:
  - name: http
    port: 80
    targetPort: 8080
  selector:
    app: gpu-monitor
```

## ⚙️ 配置说明

### 配置方式

**主要配置：** `config.yaml` 文件
**覆盖配置：** 环境变量（可选）

**优先级：** 环境变量 > config.yaml > 默认值

### 核心配置项

#### Prometheus 配置
```yaml
prometheus:
  url: "http://prometheus:9090"    # Prometheus 地址
  time_window_min: 10               # 时间窗口（分钟）
  step: "30s"                       # 查询步长
```

#### 评分权重配置
```yaml
scoring:
  gpu_util_weight: 0.5      # GPU 核心使用率权重（50%）
  mem_copy_weight: 0.2      # 内存带宽使用率权重（20%）
  mem_used_weight: 0.2      # 显存使用权重（20%）
  power_weight: 0.1         # 功率权重（10%）
```

#### 阈值配置
```yaml
thresholds:
  low_utilization: 20       # 低利用率阈值（%）
  idle: 10                  # 闲置阈值（%）
```

#### 调度配置
```yaml
scheduler:
  interval: 300             # 轮询周期（秒）
  max_workers: 8            # 最大并发线程数
```

#### AI 配置（可选）
```yaml
ai:
  enabled: false            # 是否启用 AI 分析
  api_url: ""               # AI API 地址
  api_key: ""               # API 密钥（建议用环境变量）
  model: "gpt-4"            # AI 模型
  threshold: 0.7            # 置信度阈值
```

#### 控制接口配置（可选）
```yaml
control:
  enabled: false            # 是否启用控制接口
  api_url: ""               # 控制接口地址
  timeout: 5                # 超时时间（秒）
```

### 环境变量覆盖

```powershell
# 覆盖关键配置
$env:PROM_URL="http://production-prometheus:9090"
$env:THRESHOLD="25"
$env:INTERVAL="600"

# AI 配置（推荐用环境变量保护密钥）
$env:AI_ENABLED="true"
$env:AI_API_KEY="sk-your-secret-key"
```

### 配置调整建议

| 场景 | interval | max_workers | threshold |
|------|----------|-------------|-----------|
| 开发环境 | 120-180 | 4-8 | 15-20 |
| 生产环境 | 300-600 | 8-16 | 20-25 |
| 大规模（>100 GPU） | 600-900 | 16-32 | 20-30 |

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

## 🤖 AI 智能分析

### 启用 AI 分析

编辑 `config.yaml`：

```yaml
ai:
  enabled: true
  api_url: "https://api.openai.com/v1/chat/completions"
  model: "gpt-4"
```

设置 API Key（环境变量）：
```powershell
$env:AI_API_KEY="sk-your-api-key"
```

### AI 分析功能

AI 会分析最近 10 分钟的 GPU 时序数据，包括：
- GPU 利用率波动
- 显存使用趋势
- 功率变化
- 内存带宽活动

**AI 输出结果：**
- `status`: active/idle/suspicious
- `confidence`: 置信度 (0-1)
- `reason`: 判断理由（中文）
- `recommendation`: 操作建议
- `ai_adjusted_score`: AI 调整后的评分

### 支持的 AI 模型

| 提供商 | 模型 | 配置示例 |
|--------|------|---------|
| OpenAI | gpt-4, gpt-3.5-turbo | `model: "gpt-4"` |
| Claude | claude-3-opus, claude-3-sonnet | `model: "claude-3-opus"` |
| Azure OpenAI | 自定义部署 | 修改 api_url |
| 本地模型 | 兼容 OpenAI 格式 | 使用本地 API 地址 |

### 手动触发 AI 分析

```powershell
# 触发一次带 AI 的分析
curl http://localhost:8080/analyze?use_ai=true

# 查看 AI 分析结果
curl http://localhost:8080/results | jq '.[] | select(.ai_analysis != null)'
```

## 📊 Prometheus 集成

### Prometheus 配置

在 `prometheus.yml` 中添加抓取配置：

```yaml
scrape_configs:
  - job_name: 'gpu-monitor'
    static_configs:
      - targets: ['gpu-monitor:8080']
    metrics_path: '/metrics'
    scrape_interval: 30s
    scrape_timeout: 10s
```

### PromQL 查询示例

```promql
# 平均 GPU 评分
avg(gpu_utilization_score)

# 低利用率 GPU 数量
gpu_low_utilization_count

# 按命名空间统计
sum(gpu_utilization_score) by (namespace)

# 高利用率 GPU（>70%）
count(gpu_utilization_score > 70)

# AI 判断为闲置的 GPU
count(gpu_ai_analysis_confidence{ai_status="idle"})
```

### Grafana Dashboard

推荐面板：
1. **GPU 评分分布** - 直方图
2. **低利用率 GPU 列表** - 表格
3. **命名空间使用统计** - 柱状图
4. **AI 分析成功率** - 折线图
5. **评分趋势** - 时序图

## 📢 告警集成

### 飞书机器人通知

创建 webhook 集成：

```python
import requests

def send_feishu_alert(low_util_gpus):
    webhook_url = "https://open.feishu.cn/open-apis/bot/v2/hook/YOUR_WEBHOOK"
    
    content = "⚠️ **GPU 低利用率告警**\n\n"
    for gpu in low_util_gpus:
        content += f"- **{gpu['namespace']}/{gpu['pod']}**\n"
        content += f"  - 评分: {gpu['score']}%\n"
        if gpu.get('ai_analysis'):
            content += f"  - AI: {gpu['ai_analysis']['reason']}\n"
    
    payload = {
        "msg_type": "text",
        "content": {"text": content}
    }
    requests.post(webhook_url, json=payload)
```

## 📁 项目结构

```
gpu-oour/
├── app/                      # 应用模块
│   ├── __init__.py
│   ├── config.py            # 配置管理
│   ├── models.py            # 数据模型
│   ├── prometheus_client.py # Prometheus 客户端
│   ├── gpu_analyzer.py      # GPU 分析器
│   ├── ai_analyzer.py       # AI 分析模块
│   ├── metrics_exporter.py  # Metrics 导出器
│   ├── scheduler.py         # 调度器
│   ├── utils.py             # 工具函数
│   └── exceptions.py        # 异常定义
├── main.py                  # 主应用入口
├── config.yaml              # 配置文件
├── requirements.txt         # 依赖管理
├── Dockerfile               # Docker 镜像
├── README.md               # 项目说明
└── .gitignore              # Git 忽略配置
```

## 🔧 开发指南

### 本地开发

```powershell
# 启用调试日志
$env:LOG_LEVEL="DEBUG"

# 减小轮询周期（快速测试）
$env:INTERVAL="60"

# 启动服务
python main.py
```

### 代码风格

- 遵循 PEP 8
- 使用类型注解
- 添加文档字符串
- 单元测试覆盖

### 扩展功能

要添加新功能，遵循模块化原则：

1. 在 `app/` 下创建新模块
2. 定义清晰的接口
3. 在 `main.py` 中注册端点
4. 更新配置文件

## 🐛 故障排查

### 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| 连接 Prometheus 失败 | URL 错误或网络不通 | 检查 `config.yaml` 中的 URL |
| 查询不到 GPU 数据 | DCGM exporter 未部署 | 确认 `DCGM_FI_DEV_GPU_UTIL{pod!=""}` 有数据 |
| AI 分析失败 | API Key 无效或配额不足 | 检查环境变量和 API 状态 |
| Metrics 未更新 | 调度器未运行 | 查看 `/health` 端点 |
| 服务启动失败 | 配置错误 | 查看启动日志 |

### 日志查看

```powershell
# Windows 控制台输出
# 或设置日志级别
$env:LOG_LEVEL="DEBUG"
python main.py
```

### 健康检查

```powershell
curl http://localhost:8080/health
```

返回示例：
```json
{
  "status": "healthy",
  "prometheus_connected": true,
  "last_analysis": "2025-10-26T10:30:00",
  "analysis_timeout": false,
  "ai_enabled": true,
  "interval": 300
}
```

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

### 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 🙏 致谢

- FastAPI - 现代化的 Web 框架
- Prometheus - 强大的监控系统
- OpenAI - AI 能力支持

## 📧 联系方式

如有问题请提交 Issue 或联系项目维护者。

---

**⭐ 如果这个项目对你有帮助，请给个 Star！**

