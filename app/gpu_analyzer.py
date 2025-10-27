"""
GPU 分析器模块
"""

import logging
from datetime import datetime
from typing import List
import concurrent.futures

from .config import config
from .models import GPUInfo, GPUMetrics, GPUStatus, GPUMetricsWithAI
from .prometheus_client import PrometheusClient
from .ai_analyzer import ai_analyzer

logger = logging.getLogger(__name__)


class GPUAnalyzer:
    """GPU 分析器"""
    
    def __init__(self):
        self.prom_client = PrometheusClient()
        self.ai_enabled = config.AI_ENABLED
    
    def compute_score(self, gpu_info: GPUInfo) -> GPUMetrics:
        """
        计算单个 GPU 的综合利用率评分
        
        Args:
            gpu_info: GPU 信息
        
        Returns:
            GPU 指标和评分
        """
        uuid = gpu_info.uuid
        
        # 查询各项指标
        gpu_util = self.prom_client.query_range("DCGM_FI_DEV_GPU_UTIL", uuid)
        mem_copy = self.prom_client.query_range("DCGM_FI_DEV_MEM_COPY_UTIL", uuid)
        mem_used = self.prom_client.query_range("DCGM_FI_DEV_FB_USED", uuid)
        mem_free = self.prom_client.query_range("DCGM_FI_DEV_FB_FREE", uuid)
        power_usage = self.prom_client.query_range("DCGM_FI_DEV_POWER_USAGE", uuid)
        sm_clock = self.prom_client.query_range("DCGM_FI_DEV_SM_CLOCK", uuid)
        
        # DCGM_FI_DEV_FB_USED/FREE 返回的单位已经是 MB
        mem_used_mb = mem_used
        mem_free_mb = mem_free
        
        # 计算显存总量（动态获取，不使用固定默认值）
        mem_total_mb = mem_used_mb + mem_free_mb
        if mem_total_mb <= 0:
            # 如果无法获取实际总量，使用配置的默认值
            mem_total_mb = config.DEFAULT_GPU_MEMORY_MB
            logger.warning(f"GPU {uuid}: Unable to get actual memory total, using default {mem_total_mb} MB")
        
        # 计算显存使用率
        mem_usage_ratio = min(mem_used_mb / mem_total_mb, 1.0) if mem_total_mb > 0 else 0.0
        
        # 计算综合评分
        score = (
            config.GPU_UTIL_WEIGHT * (gpu_util / 100) +
            config.MEM_COPY_WEIGHT * (mem_copy / 100) +
            config.MEM_USED_WEIGHT * mem_usage_ratio +
            config.POWER_WEIGHT * min(power_usage / config.DEFAULT_GPU_POWER_W, 1.0)
        )
        
        score_percent = round(score * 100, 1)
        
        # 判断状态
        status = self._determine_status(score_percent)
        
        return GPUMetrics(
            gpu_id=uuid,
            pod=gpu_info.pod,
            namespace=gpu_info.namespace,
            hostname=gpu_info.hostname,
            model_name=gpu_info.model_name,
            gpu_util=round(gpu_util, 2),
            mem_copy=round(mem_copy, 2),
            mem_used_mb=round(mem_used_mb, 1),
            mem_total_mb=round(mem_total_mb, 1),
            mem_usage_percent=round(mem_usage_ratio * 100, 2),
            power_usage=round(power_usage, 1),
            sm_clock=round(sm_clock, 0),
            score=score_percent,
            status=status,
            timestamp=datetime.utcnow().isoformat()
        )
    
    def _determine_status(self, score: float) -> GPUStatus:
        """
        根据评分确定 GPU 状态
        
        Args:
            score: 评分 (0-100)
        
        Returns:
            GPU 状态
        """
        if score < config.IDLE_THRESHOLD:
            return GPUStatus.IDLE
        elif score < config.THRESHOLD:
            return GPUStatus.LOW
        elif score < 70:
            return GPUStatus.NORMAL
        else:
            return GPUStatus.HIGH
    
    def compute_score_with_ai(self, gpu_info: GPUInfo) -> GPUMetricsWithAI:
        """
        计算评分并使用 AI 进行分析
        
        Args:
            gpu_info: GPU 信息
        
        Returns:
            包含 AI 分析的 GPU 指标
        """
        # 先计算基础评分
        metrics = self.compute_score(gpu_info)
        
        # 如果 AI 未启用，直接返回
        if not self.ai_enabled:
            return GPUMetricsWithAI(**metrics.dict())
        
        # 使用 AI 分析
        try:
            # 获取时序数据
            time_series_data = self.prom_client.get_gpu_time_series_data(gpu_info.uuid)
            
            # AI 分析
            ai_result = ai_analyzer.analyze_gpu(
                gpu_info.uuid,
                time_series_data,
                metrics.score
            )
            
            # 如果 AI 给出了调整后的评分，更新状态
            if ai_result and ai_result.ai_adjusted_score is not None:
                metrics.score = ai_result.ai_adjusted_score
                metrics.status = self._determine_status(ai_result.ai_adjusted_score)
            
            return GPUMetricsWithAI(**metrics.dict(), ai_analysis=ai_result)
        
        except Exception as e:
            logger.error(f"AI analysis failed for {gpu_info.uuid}: {e}")
            return GPUMetricsWithAI(**metrics.dict())
    
    def analyze_all(self, use_ai: bool = None) -> List[GPUMetricsWithAI]:
        """
        分析所有 GPU
        
        Args:
            use_ai: 是否使用 AI 分析（None 表示使用配置）
        
        Returns:
            GPU 指标列表
        """
        # 获取所有 GPU
        gpu_list = self.prom_client.get_all_gpu_series()
        
        if not gpu_list:
            logger.warning("No GPU data found")
            return []
        
        # 决定是否使用 AI
        if use_ai is None:
            use_ai = self.ai_enabled
        
        # 多线程并发计算
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
            if use_ai:
                futures = [executor.submit(self.compute_score_with_ai, gpu) for gpu in gpu_list]
            else:
                futures = [
                    executor.submit(lambda g: GPUMetricsWithAI(**self.compute_score(g).dict()), gpu) 
                    for gpu in gpu_list
                ]
            
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"Failed to compute GPU score: {e}")
        
        # 按评分排序
        results.sort(key=lambda x: x.score)
        
        return results


# 创建全局分析器实例
gpu_analyzer = GPUAnalyzer()

