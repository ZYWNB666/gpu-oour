"""
GPU 利用率监控分析服务 - 主应用

功能:
- 从 Prometheus 拉取 GPU metrics
- 多线程并发计算综合利用率评分
- AI 智能分析（可选）
- 导出 Prometheus metrics
- RESTful API 接口
- 自动定时调度
"""

from fastapi import FastAPI, BackgroundTasks, Response
from fastapi.responses import PlainTextResponse
import logging
import sys
import io
from typing import List
from datetime import datetime

from app.config import config
from app.models import GPUMetricsWithAI, AnalysisStats
from app.scheduler import scheduler
from app.gpu_analyzer import gpu_analyzer
from app.metrics_exporter import metrics_exporter
from app.prometheus_client import PrometheusClient
import numpy as np

# 配置日志（支持中文输出）
def setup_logging():
    """配置日志系统，确保中文正常显示"""
    # 强制设置 UTF-8 编码（适用于所有平台）
    try:
        # 重新包装标准输出流，强制使用 UTF-8 编码
        if hasattr(sys.stdout, 'buffer'):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
        if hasattr(sys.stderr, 'buffer'):
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    except (AttributeError, ValueError) as e:
        # 某些环境可能不支持，记录但不中断
        print(f"Warning: Failed to set UTF-8 encoding: {e}")
    
    # 创建日志处理器，使用 UTF-8 编码的流
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, config.LOG_LEVEL))
    
    # 创建格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    
    # 配置根日志
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, config.LOG_LEVEL))
    root_logger.handlers.clear()  # 清除已有的处理器
    root_logger.addHandler(handler)
    
    # 测试中文输出
    test_logger = logging.getLogger("encoding_test")
    test_logger.info("✓ 日志系统初始化完成 - 中文支持正常")

setup_logging()
logger = logging.getLogger(__name__)

# 创建 FastAPI 应用
app = FastAPI(
    title="GPU Utilization Monitor",
    description="GPU利用率监控分析服务 - 支持AI智能分析和Prometheus metrics导出",
    version="1.0.0"
)


@app.on_event("startup")
async def startup_event():
    """启动事件"""
    logger.info("=" * 60)
    logger.info("GPU Monitor Service Starting...")
    logger.info("=" * 60)
    
    # 验证配置
    try:
        config.validate()
        logger.info("Configuration validated")
    except Exception as e:
        logger.error(f"Configuration error: {e}")
        raise
    
    # 显示配置
    logger.info(f"Prometheus URL: {config.PROM_URL}")
    logger.info(f"Threshold: {config.THRESHOLD}%")
    logger.info(f"Interval: {config.INTERVAL}s")
    logger.info(f"AI Enabled: {config.AI_ENABLED}")
    logger.info(f"Control API Enabled: {config.CONTROL_API_ENABLED}")
    
    # 启动调度器
    import asyncio
    asyncio.create_task(scheduler.start())
    
    logger.info("=" * 60)


@app.on_event("shutdown")
async def shutdown_event():
    """关闭事件"""
    logger.info("Shutting down GPU Monitor Service...")
    scheduler.stop()


@app.get("/")
async def root():
    """服务信息"""
    return {
        "service": "GPU Utilization Monitor",
        "version": "1.0.0",
        "features": {
            "ai_analysis": config.AI_ENABLED,
            "prometheus_metrics": True,
            "control_api": config.CONTROL_API_ENABLED
        },
        "config": {
            "prometheus_url": config.PROM_URL,
            "threshold": config.THRESHOLD,
            "interval": config.INTERVAL,
            "time_window_min": config.TIME_WINDOW_MIN,
            "max_workers": config.MAX_WORKERS
        },
        "endpoints": {
            "analyze": "/analyze - 手动触发分析",
            "results": "/results - 获取分析结果",
            "results_low": "/results/low - 获取低利用率GPU",
            "stats": "/results/stats - 获取统计信息",
            "metrics": "/metrics - Prometheus metrics",
            "health": "/health - 健康检查"
        }
    }


@app.get("/health")
async def health():
    """健康检查"""
    last_analysis = scheduler.last_analysis_time
    
    # 检查 Prometheus 连接
    prom_client = PrometheusClient()
    prom_healthy = prom_client.health_check()
    
    # 检查最近一次分析是否超时
    analysis_timeout = False
    if last_analysis:
        from datetime import datetime, timedelta
        if datetime.utcnow() - last_analysis > timedelta(seconds=config.INTERVAL * 3):
            analysis_timeout = True
    
    # 确定总体状态
    overall_status = "healthy"
    if not prom_healthy:
        overall_status = "degraded"
    if analysis_timeout:
        overall_status = "warning"
    
    return {
        "status": overall_status,
        "prometheus_connected": prom_healthy,
        "last_analysis": last_analysis.isoformat() if last_analysis else None,
        "analysis_timeout": analysis_timeout,
        "ai_enabled": config.AI_ENABLED,
        "interval": config.INTERVAL
    }


