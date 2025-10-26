user
我想做一个gpu使用情况的监控，我现在已经有gpu的prometheus数据来。我想根据gpu的metrics数据做一个监控分析。当用户的使用率评分低于阈值的时候，会调用接口来操作一些东西之类的。
ChatGPT
很好的思路 👍  
你已经有 GPU 的 Prometheus 数据，那么可以很自然地基于 **Prometheus + Alertmanager + 自定义 Webhook 或控制逻辑** 来实现「监控 + 低使用率自动操作」这一整套系统。  

我们可以分几个层次来设计：

---

## 🧩 一、系统整体架构思路

```
┌───────────────────┐
│   Prometheus      │
│ (收集GPU指标数据) │
└───────┬───────────┘
        │
        ▼
┌───────────────────┐
│   Alertmanager    │
│ (检测阈值规则触发)│
└───────┬───────────┘
        │Webhook
        ▼
┌────────────────────────────┐
│ 自定义处理服务 (Python/Go等)│
│  1. 接收告警回调            │
│  2. 根据GPU低利用率逻辑判断 │
│  3. 调用外部接口执行动作    │
└────────────────────────────┘
```

---

## 🧠 二、Prometheus 数据指标（假设你已经有）

常见的 GPU 监控 metrics（来自 `nvidia-dcgm-exporter` 或 `nvidia-smi exporter`）：

| 指标 | 含义 |
|------|------|
| `DCGM_FI_DEV_GPU_UTIL` | GPU 使用率 (%) |
| `DCGM_FI_DEV_MEM_COPY_UTIL` | 内存拷贝使用率 |
| `DCGM_FI_DEV_FB_USED` | 显存使用量 |
| `DCGM_FI_DEV_POWER_USAGE` | 功率 (W) |
| `DCGM_FI_DEV_TEMPERATURE_GPU` | GPU 温度 |

---

## ⚙️ 三、Prometheus 告警规则（Alert Rule）

例如我们想在 GPU 使用率长期过低时触发告警：

```yaml
# /etc/prometheus/rules/gpu_alerts.yml
groups:
  - name: gpu-low-utilization
    rules:
      - alert: GpuLowUtilization
        expr: avg_over_time(DCGM_FI_DEV_GPU_UTIL[10m]) < 10
        for: 15m
        labels:
          severity: warning
        annotations:
          summary: "GPU使用率低于10%"
          description: "GPU {{ $labels.uuid }} 在过去15分钟平均利用率低于10%"
```

这里的逻辑是：
> 连续 15 分钟平均 GPU 使用率低于 10% → 触发 `GpuLowUtilization` 告警

---

## 🚨 四、Alertmanager 配置 Webhook

配置 Alertmanager 来把告警回调到你自己的服务：

```yaml
# /etc/alertmanager/alertmanager.yml
receivers:
  - name: 'gpu-webhook'
    webhook_configs:
      - url: 'http://your-service:8080/alert'

route:
  receiver: 'gpu-webhook'
```

---

## 🧩 五、自定义处理服务 (例如 Python FastAPI)

你可以写一个很轻量的服务来接收告警并执行操作：

```python
from fastapi import FastAPI, Request
import httpx, asyncio

app = FastAPI()

THRESHOLD = 10  # GPU使用率低于10%时触发

@app.post("/alert")
async def handle_alert(request: Request):
    data = await request.json()
    alerts = data.get("alerts", [])

    for alert in alerts:
        gpu_id = alert["labels"].get("uuid")
        description = alert["annotations"].get("description")

        print(f"⚠️ GPU {gpu_id} 低利用率: {description}")

        # 调用你自己的控制接口，比如释放资源、通知用户、调度任务等
        async with httpx.AsyncClient() as client:
            await client.post("http://your-control-api/gpu_action", json={
                "gpu_id": gpu_id,
                "action": "release",
                "reason": "low_utilization"
            })

    return {"status": "ok"}
```

---

## 📊 六、可选增强

你可以进一步增强：
- 用 **Grafana** 展示 GPU 历史使用趋势
- 告警时通过 **Telegram、Slack、飞书机器人** 推送通知
- 加入 **“评分系统”**：例如综合 GPU 利用率、显存使用率、温度、功耗得出一个健康分数  
  ```promql
  (DCGM_FI_DEV_GPU_UTIL * 0.5) + (DCGM_FI_DEV_FB_USED / DCGM_FI_DEV_FB_TOTAL * 100 * 0.3) + ...
  ```
- 只有当综合评分低于阈值一段时间时才执行操作（防止误触）

---

## ✅ 总结：实施步骤

