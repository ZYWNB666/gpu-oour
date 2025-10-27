"""
调度器模块
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Optional

from .config import config
from .gpu_analyzer import gpu_analyzer
from .metrics_exporter import metrics_exporter
from .models import GPUMetricsWithAI
import requests

logger = logging.getLogger(__name__)


class Scheduler:
    """后台任务调度器"""
    
    def __init__(self):
        self.interval = config.INTERVAL
        self.latest_results: List[GPUMetricsWithAI] = []
        self.last_analysis_time: Optional[datetime] = None
        self.is_running = False
    
    async def start(self):
        """启动调度器"""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return
        
        self.is_running = True
        logger.info(f"Scheduler started with interval {self.interval}s")
        
        # 立即执行一次
        await self.run_analysis()
        
        # 定期执行
        while self.is_running:
            try:
                await asyncio.sleep(self.interval)
                await self.run_analysis()
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
    
    async def run_analysis(self):
        """执行一次完整分析"""
        start_time = datetime.utcnow()
        logger.info("=" * 60)
        logger.info("Starting GPU utilization analysis")
        
        try:
            # 执行分析
            results = gpu_analyzer.analyze_all()
            
            if not results:
                logger.warning("No GPU data found")
                return
            
            # 更新结果
            self.latest_results = results
            self.last_analysis_time = start_time
            
            # 更新 Prometheus metrics
            metrics_exporter.update_metrics(results)
            metrics_exporter.analysis_total.inc()
            
            # 记录分析耗时
            duration = (datetime.utcnow() - start_time).total_seconds()
            metrics_exporter.analysis_duration.observe(duration)
            
            # 输出分析结果
            self._log_results(results)
            
            # 处理低利用率 GPU
            await self._handle_low_utilization(results)
            
            logger.info(f"Analysis completed in {duration:.2f}s")
            logger.info("=" * 60)
        
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            metrics_exporter.analysis_errors.inc()
    
    def _log_results(self, results: List[GPUMetricsWithAI]):
        """输出分析结果日志"""
        logger.info(f"\nGPU Utilization Analysis Results")
        logger.info("-" * 60)
        logger.info(
            f"{'Namespace/Pod':<40} {'Score':>8} {'Util':>8} {'Status':<10} {'AI':<15}"
        )
        logger.info("-" * 60)
        
        for r in results:
            pod_info = f"{r.namespace}/{r.pod}"
            ai_info = ""
            if r.ai_analysis:
                ai_info = f"{r.ai_analysis.status}({r.ai_analysis.confidence:.2f})"
            
            logger.info(
                f"{pod_info:<40} {r.score:>7.1f}% {r.gpu_util:>7.1f}% "
                f"{r.status.value:<10} {ai_info:<15}"
            )
    
    async def _handle_low_utilization(self, results: List[GPUMetricsWithAI]):
        """处理低利用率 GPU"""
        low_util = [r for r in results if r.score < config.THRESHOLD]
        
        if not low_util:
            logger.info(f"\n✅ All GPUs have utilization above {config.THRESHOLD}%")
            return
        
        logger.warning(f"\n⚠️  Found {len(low_util)} GPU(s) with utilization below {config.THRESHOLD}%:")
        
        for r in low_util:
            msg = f"  - {r.namespace}/{r.pod} ({r.score}%)"
            if r.ai_analysis:
                msg += f" [AI: {r.ai_analysis.status}, {r.ai_analysis.reason}]"
            logger.warning(msg)
            
            # 调用控制接口
            if config.CONTROL_API_ENABLED:
                await self._call_control_api(r)
    
    async def _call_control_api(self, gpu_metrics: GPUMetricsWithAI):
        """调用外部控制接口"""
        try:
            payload = {
                "gpu_id": gpu_metrics.gpu_id,
                "pod": gpu_metrics.pod,
                "namespace": gpu_metrics.namespace,
                "hostname": gpu_metrics.hostname,
                "score": gpu_metrics.score,
                "status": gpu_metrics.status.value,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # 添加 AI 分析结果
            if gpu_metrics.ai_analysis:
                payload["ai_analysis"] = {
                    "status": gpu_metrics.ai_analysis.status,
                    "confidence": gpu_metrics.ai_analysis.confidence,
                    "reason": gpu_metrics.ai_analysis.reason,
                    "recommendation": gpu_metrics.ai_analysis.recommendation
                }
            
            # 设置请求头，模拟正常的 HTTP 客户端
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (compatible; GPU-Monitor/1.0)",
                "Accept": "application/json"
            }
            
            logger.debug(f"Calling Control API: {config.CONTROL_API}")
            logger.debug(f"Payload: {payload}")
            
            resp = requests.post(
                config.CONTROL_API,
                json=payload,
                headers=headers,
                timeout=5
            )
            
            logger.debug(f"Control API response status: {resp.status_code}")
            logger.debug(f"Control API response: {resp.text[:200]}")
            
            if resp.status_code == 200:
                logger.info(f"Control API called for {gpu_metrics.gpu_id}")
            else:
                logger.warning(f"Control API returned {resp.status_code}: {resp.text}")
        
        except Exception as e:
            logger.error(f"Failed to call control API: {e}")
    
    def stop(self):
        """停止调度器"""
        self.is_running = False
        logger.info("Scheduler stopped")
    
    def get_latest_results(self) -> List[GPUMetricsWithAI]:
        """获取最新分析结果"""
        return self.latest_results


# 创建全局调度器实例
scheduler = Scheduler()

