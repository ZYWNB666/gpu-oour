# GPU 利用率监控系统 - 使用示例

## 场景一：查看当前所有 GPU 状态

```powershell
# 获取最新分析结果
curl http://localhost:8080/results | python -m json.tool
```

**响应示例：**
```json
[
  {
    "gpu_id": "GPU-03cd1cf6-11f6-5ecc-feb0-af07406e1838",
    "pod": "training-job-xyz",
    "namespace": "ml-team",
    "hostname": "gpu-node-01",
    "model_name": "Tesla V100S-PCIE-32GB",
    "gpu_util": 85.3,
    "mem_copy": 62.1,
    "mem_used_mb": 25600.0,
    "power_usage": 220.5,
    "sm_clock": 1530.0,
    "score": 78.4,
    "status": "high"
  },
  {
    "gpu_id": "GPU-abc123...",
    "pod": "idle-notebook",
    "namespace": "dev-team",
    "score": 5.2,
    "status": "idle"
  }
]
```

---

## 场景二：识别低利用率 GPU

```powershell
# 查看低于阈值的 GPU
curl http://localhost:8080/results/low
```

**响应示例：**
```json
{
  "count": 3,
  "threshold": 20,
  "gpus": [
    {
      "gpu_id": "GPU-abc123...",
      "pod": "idle-notebook-1",
      "namespace": "dev-team",
      "hostname": "gpu-node-02",
      "score": 5.2,
      "status": "idle"
    },
    {
      "gpu_id": "GPU-def456...",
      "pod": "suspended-job",
      "namespace": "test",
      "score": 12.8,
      "status": "low"
    }
  ]
}
```

**操作建议：**
1. 联系 `dev-team` 检查 `idle-notebook-1` 是否还需要 GPU
2. 考虑回收或重新分配闲置资源

---

## 场景三：定期监控和自动化

### 1. 定时检查（Windows 任务计划程序）

创建 PowerShell 脚本 `check_gpu.ps1`：
```powershell
# 获取低利用率 GPU
$response = Invoke-RestMethod -Uri "http://localhost:8080/results/low"

if ($response.count -gt 0) {
    Write-Host "⚠️ 发现 $($response.count) 个低利用率 GPU"
    
    foreach ($gpu in $response.gpus) {
        $msg = "GPU: $($gpu.gpu_id), Pod: $($gpu.namespace)/$($gpu.pod), Score: $($gpu.score)%"
        Write-Host $msg
        
        # 发送通知（飞书/邮件等）
        # Send-Notification -Message $msg
    }
}
```

设置任务计划：
```powershell
# 每小时执行一次
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Hours 1)
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-File C:\scripts\check_gpu.ps1"
Register-ScheduledTask -TaskName "GPU-Monitor-Check" -Trigger $trigger -Action $action
```

### 2. 与 Kubeflow 集成

当检测到低利用率时自动停止 Notebook：

```python
import requests
from kubernetes import client, config

# 获取低利用率 GPU
resp = requests.get("http://gpu-monitor/results/low").json()

config.load_kube_config()
v1 = client.CoreV1Api()

for gpu in resp['gpus']:
    namespace = gpu['namespace']
    pod_name = gpu['pod']
    score = gpu['score']
    
    if score < 10:  # 完全闲置
        print(f"Deleting idle pod: {namespace}/{pod_name}")
        v1.delete_namespaced_pod(pod_name, namespace)
```

---

## 场景四：Grafana 可视化

### Prometheus 数据源配置

在 Grafana 中添加 Prometheus 数据源，然后创建自定义指标：

#### 方法1: 通过 PushGateway 推送评分

```python
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway

registry = CollectorRegistry()
gpu_score_gauge = Gauge(
    'gpu_utilization_score',
    'GPU Utilization Score',
    ['gpu_id', 'pod', 'namespace'],
    registry=registry
)

# 推送评分数据
for result in results:
    gpu_score_gauge.labels(
        gpu_id=result['gpu_id'],
        pod=result['pod'],
        namespace=result['namespace']
    ).set(result['score'])

push_to_gateway('pushgateway:9091', job='gpu_monitor', registry=registry)
```

#### 方法2: Grafana 直接查询服务

配置 JSON API 数据源：
- URL: `http://gpu-monitor/results`
- Query: `$[*]`

### Dashboard 配置示例

```json
{
  "panels": [
    {
      "title": "GPU 利用率评分分布",
      "type": "histogram",
      "targets": [
        {
          "expr": "histogram_quantile(0.95, gpu_utilization_score)"
        }
      ]
    },
    {
      "title": "低利用率 GPU 告警",
      "type": "table",
      "targets": [
        {
          "expr": "gpu_utilization_score < 20"
        }
      ]
    }
  ]
}
```

---

## 场景五：成本优化决策

### 按团队统计 GPU 使用情况