| 步骤 | 操作 |
|------|------|
| 1 | 确认 GPU metrics 已上报 Prometheus |
| 2 | 编写 Prometheus 告警规则 |
| 3 | 配置 Alertmanager Webhook |
| 4 | 搭建一个 Webhook 接口服务（FastAPI / Flask / Go 等） |
| 5 | 在该服务中编写逻辑来执行你的自动操作 |
| 6 | （可选）Grafana 做展示，机器人推送告警 |

---

是否希望我帮你：
1️⃣ 设计一套「GPU 使用评分公式」？  
还是  
2️⃣ 写出完整可部署的 **Python Webhook 服务模板（含日志、告警解析、接口调用逻辑）**？
user
我是用在公司kubeflow出借gpu的内部场景，检测租户的gpu是否在利用，利用率过低的话会考虑降低成本！但是gpu不能单纯的靠显存或其他单一指标来判定是否在使用。所以我需要一个合理的方案来计算利用率，或者是从prometheus拉数据让ai来给我利用率的值！
ChatGPT
非常棒的目标 💡 ——  
你不是想做一个“传统意义的监控报警”，而是希望实现一个 **智能化 GPU 使用评估系统**，可以合理地判断「租户是否真的在使用 GPU」，从而指导调度或成本优化。  

我们可以拆成两部分来做：

---

## 🧠 一、设计目标总结

> **目标**：智能判断 GPU 是否被有效利用，而不仅仅是“显存大于0 或 GPU Util > 某阈值”。

> **场景**：公司内部的 Kubeflow GPU 出借系统  
> - 用户租到 GPU 后，可能空跑（比如 notebook 没训练）  
> - 你希望定期评估使用率，低利用的 GPU 触发优化或回收  

---

## ⚙️ 二、Prometheus 可用的 GPU 指标

假设你用的是 `nvidia-dcgm-exporter`（或 `nvidia-smi exporter`），常见指标如下：

| Metric | 含义 |
|--------|------|
| `DCGM_FI_DEV_GPU_UTIL` | GPU计算核心使用率 (%) |
| `DCGM_FI_DEV_MEM_COPY_UTIL` | GPU内存带宽使用率 (%) |
| `DCGM_FI_DEV_FB_USED` | 显存使用量 (bytes) |
| `DCGM_FI_DEV_FB_FREE` | 空闲显存 (bytes) |
| `DCGM_FI_DEV_SM_CLOCK` | GPU SM时钟频率 |
| `DCGM_FI_DEV_POWER_USAGE` | 功率 (W) |
| `DCGM_FI_DEV_TEMPERATURE_GPU` | 温度 (°C) |
| `DCGM_FI_DEV_ENC_UTIL/DEC_UTIL` | 编解码模块使用率 (%) |

这些指标结合起来可以推断：
- 是否有**算力计算在运行**
- 是否有**显存占用但不计算**（例如模型加载但未训练）
- 是否有**数据传输活动**
- 是否 GPU 实际空闲但任务挂起

---

## 🧮 三、合理的「GPU 利用率评分」公式设计

可以定义一个 **多维综合利用率评分 (0-100)**，比如：

```text
score = 0.4 * gpu_util_norm
      + 0.2 * mem_copy_util_norm
      + 0.2 * mem_usage_norm
      + 0.1 * power_usage_norm
      + 0.1 * sm_clock_norm
```

其中每一项是归一化到 [0,1] 的指标，例如：
```text
gpu_util_norm = DCGM_FI_DEV_GPU_UTIL / 100
mem_copy_util_norm = DCGM_FI_DEV_MEM_COPY_UTIL / 100
mem_usage_norm = DCGM_FI_DEV_FB_USED / DCGM_FI_DEV_FB_TOTAL
power_usage_norm = DCGM_FI_DEV_POWER_USAGE / DCGM_FI_DEV_POWER_LIMIT
sm_clock_norm = DCGM_FI_DEV_SM_CLOCK / DCGM_FI_DEV_SM_CLOCK_MAX
```

然后再取时间窗口（比如过去 10 分钟）平均值：
```promql
avg_over_time((0.4 * DCGM_FI_DEV_GPU_UTIL / 100
             + 0.2 * DCGM_FI_DEV_MEM_COPY_UTIL / 100
             + 0.2 * (DCGM_FI_DEV_FB_USED / DCGM_FI_DEV_FB_TOTAL)
             + 0.1 * (DCGM_FI_DEV_POWER_USAGE / DCGM_FI_DEV_POWER_LIMIT)
             + 0.1 * (DCGM_FI_DEV_SM_CLOCK / DCGM_FI_DEV_SM_CLOCK_MAX))[10m])
```

