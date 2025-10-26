"""
工具函数模块
"""

import logging
from typing import Dict, Any, Optional
import json

logger = logging.getLogger(__name__)


def safe_float(value: Any, default: float = 0.0) -> float:
    """
    安全地转换为浮点数
    
    Args:
        value: 待转换的值
        default: 默认值
    
    Returns:
        转换后的浮点数
    """
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    """
    安全地转换为整数
    
    Args:
        value: 待转换的值
        default: 默认值
    
    Returns:
        转换后的整数
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def truncate_string(text: str, max_length: int = 50, suffix: str = "...") -> str:
    """
    截断字符串
    
    Args:
        text: 原始字符串
        max_length: 最大长度
        suffix: 后缀
    
    Returns:
        截断后的字符串
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def format_bytes(bytes_value: float, unit: str = "auto") -> str:
    """
    格式化字节数
    
    Args:
        bytes_value: 字节数
        unit: 单位 (auto/KB/MB/GB)
    
    Returns:
        格式化后的字符串
    """
    if unit == "auto":
        if bytes_value < 1024:
            return f"{bytes_value:.0f} B"
        elif bytes_value < 1024 ** 2:
            return f"{bytes_value / 1024:.2f} KB"
        elif bytes_value < 1024 ** 3:
            return f"{bytes_value / (1024 ** 2):.2f} MB"
        else:
            return f"{bytes_value / (1024 ** 3):.2f} GB"
    elif unit == "KB":
        return f"{bytes_value / 1024:.2f} KB"
    elif unit == "MB":
        return f"{bytes_value / (1024 ** 2):.2f} MB"
    elif unit == "GB":
        return f"{bytes_value / (1024 ** 3):.2f} GB"
    else:
        return f"{bytes_value:.0f} B"


def format_duration(seconds: float) -> str:
    """
    格式化时间
    
    Args:
        seconds: 秒数
    
    Returns:
        格式化后的字符串
    """
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.2f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m{secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h{minutes}m"


def parse_json_safe(text: str, default: Optional[Dict] = None) -> Dict:
    """
    安全地解析 JSON
    
    Args:
        text: JSON 字符串
        default: 默认值
    
    Returns:
        解析后的字典
    """
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError) as e:
        logger.warning(f"Failed to parse JSON: {e}")
        return default or {}


def validate_percentage(value: float, allow_over_100: bool = False) -> bool:
    """
    验证百分比值
    
    Args:
        value: 待验证的值
        allow_over_100: 是否允许超过 100
    
    Returns:
        是否有效
    """
    if allow_over_100:
        return value >= 0
    return 0 <= value <= 100


def calculate_change_rate(old_value: float, new_value: float) -> float:
    """
    计算变化率
    
    Args:
        old_value: 旧值
        new_value: 新值
    
    Returns:
        变化率（百分比）
    """
    if old_value == 0:
        return 0.0 if new_value == 0 else 100.0
    return ((new_value - old_value) / old_value) * 100


def get_severity_emoji(score: float, threshold_low: float = 20, threshold_high: float = 70) -> str:
    """
    根据评分获取表情符号
    
    Args:
        score: 评分
        threshold_low: 低阈值
        threshold_high: 高阈值
    
    Returns:
        表情符号
    """
    if score < threshold_low:
        return "🔴"  # 红色 - 低利用率
    elif score < threshold_high:
        return "🟡"  # 黄色 - 正常
    else:
        return "🟢"  # 绿色 - 高负载

