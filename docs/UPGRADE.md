# GPU 利用率监控系统 - 新版说明

## 🎉 v2.0 重大更新

### ✨ 新功能

1. **模块化架构** - 代码拆分为多个独立模块，易于维护和扩展
2. **Prometheus Metrics 导出** - 新增 `/metrics` 端点，支持 Prometheus 抓取
3. **AI 智能分析** - 集成 AI 模型，智能判断 GPU 使用状态

### 📁 新的文件结构

```
gpu-oour/
├── app/
│   ├── __init__.py              # 包初始化
│   ├── config.py                # 配置管理
│   ├── models.py                # 数据模型
│   ├── prometheus_client.py     # Prometheus 查询客户端
│   ├── gpu_analyzer.py          # GPU 分析器
│   ├── ai_analyzer.py           # AI 分析模块
│   ├── metrics_exporter.py      # Metrics 导出器
│   └── scheduler.py             # 调度器
├── main.py                      # 主应用入口（新）
├── gpu_monitor.py               # 旧版本（保留）
├── requirements.txt             # 更新依赖
└── ...
```

### 🚀 快速开始

#### 1. 安装依赖

```powershell
pip install -r requirements.txt
```

#### 2. 配置环境变量

```powershell
# 基础配置
$env:PROM_URL="http://your-prometheus:9090"
$env:THRESHOLD="20"
$env:INTERVAL="300"

# AI 配置（可选）
$env:AI_ENABLED="true"
$env:AI_API_URL="https://api.openai.com/v1/chat/completions"
$env:AI_API_KEY="your-api-key"
$env:AI_MODEL="gpt-4"
```

#### 3. 启动服务

```powershell
# 使用新版本（推荐）
uvicorn main:app --host 0.0.0.0 --port 8080

# 或者使用 Python
python main.py
```

### 📊 新增的 Prometheus Metrics

访问 `http://localhost:8080/metrics` 可以获取以下 metrics：

#### GPU 指标

- `gpu_utilization_score` - GPU综合利用率评分 (0-100)
- `gpu_core_utilization` - GPU核心利用率 (%)
- `gpu_memory_used_mb` - GPU显存使用量 (MB)
- `gpu_power_usage_watts` - GPU功率使用 (W)
- `gpu_memory_copy_utilization` - GPU内存拷贝利用率 (%)
- `gpu_sm_clock_mhz` - GPU SM时钟频率 (MHz)

#### AI 分析指标

- `gpu_ai_analysis_confidence` - AI分析置信度 (0-1)
- `gpu_ai_adjusted_score` - AI调整后的评分 (0-100)

#### 统计指标

- `gpu_total_count` - GPU总数
- `gpu_low_utilization_count` - 低利用率GPU数量
- `gpu_idle_count` - 闲置GPU数量
- `gpu_average_score` - 平均GPU评分
- `gpu_status_count{status}` - GPU状态分布
- `gpu_namespace_count{namespace}` - 各命名空间GPU数量
- `gpu_namespace_average_score{namespace}` - 各命名空间平均评分

#### 服务指标

- `gpu_analysis_total` - GPU分析总次数
- `gpu_analysis_errors_total` - GPU分析错误次数
- `gpu_analysis_duration_seconds` - GPU分析耗时 (秒)

### 🤖 AI 分析功能

启用 AI 分析后，系统会：

1. 收集最近10分钟的 GPU 时序数据
2. 计算统计特征（均值、方差、变化率等）
3. 调用 AI API 进行智能判断
4. 返回：
   - 状态（active/idle/suspicious）
   - 置信度（0-1）
   - 判断理由
   - 操作建议
   - 调整后的评分

**支持的 AI API：**
- OpenAI (GPT-4, GPT-3.5)
- Claude
- 其他兼容 OpenAI 格式的 API

### 📝 API 端点

| 端点 | 说明 | 新增 |
|------|------|------|
| `GET /` | 服务信息 | |
| `GET /health` | 健康检查 | |
| `GET /analyze` | 触发分析 | 支持 `?use_ai=true` |
| `GET /results` | 获取结果 | 包含 AI 分析 |
| `GET /results/low` | 低利用率GPU | |
| `GET /results/stats` | 统计信息 | |
| **`GET /metrics`** | **Prometheus metrics** | ✅ 新增 |
| `GET /config` | 获取配置 | ✅ 新增 |
| `POST /config/update` | 更新配置 | ✅ 新增 |