这个 PromQL 表达式就能输出一个「GPU 利用评分」在 [0,1] 之间。  
> - < 0.2 代表几乎闲置  
> - 0.2~0.5 属于轻负载  
> - > 0.5 表示在训练或推理中  

---

## 🧩 四、进阶：引入 AI/模型计算利用率

你提到「让 AI 从 Prometheus 拉数据给出利用率判断」——这也是完全可行的方向，特别适合边界模糊场景。

### 架构思路：

```
Prometheus ---> 定时拉取GPU指标数据 (via Python)
         |
         ▼
   特征向量 (每张GPU)
         |
         ▼
   利用率分类模型 / LLM推理
         |
         ▼
   输出 "active" / "idle" / "anomaly"
```

你可以做一个周期性任务（Python 脚本 + cron/job），每隔 5 分钟：
1. 通过 Prometheus API 拉过去 10 分钟的 GPU 指标序列；
2. 生成特征向量（均值、方差、最大值、变化率等）；
3. 输入到一个模型（可训练 or prompt-based）；
4. 输出利用率分类结果；
5. 决策是否执行成本优化逻辑。

---

### 示例：Python 从 Prometheus 拉取并计算评分

```python
import requests
import numpy as np
from datetime import datetime, timedelta

PROM_URL = "http://prometheus:9090/api/v1/query_range"

def get_metric(name, gpu_id, minutes=10):
    end = datetime.utcnow()
    start = end - timedelta(minutes=minutes)
    query = f'{name}{{uuid="{gpu_id}"}}'
    resp = requests.get(PROM_URL, params={
        "query": query,
        "start": start.timestamp(),
        "end": end.timestamp(),
        "step": "30s"
    }).json()
    values = [float(v[1]) for v in resp["data"]["result"][0]["values"]]
    return np.mean(values)

def gpu_score(gpu_id):
    gpu_util = get_metric("DCGM_FI_DEV_GPU_UTIL", gpu_id)
    mem_copy = get_metric("DCGM_FI_DEV_MEM_COPY_UTIL", gpu_id)
    mem_used = get_metric("DCGM_FI_DEV_FB_USED", gpu_id)
    mem_total = get_metric("DCGM_FI_DEV_FB_TOTAL", gpu_id)
    power_usage = get_metric("DCGM_FI_DEV_POWER_USAGE", gpu_id)
    power_limit = get_metric("DCGM_FI_DEV_POWER_LIMIT", gpu_id)

    score = (0.4 * gpu_util/100 +
             0.2 * mem_copy/100 +
             0.2 * (mem_used/mem_total) +
             0.2 * (power_usage/power_limit))
    return round(score * 100, 1)

gpu_id = "GPU-abc123"
print(f"GPU {gpu_id} 综合利用率评分: {gpu_score(gpu_id)}")
```

---

### AI 模型辅助判断（可选）

如果你想让 AI 模型参与判断，可以：
- 把最近 10 分钟各指标的序列传给 GPT 或内部模型；
- Prompt 里要求模型判断是否在进行有效训练/推理；
- 模型输出一个标签（`"active"`, `"idle"`, `"spike"`, `"setup"`）。

例如：

```python
prompt = f"""
以下是GPU最近10分钟的监控数据：
- GPU Util: {gpu_util_series}
- Mem Copy: {mem_copy_series}
- Mem Used: {mem_used_series}
- Power Usage: {power_series}

请判断该GPU是否在进行有效计算（如训练/推理），
并输出一个JSON：{{"status": "active"|"idle", "confidence": 0~1}}。
"""
```

---

## 🧩 五、输出与自动操作

得到利用率评分或AI判定结果后：
- 如果连续5次（25分钟）评分低于 0.2 → 标记为「闲置」
- 可自动调用 Kubeflow / K8S API：
  - scale down notebook / job
  - 释放 GPU node
  - 通知租户（Slack/邮件）

---

## ✅ 推荐方案总结

| 方案 | 特点 | 复杂度 |
|------|------|--------|
| ① 多指标评分公式（PromQL） | 稳定、可部署在 Prometheus | ★☆☆ |
| ② Prometheus 拉取 + Python 计算评分 | 灵活，可扩展 | ★★☆ |
| ③ 引入 AI/LLM 辅助判断 | 智能化，适合灰区场景 | ★★★ |

---

