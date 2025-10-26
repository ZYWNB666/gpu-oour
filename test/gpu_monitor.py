"""
GPU 利用率监控分析服务

功能:
- 从 Prometheus 拉取 GPU metrics
- 多线程并发计算每个 GPU 的综合利用率评分
- 关联租户信息 (pod/namespace)
- 低利用率时调用控制接口
- 支持定时调度和手动触发
"""

from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
import requests
import concurrent.futures
import numpy as np
from datetime import datetime, timedelta
import asyncio
import logging
from typing import List, Dict, Optional
import json

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ========================
# 配置项
# ========================
class Config:
    # Prometheus 配置
    PROM_URL = "http://prometheus:9090"
    QUERY_CONDITION = '{pod!=""}'  # 只查询已分配的GPU
    TIME_WINDOW_MIN = 10  # 时间窗口（分钟）
    STEP = "30s"  # 查询步长
    
    # 评分配置
    THRESHOLD = 20  # 低利用率阈值（分数低于此值视为闲置）
    GPU_UTIL_WEIGHT = 0.5  # GPU核心使用率权重
    MEM_COPY_WEIGHT = 0.2  # 内存拷贝使用率权重
    MEM_USED_WEIGHT = 0.2  # 显存使用权重
    POWER_WEIGHT = 0.1  # 功率权重（可选）
    
    # 调度配置
    INTERVAL = 300  # 轮询周期（秒）
    MAX_WORKERS = 8  # 最大并发线程数
    
    # 控制接口配置（可选）
    CONTROL_API = "http://your-control-service/api/optimize"
    CONTROL_API_ENABLED = False  # 是否启用控制接口调用
    
    # GPU模型配置（用于功率和显存归一化）
    DEFAULT_GPU_MEMORY_MB = 32000  # V100S 32GB
    DEFAULT_GPU_POWER_W = 250  # V100S 默认功率

config = Config()

# ========================
# 数据模型
# ========================
class GPUInfo(BaseModel):
    """GPU信息"""
    uuid: str
    pod: str
    namespace: str
    hostname: str = ""
    gpu_index: str = ""
    model_name: str = ""

class GPUMetrics(BaseModel):
    """GPU指标"""
    gpu_id: str
    pod: str
    namespace: str
    hostname: str
    model_name: str
    gpu_util: float
    mem_copy: float
    mem_used_mb: float
    power_usage: float
    sm_clock: float
    score: float
    status: str  # "idle", "low", "normal", "high"

# ========================
# Prometheus 查询函数
# ========================
def query_prometheus(metric: str, gpu_uuid: str, additional_labels: Optional[Dict] = None) -> float:
    """
    查询某个 GPU 的特定 metric 平均值
    
    Args:
        metric: 指标名称
        gpu_uuid: GPU UUID
        additional_labels: 额外的标签过滤条件
    
    Returns:
        float: 指标平均值
    """
    end = datetime.utcnow()
    start = end - timedelta(minutes=config.TIME_WINDOW_MIN)
    
    # 构建查询条件
    label_cond = f'{config.QUERY_CONDITION}, UUID="{gpu_uuid}"'
    if additional_labels:
        for k, v in additional_labels.items():
            label_cond += f', {k}="{v}"'
    
    query = f'{metric}{label_cond}'
    url = f"{config.PROM_URL}/api/v1/query_range"
    
    try:
        resp = requests.get(url, params={
            "query": query,
            "start": start.timestamp(),
            "end": end.timestamp(),
            "step": config.STEP
        }, timeout=10).json()
        
        result = resp.get("data", {}).get("result", [])
        if not result:
            return 0.0
        
        # 提取值并过滤 NaN
        values = []
        for v in result[0].get("values", []):
            try:
                val = float(v[1])
                if not np.isnan(val):
                    values.append(val)
            except (ValueError, TypeError):
                continue
        
        return float(np.mean(values)) if values else 0.0
    
    except Exception as e:
        logger.error(f"Query {metric} for {gpu_uuid} failed: {e}")
        return 0.0