@app.get("/analyze")
async def trigger_analysis(bg: BackgroundTasks, use_ai: bool = None):
    """
    手动触发一次分析
    
    Args:
        use_ai: 是否使用AI分析（None表示使用配置）
    """
    bg.add_task(scheduler.run_analysis)
    return {
        "status": "triggered",
        "message": "GPU analysis started in background",
        "use_ai": use_ai if use_ai is not None else config.AI_ENABLED
    }


@app.get("/results", response_model=List[GPUMetricsWithAI])
async def get_results():
    """获取最近一次分析结果"""
    return scheduler.get_latest_results()


@app.get("/results/low")
async def get_low_utilization():
    """获取低利用率GPU"""
    results = scheduler.get_latest_results()
    low_util = [r for r in results if r.score < config.THRESHOLD]
    
    return {
        "count": len(low_util),
        "threshold": config.THRESHOLD,
        "timestamp": datetime.utcnow().isoformat(),
        "gpus": low_util
    }


@app.get("/results/stats", response_model=AnalysisStats)
async def get_statistics():
    """获取统计信息"""
    results = scheduler.get_latest_results()
    
    if not results:
        return {
            "total_gpus": 0,
            "avg_score": 0,
            "min_score": 0,
            "max_score": 0,
            "low_utilization_count": 0,
            "idle_count": 0,
            "by_status": {},
            "by_namespace": {}
        }
    
    scores = [r.score for r in results]
    
    # 按状态统计
    from collections import defaultdict
    by_status = defaultdict(int)
    for r in results:
        by_status[r.status.value] += 1
    
    # 按命名空间统计
    by_namespace = defaultdict(lambda: {
        'count': 0,
        'avg_score': 0,
        'low_util_count': 0
    })
    
    for r in results:
        ns = r.namespace
        by_namespace[ns]['count'] += 1
        by_namespace[ns]['avg_score'] += r.score
        if r.score < config.THRESHOLD:
            by_namespace[ns]['low_util_count'] += 1
    
    # 计算平均值
    for ns, stats in by_namespace.items():
        stats['avg_score'] = round(stats['avg_score'] / stats['count'], 1)
    
    return AnalysisStats(
        total_gpus=len(results),
        avg_score=round(np.mean(scores), 1),
        min_score=round(min(scores), 1),
        max_score=round(max(scores), 1),
        low_utilization_count=len([r for r in results if r.score < config.THRESHOLD]),
        idle_count=len([r for r in results if r.score < config.IDLE_THRESHOLD]),
        by_status=dict(by_status),
        by_namespace=dict(by_namespace)
    )


@app.get("/metrics")
async def get_metrics():
    """
    获取 Prometheus metrics
    
    返回所有 GPU 的监控指标，可被 Prometheus 抓取
    """
    metrics_data = metrics_exporter.get_metrics()
    return Response(
        content=metrics_data,
        media_type=metrics_exporter.get_content_type()
    )


@app.get("/config")
async def get_config():
    """获取当前配置"""
    return {
        "prometheus": {
            "url": config.PROM_URL,
            "query_condition": config.QUERY_CONDITION,
            "time_window_min": config.TIME_WINDOW_MIN,
            "step": config.STEP
        },
        "scoring": {
            "gpu_util_weight": config.GPU_UTIL_WEIGHT,
            "mem_copy_weight": config.MEM_COPY_WEIGHT,
            "mem_used_weight": config.MEM_USED_WEIGHT,
            "power_weight": config.POWER_WEIGHT
        },
        "thresholds": {
            "low_utilization": config.THRESHOLD,
            "idle": config.IDLE_THRESHOLD
        },
        "scheduler": {
            "interval": config.INTERVAL,
            "max_workers": config.MAX_WORKERS
        },
        "ai": {
            "enabled": config.AI_ENABLED,
            "model": config.AI_MODEL if config.AI_ENABLED else None
        },
        "control": {
            "enabled": config.CONTROL_API_ENABLED,
            "api_url": config.CONTROL_API if config.CONTROL_API_ENABLED else None
        }
    }


@app.post("/config/update")
async def update_config(
    threshold: int = None,
    interval: int = None,
    ai_enabled: bool = None
):
    """
    动态更新配置
    
    注意: 某些配置需要重启服务才能生效
    """
    updates = {}
    
    if threshold is not None:
        if 0 <= threshold <= 100:
            config.THRESHOLD = threshold
            updates["threshold"] = threshold
        else:
            return {"error": "threshold must be between 0 and 100"}
    
    if interval is not None:
        if interval > 0:
            config.INTERVAL = interval
            scheduler.interval = interval
            updates["interval"] = interval
        else:
            return {"error": "interval must be positive"}
    
    if ai_enabled is not None:
        config.AI_ENABLED = ai_enabled
        gpu_analyzer.ai_enabled = ai_enabled
        updates["ai_enabled"] = ai_enabled
    
    return {
        "status": "updated",
        "updates": updates,
        "note": "Some changes require service restart"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)