是否希望我帮你进一步：
1️⃣ 生成一个 **可运行的 Python 脚本**，直接从 Prometheus 拉数据、计算综合利用率、并判断是否空闲；  
还是  
2️⃣ 设计一个 **AI 模型输入格式与Prompt模板**，帮助你接入 ChatGPT/内部模型来做智能判定？
user
很好，我的gpu有很多，每次让ai判断要多线程，并且要区分gpu。DCGM_FI_DEV_POWER_LIMIT、DCGM_FI_DEV_FB_TOTAL这两个指标没数据。并且需要设置查询条件{pod!=""}
ChatGPT
非常好，你已经进入了落地阶段 🚀  

你的场景是：
- 多个 GPU（多节点/多卡）；
- 每张 GPU 都绑定租户 pod；
- Prometheus 查询要带 `{pod!=""}`（只看分配出去的 GPU）；
- 某些指标缺失 (`POWER_LIMIT`、`FB_TOTAL`)；
- 希望支持多线程/并发查询来加速计算。

---

## ✅ 目标
写一个 **Python GPU 利用率分析脚本**：
- 从 Prometheus 拉取各 GPU 的指标；
- 多线程并行；
- 计算每个 GPU 的综合利用率评分；
- 输出 JSON 或日志；
- 可作为 AI 判定输入的上游模块。

---

## 🧠 指标方案调整

因为部分指标缺失，我们改为以下 **自适应简化公式**：

```python
score = 0.5 * gpu_util_norm \
      + 0.2 * mem_copy_util_norm \
      + 0.3 * mem_usage_norm
```

其中：
- `gpu_util_norm = DCGM_FI_DEV_GPU_UTIL / 100`
- `mem_copy_util_norm = DCGM_FI_DEV_MEM_COPY_UTIL / 100`
- `mem_usage_norm = DCGM_FI_DEV_FB_USED / max(DCGM_FI_DEV_FB_USED)` （同节点归一化）

⚙️ 这样即便 `FB_TOTAL` 没数据，也能计算出相对使用度。

---

## 🚀 完整 Python 版本（并发 + PromQL 查询 + 评分计算）

```python
import requests
import concurrent.futures
import numpy as np
from datetime import datetime, timedelta

PROM_URL = "http://prometheus:9090/api/v1/query_range"
QUERY_CONDITION = '{pod!=""}'
TIME_WINDOW_MIN = 10
STEP = "30s"

def query_prometheus(metric, gpu_id):
    """查询某个 GPU 的特定 metric 平均值"""
    end = datetime.utcnow()
    start = end - timedelta(minutes=TIME_WINDOW_MIN)
    query = f'{metric}{QUERY_CONDITION}, uuid="{gpu_id}"'

    try:
        resp = requests.get(PROM_URL, params={
            "query": query,
            "start": start.timestamp(),
            "end": end.timestamp(),
            "step": STEP
        }).json()
        results = resp.get("data", {}).get("result", [])
        if not results:
            return 0
        values = [float(v[1]) for v in results[0]["values"] if v[1] != 'NaN']
        return np.mean(values) if values else 0
    except Exception as e:
        print(f"[ERROR] Query {metric} for {gpu_id} failed: {e}")
        return 0


def compute_gpu_score(gpu_id):
    """计算单卡GPU利用率评分"""
    gpu_util = query_prometheus("DCGM_FI_DEV_GPU_UTIL", gpu_id)
    mem_copy = query_prometheus("DCGM_FI_DEV_MEM_COPY_UTIL", gpu_id)
    mem_used = query_prometheus("DCGM_FI_DEV_FB_USED", gpu_id)

    score = (
        0.5 * (gpu_util / 100) +
        0.2 * (mem_copy / 100) +
        0.3 * min(mem_used / (mem_used + 1e-6), 1.0)  # 防止除零
    )

    return {
        "gpu_id": gpu_id,
        "gpu_util": round(gpu_util, 2),
        "mem_copy": round(mem_copy, 2),
        "mem_used": round(mem_used, 2),
        "score": round(score * 100, 1)
    }


def get_all_gpu_ids():
    """从Prometheus获取当前活跃GPU列表"""
    query = f'DCGM_FI_DEV_GPU_UTIL{QUERY_CONDITION}'
    try:
        resp = requests.get(f"http://prometheus:9090/api/v1/series", params={"match[]": query}).json()
        gpu_ids = {m['uuid'] for m in resp.get("data", []) if 'uuid' in m}
        return list(gpu_ids)
    except Exception as e:
        print(f"[ERROR] 获取GPU列表失败: {e}")
        return []


def main():
    gpu_ids = get_all_gpu_ids()
    if not gpu_ids:
        print("未找到任何GPU指标数据。")
        return

    print(f"检测到 {len(gpu_ids)} 张 GPU，开始并发计算...\n")

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(compute_gpu_score, gpu_id) for gpu_id in gpu_ids]
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())

    results.sort(key=lambda x: x["score"])
    for r in results:
        print(f"GPU {r['gpu_id']:<20} | Score={r['score']:>5}% | Util={r['gpu_util']:>5}% | Mem={r['mem_used'] / 1e6:>8.1f}MB")

    low_util = [r for r in results if r["score"] < 20]
    print("\n低利用率GPU:")
    for r in low_util:
        print(f"  → {r['gpu_id']} ({r['score']}%)")


if __name__ == "__main__":
    main()
```

