"""
错误处理模块
"""

from typing import Optional
import logging

logger = logging.getLogger(__name__)


class GPUMonitorError(Exception):
    """GPU 监控基础异常"""
    pass


class PrometheusConnectionError(GPUMonitorError):
    """Prometheus 连接错误"""
    pass


class PrometheusQueryError(GPUMonitorError):
    """Prometheus 查询错误"""
    pass


class AIAnalysisError(GPUMonitorError):
    """AI 分析错误"""
    pass


class ConfigurationError(GPUMonitorError):
    """配置错误"""
    pass


class ControlAPIError(GPUMonitorError):
    """控制接口调用错误"""
    pass


def handle_error(error: Exception, context: Optional[str] = None) -> None:
    """
    统一错误处理
    
    Args:
        error: 异常对象
        context: 上下文信息
    """
    error_msg = f"{context}: {str(error)}" if context else str(error)
    
    if isinstance(error, PrometheusConnectionError):
        logger.error(f"[Prometheus Connection] {error_msg}")
    elif isinstance(error, PrometheusQueryError):
        logger.error(f"[Prometheus Query] {error_msg}")
    elif isinstance(error, AIAnalysisError):
        logger.error(f"[AI Analysis] {error_msg}")
    elif isinstance(error, ConfigurationError):
        logger.error(f"[Configuration] {error_msg}")
    elif isinstance(error, ControlAPIError):
        logger.error(f"[Control API] {error_msg}")
    else:
        logger.error(f"[Unknown Error] {error_msg}")

