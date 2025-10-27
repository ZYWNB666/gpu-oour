"""
数据模型定义
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum


class GPUStatus(str, Enum):
    """GPU 状态枚举"""
    IDLE = "idle"        # 完全闲置
    LOW = "low"          # 低利用率
    NORMAL = "normal"    # 正常使用
    HIGH = "high"        # 高负载


class GPUInfo(BaseModel):
    """GPU 基础信息"""
    uuid: str = Field(..., description="GPU UUID")
    pod: str = Field(..., description="Pod 名称")
    namespace: str = Field(..., description="命名空间")
    hostname: str = Field(default="", description="节点主机名")
    gpu_index: str = Field(default="", description="GPU 索引")
    model_name: str = Field(default="", description="GPU 型号")


class GPUMetrics(BaseModel):
    """GPU 指标数据"""
    gpu_id: str = Field(..., description="GPU ID")
    pod: str = Field(..., description="Pod 名称")
    namespace: str = Field(..., description="命名空间")
    hostname: str = Field(..., description="节点主机名")
    model_name: str = Field(..., description="GPU 型号")
    
    # 原始指标
    gpu_util: float = Field(..., description="GPU 核心利用率 (%)")
    mem_copy: float = Field(..., description="内存拷贝利用率 (%)")
    mem_used_mb: float = Field(..., description="显存使用量 (MB)")
    mem_total_mb: float = Field(..., description="显存总量 (MB)")
    mem_usage_percent: float = Field(..., description="显存使用率 (%)")
    power_usage: float = Field(..., description="功率使用 (W)")
    sm_clock: float = Field(..., description="SM 时钟频率 (MHz)")
    
    # 计算结果
    score: float = Field(..., description="综合利用率评分 (0-100)")
    status: GPUStatus = Field(..., description="GPU 状态")
    
    # 时间戳
    timestamp: Optional[str] = Field(None, description="采集时间")


class AIAnalysisResult(BaseModel):
    """AI 分析结果"""
    gpu_id: str = Field(..., description="GPU ID")
    status: str = Field(..., description="AI 判断的状态: active/idle/suspicious")
    confidence: float = Field(..., description="置信度 (0-1)")
    reason: str = Field(..., description="判断理由")
    recommendation: str = Field(..., description="操作建议")
    raw_score: float = Field(..., description="原始评分")
    ai_adjusted_score: Optional[float] = Field(None, description="AI 调整后的评分")


class GPUMetricsWithAI(GPUMetrics):
    """包含 AI 分析的 GPU 指标"""
    ai_analysis: Optional[AIAnalysisResult] = Field(None, description="AI 分析结果")


class MetricsTimeSeries(BaseModel):
    """指标时序数据"""
    timestamps: List[float] = Field(..., description="时间戳列表")
    values: List[float] = Field(..., description="指标值列表")


class GPUTimeSeriesData(BaseModel):
    """GPU 时序数据"""
    gpu_id: str
    gpu_util_series: MetricsTimeSeries
    mem_used_series: MetricsTimeSeries
    power_series: MetricsTimeSeries
    mem_copy_series: MetricsTimeSeries


class AnalysisStats(BaseModel):
    """分析统计信息"""
    total_gpus: int
    avg_score: float
    min_score: float
    max_score: float
    low_utilization_count: int
    idle_count: int
    by_status: dict
    by_namespace: dict