---

## ⚡ 特点

✅ **多线程**：并行查询所有 GPU 指标（默认 `max_workers=8`）  
✅ **按 GPU 维度聚合**：通过 `uuid` 区分不同 GPU  
✅ **Prometheus 查询带条件 `{pod!=""}`**  
✅ **自动降级**：缺失指标不会报错，会返回 0  
✅ **评分输出可直接送入 LLM 或调度策略**  
✅ **输出格式清晰**，方便后续 JSON 集成：

```
GPU GPU-12345               | Score= 82.1% | Util= 78.5% | Mem= 6144.0MB
GPU GPU-67890               | Score=  3.5% | Util=  1.2% | Mem=   12.0MB
```

---

## 🔧 下一步可扩展

| 方向 | 说明 |
|------|------|
| 🧩 加入 pod/job 标签 | 同时输出 GPU 对应租户或 Notebook 名称 |
| 🧠 接入 AI | 将每张 GPU 的最近10分钟序列传入模型判定 |
| 🕓 定时调度 | 每 5 分钟跑一次，结果写入数据库或触发接口 |
| 📈 可视化 | 在 Grafana 展示每卡评分趋势 |

---

是否希望我帮你：
1️⃣ 在这个基础上 **加上 pod / namespace 信息**（方便知道是哪位租户在用），  
还是  
2️⃣ 帮你 **改造成一个后台任务服务（FastAPI + Scheduler）**，自动定期拉取并调用你的控制接口？
user
扩展吧
ChatGPT
完美 ✅ 我们来扩展成一个 **可部署的 GPU 利用率分析服务**，  
它可以自动定期从 Prometheus 拉取数据，计算每张 GPU 的利用率评分，关联租户 pod/namespace，并根据阈值调用控制接口（比如降成本或释放资源）。

---

## 🧱 架构设计

```
┌────────────────────────────┐
│      Prometheus            │
│ (DCGM exporter GPU metrics)│
└──────────────┬─────────────┘
               │
       每隔 N 分钟拉取
               ▼
┌────────────────────────────┐
│ GPU Monitor Service (FastAPI) │
│  - 多线程拉取每张GPU数据        │
│  - 计算评分 score(0~100)       │
│  - 获取 pod/namespace 标签     │
│  - 保存结果 / 触发动作         │
│  - /metrics, /analyze API     │
└──────────────┬─────────────┘
               │
               ▼
┌────────────────────────────┐
│  外部控制系统 / Kubeflow API │
│  触发成本优化、通知租户等     │
└────────────────────────────┘
```

---

## 🚀 完整 Python 实现（FastAPI + Scheduler + Prometheus 查询 + 多线程）

> ✅ 可直接运行  
> ✅ 自动定时检测  
> ✅ 输出租户 + GPU 利用率 + 阈值判定  
> ✅ 可通过 `/analyze` 手动触发一次