```python
import requests
from collections import defaultdict

# 获取所有 GPU 数据
resp = requests.get("http://localhost:8080/results").json()

# 按 namespace 统计
team_stats = defaultdict(lambda: {
    'total': 0, 
    'avg_score': 0, 
    'low_util_count': 0
})

for gpu in resp:
    ns = gpu['namespace']
    team_stats[ns]['total'] += 1
    team_stats[ns]['avg_score'] += gpu['score']
    if gpu['score'] < 20:
        team_stats[ns]['low_util_count'] += 1

# 计算平均值
for ns, stats in team_stats.items():
    stats['avg_score'] = stats['avg_score'] / stats['total']

# 输出报告
print("\n=== GPU 使用情况报告 ===")
for ns, stats in sorted(team_stats.items()):
    print(f"\nTeam: {ns}")
    print(f"  Total GPUs: {stats['total']}")
    print(f"  Avg Score: {stats['avg_score']:.1f}%")
    print(f"  Low Util Count: {stats['low_util_count']}")
    print(f"  Efficiency: {100 - (stats['low_util_count']/stats['total']*100):.1f}%")
```

**输出示例：**
```
=== GPU 使用情况报告 ===

Team: ml-training
  Total GPUs: 8
  Avg Score: 72.3%
  Low Util Count: 0
  Efficiency: 100.0%

Team: dev-team
  Total GPUs: 4
  Avg Score: 15.2%
  Low Util Count: 3
  Efficiency: 25.0%

建议: dev-team 团队 GPU 利用率过低，建议回收部分资源
```

---

## 场景六：AI 辅助判断（进阶）

将指标数据传递给 AI 模型进行智能分析：

```python
import requests
import json

def ai_analyze_gpu(gpu_id):
    """使用 AI 分析 GPU 利用率"""
    
    # 获取最近10分钟的时序数据
    prom_url = "http://prometheus:9090/api/v1/query_range"
    end = datetime.utcnow()
    start = end - timedelta(minutes=10)
    
    metrics = ['DCGM_FI_DEV_GPU_UTIL', 'DCGM_FI_DEV_FB_USED', 'DCGM_FI_DEV_POWER_USAGE']
    series_data = {}
    
    for metric in metrics:
        query = f'{metric}{{UUID="{gpu_id}"}}'
        resp = requests.get(prom_url, params={
            "query": query,
            "start": start.timestamp(),
            "end": end.timestamp(),
            "step": "30s"
        }).json()
        series_data[metric] = resp['data']['result'][0]['values']
    
    # 构建 AI Prompt
    prompt = f"""
    请分析以下 GPU 在最近10分钟的使用情况，判断是否在进行有效计算：
    
    1. GPU 利用率序列: {series_data['DCGM_FI_DEV_GPU_UTIL']}
    2. 显存使用序列: {series_data['DCGM_FI_DEV_FB_USED']}
    3. 功率使用序列: {series_data['DCGM_FI_DEV_POWER_USAGE']}
    
    请输出 JSON 格式：
    {{
        "status": "active|idle|suspicious",
        "confidence": 0.0-1.0,
        "reason": "判断理由",
        "recommendation": "操作建议"
    }}
    """
    
    # 调用 AI API（OpenAI/Claude/本地模型）
    ai_response = call_llm_api(prompt)
    return ai_response

# 使用示例
result = ai_analyze_gpu("GPU-03cd1cf6-11f6-5ecc-feb0-af07406e1838")
print(f"AI 判断: {result['status']}")
print(f"置信度: {result['confidence']}")
print(f"理由: {result['reason']}")
print(f"建议: {result['recommendation']}")
```

---

## 场景七：飞书通知集成

```python
import requests

def send_feishu_notification(low_util_gpus):
    """发送飞书通知"""
    
    webhook_url = "https://open.feishu.cn/open-apis/bot/v2/hook/YOUR_WEBHOOK"
    
    # 构建消息内容
    content = "⚠️ **GPU 低利用率告警**\n\n"
    for gpu in low_util_gpus:
        content += f"- **{gpu['namespace']}/{gpu['pod']}**\n"
        content += f"  - GPU: {gpu['gpu_id'][:20]}...\n"
        content += f"  - 评分: {gpu['score']}%\n"
        content += f"  - 节点: {gpu['hostname']}\n\n"
    
    content += f"阈值: 20%\n"
    content += f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    # 发送消息
    payload = {
        "msg_type": "text",
        "content": {"text": content}
    }
    
    requests.post(webhook_url, json=payload)

# 定期检查并通知
resp = requests.get("http://localhost:8080/results/low").json()
if resp['count'] > 0:
    send_feishu_notification(resp['gpus'])
```

---

## 最佳实践建议

1. **设置合理阈值**：根据实际业务调整 `THRESHOLD`，避免误报
2. **定期巡检**：每小时检查一次，及时发现问题
3. **分级处理**：
   - `score < 10`：立即回收
   - `10 < score < 20`：发送通知，观察1小时
   - `score > 20`：正常使用
4. **记录历史**：保存分析结果，用于趋势分析
5. **团队责任制**：按 namespace 划分责任团队

