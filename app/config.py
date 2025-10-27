"""
配置管理模块

配置优先级：环境变量 > YAML 文件 > 默认值
"""

import os
import yaml
from pathlib import Path
from typing import Optional, Dict, Any


def load_yaml_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """
    加载 YAML 配置文件
    
    Args:
        config_path: 配置文件路径
    
    Returns:
        配置字典
    """
    config_file = Path(config_path)
    if config_file.exists():
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            print(f"Warning: Failed to load {config_path}: {e}")
    return {}


class Config:
    """应用配置类"""
    
    def __init__(self, config_file: str = "config.yaml"):
        """
        初始化配置
        
        Args:
            config_file: YAML 配置文件路径（可选）
        """
        # 加载 YAML 配置（如果存在）
        yaml_config = load_yaml_config(config_file)
        
        # Prometheus 配置
        # 优先级：环境变量 > YAML > 默认值
        self.PROM_URL = os.getenv(
            "PROM_URL",
            yaml_config.get("prometheus", {}).get("url", "http://prometheus:9090")
        )
        self.QUERY_CONDITION = os.getenv(
            "QUERY_CONDITION",
            yaml_config.get("prometheus", {}).get("query_condition", '{pod!=""}')
        )
        self.TIME_WINDOW_MIN = int(os.getenv(
            "TIME_WINDOW_MIN",
            yaml_config.get("prometheus", {}).get("time_window_min", 10)
        ))
        self.STEP = yaml_config.get("prometheus", {}).get("step", "30s")
        
        # 评分权重配置
        scoring = yaml_config.get("scoring", {})
        self.GPU_UTIL_WEIGHT = float(scoring.get("gpu_util_weight", 0.5))
        self.MEM_COPY_WEIGHT = float(scoring.get("mem_copy_weight", 0.2))
        self.MEM_USED_WEIGHT = float(scoring.get("mem_used_weight", 0.2))
        self.POWER_WEIGHT = float(scoring.get("power_weight", 0.1))
        
        # 阈值配置
        thresholds = yaml_config.get("thresholds", {})
        self.THRESHOLD = int(os.getenv(
            "THRESHOLD",
            thresholds.get("low_utilization", 20)
        ))
        self.IDLE_THRESHOLD = int(thresholds.get("idle", 10))
        
        # 调度配置
        scheduler = yaml_config.get("scheduler", {})
        self.INTERVAL = int(os.getenv(
            "INTERVAL",
            scheduler.get("interval", 300)
        ))
        self.MAX_WORKERS = int(os.getenv(
            "MAX_WORKERS",
            scheduler.get("max_workers", 8)
        ))
        
        # GPU 默认配置
        gpu_defaults = yaml_config.get("gpu_defaults", {})
        self.DEFAULT_GPU_MEMORY_MB = int(gpu_defaults.get("memory_mb", 32000))
        self.DEFAULT_GPU_POWER_W = int(gpu_defaults.get("power_w", 250))
        
        # 控制接口配置
        control = yaml_config.get("control", {})
        self.CONTROL_API = os.getenv(
            "CONTROL_API",
            control.get("api_url", "http://your-control-service/api/optimize")
        )
        self.CONTROL_API_ENABLED = os.getenv(
            "CONTROL_API_ENABLED",
            str(control.get("enabled", False))
        ).lower() == "true"
        
        # AI 配置
        ai_config = yaml_config.get("ai", {})
        self.AI_ENABLED = str(os.getenv(
            "AI_ENABLED",
            ai_config.get("enabled", False)
        )).lower() == "true"
        self.AI_API_URL = os.getenv(
            "AI_API_URL",
            ai_config.get("api_url", "")
        )
        # API Key 优先从环境变量读取（安全考虑）
        self.AI_API_KEY = os.getenv(
            "AI_API_KEY",
            ai_config.get("api_key", "")
        )
        self.AI_MODEL = os.getenv(
            "AI_MODEL",
            ai_config.get("model", "gpt-4")
        )
        self.AI_THRESHOLD = float(ai_config.get("threshold", 0.7))
        self.AI_MAX_TOKENS = int(os.getenv(
            "AI_MAX_TOKENS",
            ai_config.get("max_tokens", 2000)
        ))
        self.AI_RETRY_TIMES = int(os.getenv(
            "AI_RETRY_TIMES",
            ai_config.get("retry_times", 3)
        ))
        self.AI_RETRY_DELAY = float(os.getenv(
            "AI_RETRY_DELAY",
            ai_config.get("retry_delay", 2.0)
        ))
        
        # 日志配置
        logging_config = yaml_config.get("logging", {})
        self.LOG_LEVEL = os.getenv(
            "LOG_LEVEL",
            logging_config.get("level", "INFO")
        )
    
    def validate(self):
        """验证配置"""
        if self.AI_ENABLED and not self.AI_API_URL:
            raise ValueError("AI_ENABLED is True but AI_API_URL is not set")
        
        if self.THRESHOLD < 0 or self.THRESHOLD > 100:
            raise ValueError("THRESHOLD must be between 0 and 100")
    
    def to_dict(self) -> Dict[str, Any]:
        """导出配置为字典"""
        return {
            "prometheus": {
                "url": self.PROM_URL,
                "query_condition": self.QUERY_CONDITION,
                "time_window_min": self.TIME_WINDOW_MIN,
                "step": self.STEP
            },
            "scoring": {
                "gpu_util_weight": self.GPU_UTIL_WEIGHT,
                "mem_copy_weight": self.MEM_COPY_WEIGHT,
                "mem_used_weight": self.MEM_USED_WEIGHT,
                "power_weight": self.POWER_WEIGHT
            },
            "thresholds": {
                "low_utilization": self.THRESHOLD,
                "idle": self.IDLE_THRESHOLD
            },
            "scheduler": {
                "interval": self.INTERVAL,
                "max_workers": self.MAX_WORKERS
            },
            "gpu_defaults": {
                "memory_mb": self.DEFAULT_GPU_MEMORY_MB,
                "power_w": self.DEFAULT_GPU_POWER_W
            },
            "control": {
                "enabled": self.CONTROL_API_ENABLED,
                "api_url": self.CONTROL_API
            },
            "ai": {
                "enabled": self.AI_ENABLED,
                "api_url": self.AI_API_URL,
                "model": self.AI_MODEL,
                "max_tokens": self.AI_MAX_TOKENS,
                "retry_times": self.AI_RETRY_TIMES,
                "retry_delay": self.AI_RETRY_DELAY
            },
            "logging": {
                "level": self.LOG_LEVEL
            }
        }


# 创建全局配置实例
config = Config()

