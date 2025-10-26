# GPU 监控服务配置说明

## 📝 配置方式

### 方式 1：只使用 config.yaml（推荐）

直接修改 `config.yaml` 文件中的配置项即可。

**优点：**
- ✅ 配置集中管理
- ✅ 结构化清晰
- ✅ 支持注释
- ✅ 适合版本控制

### 方式 2：使用环境变量覆盖（可选）

环境变量会覆盖 YAML 文件中的配置。

**优先级：** 环境变量 > config.yaml > 默认值

**适用场景：**
- 临时修改配置（测试）
- 生产环境敏感信息（API Key）
- 容器化部署动态配置

---

## 🔧 配置项详解

### 1. Prometheus 配置

```yaml
prometheus:
  url: "http://prometheus:9090"    # Prometheus 服务地址
  query_condition: '{pod!=""}'     # 查询条件（固定）
  time_window_min: 10              # 时间窗口（分钟）
  step: "30s"                      # 查询步长
```

**说明：**
- `url`: Prometheus 服务地址，需要能够访问
- `time_window_min`: 计算评分时使用的时间窗口
- `step`: 查询时序数据的步长，越小越精确但查询越慢

**环境变量覆盖：**
```bash
PROM_URL=http://your-prometheus:9090
TIME_WINDOW_MIN=15
```

---

### 2. 评分权重配置

```yaml
scoring:
  gpu_util_weight: 0.5      # GPU 核心使用率权重（默认 50%）
  mem_copy_weight: 0.2      # 内存带宽使用率权重（默认 20%）
  mem_used_weight: 0.2      # 显存使用权重（默认 20%）
  power_weight: 0.1         # 功率使用权重（默认 10%）
```

**说明：**
- 四个权重之和应为 1.0
- 可根据实际场景调整权重
- GPU 核心利用率通常最重要

**调整建议：**
- 训练场景：GPU 核心利用率权重可以更高 (0.6)
- 推理场景：内存带宽权重可以更高 (0.3)
- 显存密集型：显存使用权重可以更高 (0.3)

---

### 3. 阈值配置

```yaml
thresholds:
  low_utilization: 20       # 低利用率阈值（%）
  idle: 10                  # 闲置阈值（%）
```

**说明：**
- `low_utilization`: 低于此值会被标记为低利用率，触发告警
- `idle`: 低于此值会被标记为完全闲置

**推荐值：**
- 严格环境：15-20
- 一般环境：20-25
- 宽松环境：25-30

**环境变量覆盖：**
```bash
THRESHOLD=15  # 覆盖 low_utilization
```

---

### 4. 调度配置

```yaml
scheduler:
  interval: 300             # 轮询周期（秒）
  max_workers: 8            # 最大并发线程数
```

**说明：**
- `interval`: 自动分析的时间间隔
- `max_workers`: 并发查询 GPU 的线程数

**调整建议：**

| GPU 数量 | interval | max_workers |
|----------|----------|-------------|
| < 10     | 180-300  | 4-8         |
| 10-50    | 300-600  | 8-16        |
| 50-100   | 600-900  | 16-32       |
| > 100    | 900-1200 | 32-64       |

**环境变量覆盖：**
```bash
INTERVAL=600
MAX_WORKERS=16
```

---

### 5. GPU 默认配置

```yaml
gpu_defaults:
  memory_mb: 32000          # 默认显存（MB）
  power_w: 250              # 默认功率（W）
```

**说明：**
- 用于归一化计算，当无法获取实际值时使用
- V100S: 32GB / 250W
- A100: 40GB / 400W
- T4: 16GB / 70W

**根据你的 GPU 型号调整！**

---

### 6. 控制接口配置

```yaml
control:
  enabled: false            # 是否启用控制接口调用
  api_url: "http://your-control-service/api/optimize"
  timeout: 5                # 超时时间（秒）
```

**说明：**
- 当检测到低利用率 GPU 时，自动调用此接口
- 接口会收到包含 GPU 信息和评分的 JSON

**请求格式：**
```json
{
  "gpu_id": "GPU-xxx",
  "pod": "pod-name",
  "namespace": "namespace",
  "hostname": "node-name",
  "score": 5.2,
  "status": "idle",
  "timestamp": "2025-10-26T10:30:00",
  "ai_analysis": {  // 如果启用 AI
    "status": "idle",
    "confidence": 0.92,
    "reason": "...",
    "recommendation": "..."
  }
}
```

**环境变量覆盖：**
```bash
CONTROL_API_ENABLED=true
CONTROL_API=http://production-api/optimize
```

---

### 7. AI 分析配置