def get_all_gpu_series() -> List[GPUInfo]:
    """
    从 Prometheus 获取当前活跃 GPU 列表及其标签信息
    
    Returns:
        List[GPUInfo]: GPU信息列表
    """
    query = f'DCGM_FI_DEV_GPU_UTIL{config.QUERY_CONDITION}'
    url = f"{config.PROM_URL}/api/v1/series"
    
    try:
        resp = requests.get(url, params={"match[]": query}, timeout=10).json()
        
        gpu_list = []
        for s in resp.get("data", []):
            if "UUID" in s:
                gpu_info = GPUInfo(
                    uuid=s.get("UUID", ""),
                    pod=s.get("pod", ""),
                    namespace=s.get("namespace", ""),
                    hostname=s.get("Hostname", s.get("kubernetes_node", "")),
                    gpu_index=s.get("gpu", ""),
                    model_name=s.get("modelName", "")
                )
                gpu_list.append(gpu_info)
        
        logger.info(f"Found {len(gpu_list)} GPUs")
        return gpu_list
    
    except Exception as e:
        logger.error(f"Failed to get GPU list: {e}")
        return []


def compute_gpu_score(gpu_info: GPUInfo) -> GPUMetrics:
    """
    计算单个 GPU 的综合利用率评分
    
    Args:
        gpu_info: GPU信息
    
    Returns:
        GPUMetrics: GPU指标和评分
    """
    uuid = gpu_info.uuid
    
    # 查询各项指标
    gpu_util = query_prometheus("DCGM_FI_DEV_GPU_UTIL", uuid)
    mem_copy = query_prometheus("DCGM_FI_DEV_MEM_COPY_UTIL", uuid)
    mem_used = query_prometheus("DCGM_FI_DEV_FB_USED", uuid)  # bytes
    power_usage = query_prometheus("DCGM_FI_DEV_POWER_USAGE", uuid)
    sm_clock = query_prometheus("DCGM_FI_DEV_SM_CLOCK", uuid)
    
    # 转换显存为MB
    mem_used_mb = mem_used / (1024 * 1024) if mem_used > 0 else 0
    
    # 计算综合评分（0-100）
    # 由于 DCGM_FI_DEV_FB_TOTAL 和 DCGM_FI_DEV_POWER_LIMIT 没数据，使用简化公式
    score = (
        config.GPU_UTIL_WEIGHT * (gpu_util / 100) +
        config.MEM_COPY_WEIGHT * (mem_copy / 100) +
        config.MEM_USED_WEIGHT * min(mem_used_mb / config.DEFAULT_GPU_MEMORY_MB, 1.0) +
        config.POWER_WEIGHT * min(power_usage / config.DEFAULT_GPU_POWER_W, 1.0)
    )
    
    score_percent = round(score * 100, 1)
    
    # 判断状态
    if score_percent < 10:
        status = "idle"
    elif score_percent < config.THRESHOLD:
        status = "low"
    elif score_percent < 70:
        status = "normal"
    else:
        status = "high"
    
    return GPUMetrics(
        gpu_id=uuid,
        pod=gpu_info.pod,
        namespace=gpu_info.namespace,
        hostname=gpu_info.hostname,
        model_name=gpu_info.model_name,
        gpu_util=round(gpu_util, 2),
        mem_copy=round(mem_copy, 2),
        mem_used_mb=round(mem_used_mb, 1),
        power_usage=round(power_usage, 1),
        sm_clock=round(sm_clock, 0),
        score=score_percent,
        status=status
    )