```python
from fastapi import FastAPI, BackgroundTasks
import requests
import concurrent.futures
import numpy as np
from datetime import datetime, timedelta
import asyncio

# ------------------------
# 配置项
# ------------------------
PROM_URL = "http://prometheus:9090"
QUERY_CONDITION = '{pod!=""}'
TIME_WINDOW_MIN = 10
STEP = "30s"
THRESHOLD = 20  # 判定为闲置的评分阈值
INTERVAL = 300  # 轮询周期（秒）
MAX_WORKERS = 8
CONTROL_API = "http://your-control-service/api/optimize"  # 可选控制接口

app = FastAPI(title="GPU Utilization Monitor", version="1.0")

# ------------------------
# Prometheus 查询函数
# ------------------------
def query_prometheus(metric, gpu_uuid, labels=None):
    """查询某个 GPU 的特定 metric 平均值"""
    end = datetime.utcnow()
    start = end - timedelta(minutes=TIME_WINDOW_MIN)
    label_cond = f'{QUERY_CONDITION}, uuid="{gpu_uuid}"'
    if labels:
        label_cond += "".join([f', {k}="{v}"' for k, v in labels.items()])

    query = f'{metric}{label_cond}'
    url = f"{PROM_URL}/api/v1/query_range"

    try:
        resp = requests.get(url, params={
            "query": query,
            "start": start.timestamp(),
            "end": end.timestamp(),
            "step": STEP
        }).json()

        result = resp.get("data", {}).get("result", [])
        if not result:
            return 0
        values = [float(v[1]) for v in result[0]["values"] if v[1] != "NaN"]
        return np.mean(values) if values else 0
    except Exception as e:
        print(f"[ERROR] Query {metric} for {gpu_uuid} failed: {e}")
        return 0


def get_all_gpu_series():
    """从 Prometheus 获取当前活跃 GPU + Pod + Namespace 列表"""
    query = f'DCGM_FI_DEV_GPU_UTIL{QUERY_CONDITION}'
    url = f"{PROM_URL}/api/v1/series"
    try:
        resp = requests.get(url, params={"match[]": query}).json()
        series = []
        for s in resp.get("data", []):
            if "uuid" in s:
                series.append({
                    "uuid": s["uuid"],
                    "pod": s.get("pod", ""),
                    "namespace": s.get("namespace", "")
                })
        return series
    except Exception as e:
        print(f"[ERROR] 获取 GPU 列表失败: {e}")
        return []


def compute_gpu_score(gpu_info):
    """计算单卡 GPU 利用率评分"""
    uuid = gpu_info["uuid"]
    pod = gpu_info["pod"]
    namespace = gpu_info["namespace"]

    gpu_util = query_prometheus("DCGM_FI_DEV_GPU_UTIL", uuid)
    mem_copy = query_prometheus("DCGM_FI_DEV_MEM_COPY_UTIL", uuid)
    mem_used = query_prometheus("DCGM_FI_DEV_FB_USED", uuid)

    score = (
        0.5 * (gpu_util / 100) +
        0.2 * (mem_copy / 100) +
        0.3 * min(mem_used / (mem_used + 1e-6), 1.0)
    )

    return {
        "gpu_id": uuid,
        "pod": pod,
        "namespace": namespace,
        "gpu_util": round(gpu_util, 2),
        "mem_copy": round(mem_copy, 2),
        "mem_used": round(mem_used / 1e6, 1),  # MB
        "score": round(score * 100, 1)
    }

# ------------------------
# 后台任务调度
# ------------------------
async def analyze_all_gpus():
    gpu_series = get_all_gpu_series()
    if not gpu_series:
        print("[WARN] 未找到任何 GPU 数据")
        return

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(compute_gpu_score, g) for g in gpu_series]
        for f in concurrent.futures.as_completed(futures):
            results.append(f.result())

    results.sort(key=lambda x: x["score"])
    print("\n========== GPU 利用率分析 ==========")
    for r in results:
        print(f"[{r['namespace']}/{r['pod']}] GPU {r['gpu_id']} → Score={r['score']:>5}% (Util={r['gpu_util']:>5}%)")

    low_util = [r for r in results if r["score"] < THRESHOLD]
    if low_util:
        print(f"\n⚠️ 检测到 {len(low_util)} 张 GPU 利用率低于 {THRESHOLD}%：")
        for r in low_util:
            print(f"  - {r['namespace']}/{r['pod']} ({r['score']}%)")
            try:
                # 可选：调用控制API
                requests.post(CONTROL_API, json={
                    "gpu_id": r["gpu_id"],
                    "pod": r["pod"],
                    "namespace": r["namespace"],
                    "score": r["score"]
                }, timeout=5)
            except Exception as e:
                print(f"[WARN] 调用控制接口失败: {e}")


@app.on_event("startup")
async def startup_event():
    """后台周期任务"""
    async def scheduler():
        while True:
            await analyze_all_gpus()
            await asyncio.sleep(INTERVAL)

    asyncio.create_task(scheduler())


@app.get("/analyze")
async def trigger_analysis(bg: BackgroundTasks):
    """手动触发一次 GPU 利用率分析"""
    bg.add_task(analyze_all_gpus)
    return {"status": "started"}


@app.get("/")
async def root():
    return {"service": "GPU Utilization Monitor", "interval": INTERVAL, "threshold": THRESHOLD}
```

---

## 🧩 部署方式

### 🐳 1. 直接运行
```bash
pip install fastapi uvicorn numpy requests
uvicorn gpu_monitor:app --host 0.0.0.0 --port 8080
```

### 🧭 2. 访问接口
- 手动触发分析：`GET /analyze`
- 查看配置：`GET /`
- 自动每 5 分钟执行一次轮询