```yaml
ai:
  enabled: false            # 是否启用 AI 智能分析
  api_url: ""               # AI API 地址
  api_key: ""               # AI API 密钥
  model: "gpt-4"            # AI 模型
  threshold: 0.7            # 置信度阈值
```

**说明：**
- 启用后，会调用 AI 模型进行智能判断
- 支持 OpenAI、Claude 等兼容 OpenAI 格式的 API

**支持的模型：**
- OpenAI: `gpt-4`, `gpt-3.5-turbo`
- Claude: `claude-3-opus`, `claude-3-sonnet`
- 其他兼容 OpenAI 的 API

**配置示例：**

#### OpenAI
```yaml
ai:
  enabled: true
  api_url: "https://api.openai.com/v1/chat/completions"
  api_key: "sk-your-key"  # 建议用环境变量
  model: "gpt-4"
```

#### Azure OpenAI
```yaml
ai:
  enabled: true
  api_url: "https://your-resource.openai.azure.com/openai/deployments/gpt-4/chat/completions?api-version=2023-05-15"
  api_key: "your-azure-key"
  model: "gpt-4"
```

#### 本地模型（兼容 OpenAI 格式）
```yaml
ai:
  enabled: true
  api_url: "http://localhost:8000/v1/chat/completions"
  api_key: "not-needed"
  model: "local-model"
```

**安全建议：**
⚠️ **API Key 不要直接写在 config.yaml 中！**

使用环境变量：
```bash
AI_API_KEY=sk-your-secret-key
```

或在启动时设置：
```powershell
$env:AI_API_KEY="sk-your-secret-key"
python main.py
```

**环境变量覆盖：**
```bash
AI_ENABLED=true
AI_API_URL=https://api.openai.com/v1/chat/completions
AI_API_KEY=sk-your-key  # 推荐方式
AI_MODEL=gpt-4
```

---

### 8. 日志配置

```yaml
logging:
  level: "INFO"             # 日志级别
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

**日志级别：**
- `DEBUG`: 详细调试信息
- `INFO`: 一般信息（推荐）
- `WARNING`: 警告信息
- `ERROR`: 错误信息

**环境变量覆盖：**
```bash
LOG_LEVEL=DEBUG
```

---

## 📊 完整配置示例

### 场景 1：开发环境
```yaml
prometheus:
  url: "http://localhost:9090"
  time_window_min: 5

thresholds:
  low_utilization: 15

scheduler:
  interval: 120  # 2 分钟

ai:
  enabled: false  # 开发环境不用 AI

logging:
  level: "DEBUG"
```

### 场景 2：生产环境
```yaml
prometheus:
  url: "http://prometheus.monitoring:9090"
  time_window_min: 10

thresholds:
  low_utilization: 20

scheduler:
  interval: 300  # 5 分钟

control:
  enabled: true
  api_url: "http://resource-controller/api/optimize"

ai:
  enabled: true
  api_url: "https://api.openai.com/v1/chat/completions"
  # API Key 通过环境变量设置
  model: "gpt-4"

logging:
  level: "INFO"
```

### 场景 3：大规模集群（>100 GPU）
```yaml
prometheus:
  url: "http://prometheus:9090"
  time_window_min: 5  # 减小窗口

thresholds:
  low_utilization: 20

scheduler:
  interval: 600  # 10 分钟（减少频率）
  max_workers: 32  # 增加并发

ai:
  enabled: false  # 关闭 AI（提高性能）

logging:
  level: "WARNING"  # 减少日志
```

---

## 🔒 安全最佳实践

### 1. 敏感信息保护

**不要在 config.yaml 中写入：**
- ❌ AI API Key
- ❌ 控制接口密钥
- ❌ 任何密码或 Token

**使用环境变量：**
```bash
export AI_API_KEY="sk-your-secret-key"
export CONTROL_API_TOKEN="your-token"
```

### 2. 文件权限

```bash
# 限制配置文件权限
chmod 600 config.yaml
```

### 3. 版本控制

```bash
# .gitignore
config.yaml          # 不提交配置文件
.env                 # 不提交环境变量文件
```

提交模板：
```bash
# 提交示例配置
config.yaml.example
```

---

## 🔄 配置热更新

目前配置在服务启动时加载，修改后需要重启服务。

**重启服务：**
```powershell
# 停止服务
Ctrl + C

# 重新启动
python main.py
```

---

## ✅ 配置验证

启动时会自动验证配置：

```python
# 验证项：
1. AI 启用时必须设置 API URL
2. 阈值必须在 0-100 之间
3. Prometheus 连接测试
```

**查看当前配置：**
```powershell
curl http://localhost:8080/config
```

---

## 📞 获取帮助

- 查看示例配置：`config.yaml`
- 查看环境变量示例：`env.example`
- 查看完整文档：`README.md`

