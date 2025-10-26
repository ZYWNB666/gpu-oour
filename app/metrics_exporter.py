"""
Prometheus Metrics 导出模块
"""

from prometheus_client import Counter, Gauge, Histogram, Info, generate_latest, CONTENT_TYPE_LATEST
from typing import List
import logging

from .models import GPUMetricsWithAI
from .config import config

logger = logging.getLogger(__name__)


class MetricsExporter:
    """Prometheus Metrics 导出器"""
    
    def __init__(self):
        # GPU 评分指标
        self.gpu_score = Gauge(
            'gpu_utilization_score',
            'GPU综合利用率评分 (0-100)',
            ['gpu_id', 'pod', 'namespace', 'hostname', 'model', 'status']
        )
        
        # GPU 核心利用率
        self.gpu_util = Gauge(
            'gpu_core_utilization',
            'GPU核心利用率 (%)',
            ['gpu_id', 'pod', 'namespace', 'hostname']
        )
        
        # 显存使用量
        self.gpu_memory = Gauge(
            'gpu_memory_used_mb',
            'GPU显存使用量 (MB)',
            ['gpu_id', 'pod', 'namespace', 'hostname']
        )
        
        # 功率使用
        self.gpu_power = Gauge(
            'gpu_power_usage_watts',
            'GPU功率使用 (W)',
            ['gpu_id', 'pod', 'namespace', 'hostname']
        )
        
        # 内存拷贝利用率
        self.gpu_mem_copy = Gauge(
            'gpu_memory_copy_utilization',
            'GPU内存拷贝利用率 (%)',
            ['gpu_id', 'pod', 'namespace', 'hostname']
        )
        
        # SM 时钟频率
        self.gpu_sm_clock = Gauge(
            'gpu_sm_clock_mhz',
            'GPU SM时钟频率 (MHz)',
            ['gpu_id', 'pod', 'namespace', 'hostname']
        )
        
        # AI 分析结果
        self.ai_confidence = Gauge(
            'gpu_ai_analysis_confidence',
            'AI分析置信度 (0-1)',
            ['gpu_id', 'pod', 'namespace', 'ai_status']
        )
        
        self.ai_adjusted_score = Gauge(
            'gpu_ai_adjusted_score',
            'AI调整后的评分 (0-100)',
            ['gpu_id', 'pod', 'namespace']
        )
        
        # 统计指标
        self.total_gpus = Gauge(
            'gpu_total_count',
            'GPU总数'
        )
        
        self.low_util_gpus = Gauge(
            'gpu_low_utilization_count',
            '低利用率GPU数量'
        )
        
        self.idle_gpus = Gauge(
            'gpu_idle_count',
            '闲置GPU数量'
        )
        
        self.avg_score = Gauge(
            'gpu_average_score',
            '平均GPU评分'
        )
        
        # 状态分布
        self.status_count = Gauge(
            'gpu_status_count',
            'GPU状态分布',
            ['status']
        )
        
        # 命名空间统计
        self.namespace_gpu_count = Gauge(
            'gpu_namespace_count',
            '各命名空间GPU数量',
            ['namespace']
        )
        
        self.namespace_avg_score = Gauge(
            'gpu_namespace_average_score',
            '各命名空间平均评分',
            ['namespace']
        )
        
        # 分析计数器
        self.analysis_total = Counter(
            'gpu_analysis_total',
            'GPU分析总次数'
        )
        
        self.analysis_errors = Counter(
            'gpu_analysis_errors_total',
            'GPU分析错误次数'
        )
        
        # 响应时间
        self.analysis_duration = Histogram(
            'gpu_analysis_duration_seconds',
            'GPU分析耗时 (秒)'
        )
        
        # 服务信息
        self.service_info = Info(
            'gpu_monitor_service',
            'GPU监控服务信息'
        )
        
        self.service_info.info({
            'version': '1.0.0',
            'threshold': str(config.THRESHOLD),
            'interval': str(config.INTERVAL),
            'ai_enabled': str(config.AI_ENABLED)
        })
    
    def update_metrics(self, results: List[GPUMetricsWithAI]):
        """
        更新所有 metrics
        
        Args:
            results: GPU 分析结果列表
        """
        if not results:
            logger.warning("No results to export")
            return
        
        try:
            # 更新每个 GPU 的指标
            for r in results:
                labels = {
                    'gpu_id': r.gpu_id[:32],  # 截断过长的 ID
                    'pod': r.pod,
                    'namespace': r.namespace,
                    'hostname': r.hostname
                }
                
                # 基础指标
                self.gpu_score.labels(
                    **labels,
                    model=r.model_name[:20] if r.model_name else 'unknown',
                    status=r.status.value
                ).set(r.score)
                
                self.gpu_util.labels(**labels).set(r.gpu_util)
                self.gpu_memory.labels(**labels).set(r.mem_used_mb)
                self.gpu_power.labels(**labels).set(r.power_usage)
                self.gpu_mem_copy.labels(**labels).set(r.mem_copy)
                self.gpu_sm_clock.labels(**labels).set(r.sm_clock)
                
                # AI 分析指标
                if r.ai_analysis:
                    ai_labels = {
                        'gpu_id': r.gpu_id[:32],
                        'pod': r.pod,
                        'namespace': r.namespace,
                        'ai_status': r.ai_analysis.status
                    }
                    self.ai_confidence.labels(**ai_labels).set(r.ai_analysis.confidence)
                    
                    if r.ai_analysis.ai_adjusted_score is not None:
                        self.ai_adjusted_score.labels(
                            gpu_id=r.gpu_id[:32],
                            pod=r.pod,
                            namespace=r.namespace
                        ).set(r.ai_analysis.ai_adjusted_score)
            
            # 更新统计指标
            self._update_stats(results)
            
            logger.info(f"Metrics updated for {len(results)} GPUs")
        
        except Exception as e:
            logger.error(f"Failed to update metrics: {e}")
            self.analysis_errors.inc()
    
    def _update_stats(self, results: List[GPUMetricsWithAI]):
        """更新统计指标"""
        from collections import defaultdict
        
        # 总数统计
        self.total_gpus.set(len(results))
        
        scores = [r.score for r in results]
        if scores:
            self.avg_score.set(sum(scores) / len(scores))
        
        # 状态统计
        status_counts = defaultdict(int)
        for r in results:
            status_counts[r.status.value] += 1
        
        for status, count in status_counts.items():
            self.status_count.labels(status=status).set(count)
        
        self.low_util_gpus.set(
            len([r for r in results if r.score < config.THRESHOLD])
        )
        self.idle_gpus.set(
            len([r for r in results if r.score < config.IDLE_THRESHOLD])
        )
        
        # 命名空间统计
        ns_stats = defaultdict(lambda: {'count': 0, 'total_score': 0})
        for r in results:
            ns_stats[r.namespace]['count'] += 1
            ns_stats[r.namespace]['total_score'] += r.score
        
        for ns, stats in ns_stats.items():
            self.namespace_gpu_count.labels(namespace=ns).set(stats['count'])
            avg = stats['total_score'] / stats['count']
            self.namespace_avg_score.labels(namespace=ns).set(avg)
    
    def get_metrics(self) -> bytes:
        """
        获取 Prometheus 格式的 metrics
        
        Returns:
            Metrics 数据
        """
        return generate_latest()
    
    def get_content_type(self) -> str:
        """
        获取 Content-Type
        
        Returns:
            Content-Type
        """
        return CONTENT_TYPE_LATEST


# 创建全局 metrics 导出器实例
metrics_exporter = MetricsExporter()