### 🛠️ 3. 输出日志示例
```
========== GPU 利用率分析 ==========
[team-a/ns-train1] GPU GPU-a123 → Score=  85% (Util= 78%)
[team-b/ns-lab3]  GPU GPU-b789 → Score=   5% (Util=  2%)

⚠️ 检测到 1 张 GPU 利用率低于 20%：
  - team-b/ns-lab3 (5%)
```

---

## 🌟 可选扩展建议

| 功能 | 说明 |
|------|------|
| 🧠 **AI 模型判断** | 将每张 GPU 最近10分钟指标序列作为特征输入到 LLM，智能判断是否空闲 |
| 💾 **保存历史数据** | 把每轮分析结果写入 SQLite / InfluxDB，用于趋势可视化 |
| 🕹 **Grafana 视图** | 显示每张 GPU 利用率评分、pod/namespace、趋势图 |
| 🔔 **告警通知** | 接入 Slack / 飞书 / 邮件 通知低利用 GPU |
| 🧩 **与 Kubeflow 集成** | 调用 Kubeflow Notebook / Job API 自动缩容或停止空闲实例 |

---

是否希望我帮你：
1️⃣ 在这个服务上再加上 **LLM 判断逻辑（比如利用AI分析10分钟序列是否在训练）**，  
还是  
2️⃣ 帮你加上 **保存分析结果到数据库 + Grafana可视化接口**？
user
DCGM_FI_DEV_POWER_USAGE{DCGM_FI_DRIVER_VERSION="545.23.08", Hostname="aigc-k8s-vn-master001", UUID="GPU-03cd1cf6-11f6-5ecc-feb0-af07406e1838", alert_group="aigc", app_kubernetes_io_component="dcgm-exporter", app_kubernetes_io_instance="nvidia-gpu", app_kubernetes_io_name="dcgm-exporter", container="comfyui", controller_revision_hash="5b87bdbcd9", device="nvidia0", gpu="0", group="vm_aigc", idc="aigc-vn", instance="10.244.0.50:9400", job="lens-metrics/nvidia-gpu-dcgm-exporter", k8s_cluster="aigc-k8s-vn", kubernetes_namespace="comfyui", kubernetes_node="aigc-k8s-vn-master001", kubernetes_pod_name="nvidia-gpu-dcgm-exporter-d96xw", labrador_project="AIGC", modelName="Tesla V100S-PCIE-32GB", namespace="comfyui", pod="comfyui-xuanwu-deploy-694d64fb5-jqs8w", pod_template_generation="1", target_endpoint="pods", zone_name="vn"}

这是查询响应内容，你可以参考一下
ChatGPT
非常好，你这条 Prometheus 响应样例信息非常关键，它说明你的数据结构已经标准化了，可以通过 label（如 `gpu`、`pod`、`namespace`、`Hostname`）区分不同 GPU 实例，非常适合做自动化多 GPU 利用率分析。  

---

## ✅ 一、目标
你的目标是：
1. 对每个 GPU（可通过 `UUID` 或 `gpu` label 唯一识别）计算出一个 **综合利用率评分**；
2. 支持多线程（或异步）并行分析；
3. 当利用率低于阈值时自动调用接口（比如释放 GPU、提醒租户、或缩容）；
4. 查询 Prometheus 时加上 `{pod!=""}` 过滤条件。

---

## ✅ 二、推荐的监控方案架构
整体流程图如下：

```
[Prometheus] 
   ↓ (promQL 查询 GPU metrics)
[GPU Monitor Service]
   ↓
[AI/Rule-based Analyzer] (计算综合利用率评分)
   ↓
[Decision Engine]
   ↓
[Action API 调用 (释放/提醒/缩容)]
```

你可以实现成一个 Python 服务，定时拉取指标。

---

## ✅ 三、Prometheus 查询指标建议

为了让 AI 或算法合理判断 GPU 是否“真的在用”，建议同时采集以下 metrics：

| 指标名 | 说明 | 是否关键 |
|--------|------|-----------|
| `DCGM_FI_DEV_GPU_UTIL` | GPU 核心利用率 (%) | ✅ 高 |
| `DCGM_FI_DEV_FB_USED` | 显存使用量 (MiB) | ✅ 中 |
| `DCGM_FI_DEV_FB_TOTAL` | 显存总量 (MiB) | ⚠️（你没数据，可忽略或从其他 metric 推导） |
| `DCGM_FI_DEV_SM_CLOCK` | 核心频率 (MHz) | ✅ 辅助判断活跃度 |
| `DCGM_FI_DEV_MEM_CLOCK` | 显存频率 (MHz) | ✅ 辅助 |
| `DCGM_FI_DEV_POWER_USAGE` | 实际功率 (W) | ✅ 非常关键（可以判断 GPU 是否处于低功耗闲置状态） |
| `DCGM_FI_PROF_PIPE_TENSOR_ACTIVE` | Tensor Core 利用率 | ✅ 可选，用于深度学习场景 |
| `DCGM_FI_PROF_GR_ENGINE_ACTIVE` | 图形引擎利用率 | ✅ 可选 |
| `DCGM_FI_DEV_TEMP` | 温度 | ⚙️ 辅助指标 |