def call_control_api(gpu_metrics: GPUMetrics):
    """
    调用外部控制接口
    
    Args:
        gpu_metrics: GPU指标数据
    """
    if not config.CONTROL_API_ENABLED:
        return
    
    try:
        payload = {
            "gpu_id": gpu_metrics.gpu_id,
            "pod": gpu_metrics.pod,
            "namespace": gpu_metrics.namespace,
            "hostname": gpu_metrics.hostname,
            "score": gpu_metrics.score,
            "status": gpu_metrics.status,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        resp = requests.post(
            config.CONTROL_API,
            json=payload,
            timeout=5
        )
        
        if resp.status_code == 200:
            logger.info(f"Control API called successfully for {gpu_metrics.gpu_id}")
        else:
            logger.warning(f"Control API returned {resp.status_code} for {gpu_metrics.gpu_id}")
    
    except Exception as e:
        logger.error(f"Failed to call control API: {e}")


# ========================
# 核心分析逻辑
# ========================
async def analyze_all_gpus() -> List[GPUMetrics]:
    """
    分析所有 GPU 的利用率
    
    Returns:
        List[GPUMetrics]: GPU指标列表
    """
    logger.info("=" * 60)
    logger.info("Starting GPU utilization analysis")
    
    # 获取所有GPU
    gpu_series = get_all_gpu_series()
    if not gpu_series:
        logger.warning("No GPU data found")
        return []
    
    # 多线程并发计算
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
        futures = [executor.submit(compute_gpu_score, g) for g in gpu_series]
        
        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to compute GPU score: {e}")
    
    # 按评分排序
    results.sort(key=lambda x: x.score)
    
    # 输出分析结果
    logger.info(f"\n{'='*60}")
    logger.info("GPU Utilization Analysis Results")
    logger.info(f"{'='*60}")
    logger.info(f"{'Namespace/Pod':<40} {'GPU':<40} {'Score':>8} {'Util':>8} {'Mem(MB)':>10} {'Status':<8}")
    logger.info(f"{'-'*60}")
    
    for r in results:
        pod_info = f"{r.namespace}/{r.pod}"
        logger.info(
            f"{pod_info:<40} {r.gpu_id[:40]:<40} "
            f"{r.score:>7.1f}% {r.gpu_util:>7.1f}% "
            f"{r.mem_used_mb:>9.1f} {r.status:<8}"
        )
    
    # 统计低利用率GPU
    low_util = [r for r in results if r.score < config.THRESHOLD]
    if low_util:
        logger.warning(f"\n⚠️  Found {len(low_util)} GPU(s) with utilization below {config.THRESHOLD}%:")
        for r in low_util:
            logger.warning(f"  - {r.namespace}/{r.pod} ({r.score}%) - {r.gpu_id}")
            # 调用控制接口
            call_control_api(r)
    else:
        logger.info(f"\n✅ All GPUs have utilization above {config.THRESHOLD}%")
    
    logger.info(f"{'='*60}\n")
    
    return results


# ========================
# FastAPI 应用
# ========================
app = FastAPI(
    title="GPU Utilization Monitor",
    description="GPU利用率监控分析服务",
    version="1.0.0"
)

# 全局变量存储最近一次分析结果
latest_results: List[GPUMetrics] = []


@app.on_event("startup")
async def startup_event():
    """启动时初始化后台任务"""
    logger.info("GPU Monitor Service starting...")
    
    async def scheduler():
        """后台定时任务"""
        while True:
            try:
                global latest_results
                latest_results = await analyze_all_gpus()
            except Exception as e:
                logger.error(f"Error in scheduled analysis: {e}")
            
            await asyncio.sleep(config.INTERVAL)
    
    # 创建后台任务
    asyncio.create_task(scheduler())
    logger.info(f"Scheduler started with interval {config.INTERVAL}s")


@app.get("/")
async def root():
    """服务信息"""
    return {
        "service": "GPU Utilization Monitor",
        "version": "1.0.0",
        "config": {
            "prometheus_url": config.PROM_URL,
            "threshold": config.THRESHOLD,
            "interval": config.INTERVAL,
            "time_window_min": config.TIME_WINDOW_MIN
        }
    }


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "healthy"}


@app.get("/analyze")
async def trigger_analysis(bg: BackgroundTasks):
    """手动触发一次分析"""
    bg.add_task(analyze_all_gpus)
    return {
        "status": "triggered",
        "message": "GPU analysis started in background"
    }


@app.get("/results", response_model=List[GPUMetrics])
async def get_results():
    """获取最近一次分析结果"""
    return latest_results


@app.get("/results/low")
async def get_low_utilization():
    """获取低利用率GPU"""
    low_util = [r for r in latest_results if r.score < config.THRESHOLD]
    return {
        "count": len(low_util),
        "threshold": config.THRESHOLD,
        "gpus": low_util
    }


@app.get("/results/stats")
async def get_statistics():
    """获取统计信息"""
    if not latest_results:
        return {"message": "No data available"}
    
    scores = [r.score for r in latest_results]
    
    return {
        "total_gpus": len(latest_results),
        "avg_score": round(np.mean(scores), 1),
        "min_score": round(min(scores), 1),
        "max_score": round(max(scores), 1),
        "low_utilization_count": len([r for r in latest_results if r.score < config.THRESHOLD]),
        "idle_count": len([r for r in latest_results if r.status == "idle"]),
        "by_status": {
            "idle": len([r for r in latest_results if r.status == "idle"]),
            "low": len([r for r in latest_results if r.status == "low"]),
            "normal": len([r for r in latest_results if r.status == "normal"]),
            "high": len([r for r in latest_results if r.status == "high"])
        }
    }


@app.post("/config")
async def update_config(
    threshold: Optional[int] = None,
    interval: Optional[int] = None
):
    """
    更新配置（需要重启服务才能生效某些配置）
    """
    updates = {}
    if threshold is not None:
        config.THRESHOLD = threshold
        updates["threshold"] = threshold
    if interval is not None:
        config.INTERVAL = interval
        updates["interval"] = interval
    
    return {
        "status": "updated",
        "updates": updates,
        "note": "Some changes may require service restart"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)