### 📈 Prometheus 集成示例

#### 1. Prometheus 配置

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'gpu-monitor'
    static_configs:
      - targets: ['gpu-monitor:8080']
    metrics_path: '/metrics'
    scrape_interval: 30s
```

#### 2. 查询示例

```promql
# 平均 GPU 评分
avg(gpu_utilization_score)

# 低利用率 GPU 数量
gpu_low_utilization_count

# 按命名空间统计
sum(gpu_utilization_score) by (namespace)

# AI 分析置信度
avg(gpu_ai_analysis_confidence) by (ai_status)
```

#### 3. Grafana Dashboard

可以创建 Dashboard 展示：
- GPU 评分趋势图
- 低利用率告警面板
- 命名空间使用情况
- AI 分析统计

### 🔧 配置说明

#### 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `PROM_URL` | Prometheus 地址 | `http://prometheus:9090` |
| `THRESHOLD` | 低利用率阈值 | `20` |
| `INTERVAL` | 轮询周期（秒） | `300` |
| `MAX_WORKERS` | 最大并发线程 | `8` |
| `TIME_WINDOW_MIN` | 时间窗口（分钟） | `10` |
| `AI_ENABLED` | 启用 AI 分析 | `false` |
| `AI_API_URL` | AI API 地址 | - |
| `AI_API_KEY` | AI API 密钥 | - |
| `AI_MODEL` | AI 模型 | `gpt-4` |
| `CONTROL_API_ENABLED` | 启用控制接口 | `false` |
| `CONTROL_API` | 控制接口地址 | - |

### 🎯 使用示例

#### 1. 启用 AI 分析

```powershell
# 设置环境变量
$env:AI_ENABLED="true"
$env:AI_API_URL="https://api.openai.com/v1/chat/completions"
$env:AI_API_KEY="sk-your-api-key"

# 启动服务
python main.py
```

#### 2. 手动触发 AI 分析

```powershell
curl http://localhost:8080/analyze?use_ai=true
```

#### 3. 查看 AI 分析结果

```powershell
curl http://localhost:8080/results | jq '.[] | select(.ai_analysis != null)'
```

#### 4. 导出 Prometheus Metrics

```powershell
curl http://localhost:8080/metrics
```

### 🔄 从旧版本迁移

旧版本 `gpu_monitor.py` 仍然保留，可以继续使用。

新版本主要改进：
1. 模块化设计，代码更清晰
2. 新增 Prometheus metrics 导出
3. 集成 AI 智能分析
4. 更强大的配置管理

建议逐步迁移到新版本。

### 📚 模块说明

#### app/config.py
配置管理，支持环境变量和默认值

#### app/models.py
数据模型定义（Pydantic）

#### app/prometheus_client.py
Prometheus 查询客户端，封装所有 Prometheus API 调用

#### app/gpu_analyzer.py
GPU 分析器，计算评分和状态判定

#### app/ai_analyzer.py
AI 分析模块，调用 LLM API 进行智能判断

#### app/metrics_exporter.py
Prometheus metrics 导出器

#### app/scheduler.py
后台调度器，定时执行分析任务

#### main.py
主应用入口，FastAPI 应用定义

### 🐛 故障排查

#### AI 分析失败

检查配置：
```powershell
curl http://localhost:8080/config
```

查看日志：
```
AI analysis failed for GPU-xxx: ...
```

#### Metrics 未更新

确认分析任务执行：
```powershell
curl http://localhost:8080/health
```

### 📞 获取帮助

- 查看完整文档：`README.md`
- 查看使用示例：`EXAMPLES.md`
- 查看部署指南：`DEPLOYMENT.md`

---

## 升级日志

### v2.0.0 (2025-10-26)
- ✅ 模块化重构
- ✅ 新增 Prometheus metrics 导出
- ✅ 集成 AI 智能分析
- ✅ 动态配置更新
- ✅ 改进日志输出