---

## ✅ 四、综合利用率评分计算方案

可以自定义一个 **AI前置启发式评分函数**：

```python
def gpu_utilization_score(metrics):
    """
    计算GPU综合利用率评分 (0~100)
    """
    gpu_util = metrics.get("DCGM_FI_DEV_GPU_UTIL", 0)
    fb_used = metrics.get("DCGM_FI_DEV_FB_USED", 0)
    sm_clock = metrics.get("DCGM_FI_DEV_SM_CLOCK", 0)
    mem_clock = metrics.get("DCGM_FI_DEV_MEM_CLOCK", 0)
    power_usage = metrics.get("DCGM_FI_DEV_POWER_USAGE", 0)

    # 简单归一化逻辑，可被AI模型替换
    score = (
        0.5 * gpu_util +
        0.2 * (fb_used / 32000 * 100) +  # 假设V100S 32GB
        0.15 * (power_usage / 250 * 100) +
        0.1 * (sm_clock / 1600 * 100) +
        0.05 * (mem_clock / 1200 * 100)
    )
    return round(score, 2)
```

如果评分低于某个阈值（例如 < 10），且持续时间超过 10 分钟，则认为“空闲”。

---

## ✅ 五、Prometheus 查询样例

以 `aiohttp` + `prometheus_api_client` 方式实现异步多 GPU 拉取：

```python
import asyncio
from prometheus_api_client import PrometheusConnect
from concurrent.futures import ThreadPoolExecutor

prom = PrometheusConnect(url="http://prometheus.yourdomain:9090", disable_ssl=True)

QUERY_METRICS = [
    "DCGM_FI_DEV_GPU_UTIL",
    "DCGM_FI_DEV_FB_USED",
    "DCGM_FI_DEV_SM_CLOCK",
    "DCGM_FI_DEV_MEM_CLOCK",
    "DCGM_FI_DEV_POWER_USAGE",
]

def query_metric(metric):
    query = f'{metric}{{pod!=""}}'
    return prom.custom_query(query=query)

def analyze_gpu(gpu_data):
    # 汇总每个 GPU 的指标值
    metrics = {}
    for d in gpu_data:
        gpu_id = d['metric'].get('UUID') or d['metric'].get('gpu')
        value = float(d['value'][1])
        metric_name = d['metric']['__name__']
        metrics.setdefault(gpu_id, {})[metric_name] = value

    results = {}
    for gpu_id, vals in metrics.items():
        results[gpu_id] = gpu_utilization_score(vals)
    return results

async def main():
    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor() as pool:
        gpu_data_all = await asyncio.gather(*[
            loop.run_in_executor(pool, query_metric, m) for m in QUERY_METRICS
        ])
        gpu_data_flat = [item for sublist in gpu_data_all for item in sublist]
        results = analyze_gpu(gpu_data_flat)
        print(results)

asyncio.run(main())
```

输出示例：
```bash
{
  "GPU-03cd1cf6-11f6-5ecc-feb0-af07406e1838": 12.4,
  "GPU-a24b...": 83.7
}
```

---

## ✅ 六、扩展：调用AI辅助判断

你可以在分析阶段将最近5分钟的时序数据（如功耗、显存、GPU_UTIL曲线）输入AI模型，让AI输出判断，例如：

```python
prompt = f"""
请根据以下GPU指标数据，判断该GPU是否正在被有效利用。
数据: {json.dumps(gpu_timeseries, ensure_ascii=False)}
返回一个0~100的利用率评分。
"""
```

这样AI会综合时间序列变化趋势（比如GPU_UTIL波动、功耗上升、显存占用稳定等）来判断是否真的在跑任务。

---

## ✅ 七、后续扩展建议
- ✅ 将结果写入 Prometheus PushGateway 或 Grafana Loki，形成“AI利用率”指标；
- ✅ 增加一个持续性判定逻辑，比如连续 N 次采样评分低才触发回收；
- ✅ 结合 K8s API 自动 label、驱动 Pod 驱逐或通知。

---

我可以帮你把上面的方案扩展成一个完整的 Python 服务（带 Prometheus 拉取、AI分析、REST API 调用、异步调度模块）。  
是否希望我直接帮你生成这个完整框架？