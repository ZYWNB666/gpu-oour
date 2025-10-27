"""
Prometheus 客户端模块
"""

import requests
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

from .config import config
from .models import GPUInfo, MetricsTimeSeries, GPUTimeSeriesData
from .exceptions import PrometheusConnectionError, PrometheusQueryError

logger = logging.getLogger(__name__)


class PrometheusClient:
    """Prometheus 查询客户端"""
    
    def __init__(self):
        self.base_url = config.PROM_URL
        self.query_condition = config.QUERY_CONDITION
        self.time_window = config.TIME_WINDOW_MIN
        self.step = config.STEP
        self._check_connection()
    
    def query_instant(self, query: str) -> dict:
        """
        即时查询
        
        Args:
            query: PromQL 查询语句
        
        Returns:
            查询结果
        """
        url = f"{self.base_url}/api/v1/query"
        try:
            resp = requests.get(url, params={"query": query}, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Instant query failed: {e}")
            return {"data": {"result": []}}
    
    def query_range(
        self,
        metric: str,
        gpu_uuid: str,
        additional_labels: Optional[Dict] = None
    ) -> float:
        """
        查询指定时间范围内的指标平均值
        
        Args:
            metric: 指标名称
            gpu_uuid: GPU UUID
            additional_labels: 额外的标签过滤
        
        Returns:
            指标平均值
        """
        end = datetime.utcnow()
        start = end - timedelta(minutes=self.time_window)
        
        # 构建查询条件 - 所有标签需在同一个大括号内
        labels = [f'pod!=""', f'UUID="{gpu_uuid}"']
        if additional_labels:
            for k, v in additional_labels.items():
                labels.append(f'{k}="{v}"')
        
        query = f'{metric}{{{", ".join(labels)}}}'
        url = f"{self.base_url}/api/v1/query_range"
        
        try:
            resp = requests.get(url, params={
                "query": query,
                "start": start.timestamp(),
                "end": end.timestamp(),
                "step": self.step
            }, timeout=10)
            
            resp.raise_for_status()
            result = resp.json().get("data", {}).get("result", [])
            
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
            logger.error(f"Range query failed for {metric}/{gpu_uuid}: {e}")
            return 0.0
    
    def get_time_series(
        self,
        metric: str,
        gpu_uuid: str
    ) -> MetricsTimeSeries:
        """
        获取指标的完整时序数据
        
        Args:
            metric: 指标名称
            gpu_uuid: GPU UUID
        
        Returns:
            时序数据
        """
        end = datetime.utcnow()
        start = end - timedelta(minutes=self.time_window)
        
        # 构建查询条件 - 所有标签需在同一个大括号内
        query = f'{metric}{{pod!="", UUID="{gpu_uuid}"}}'
        url = f"{self.base_url}/api/v1/query_range"
        
        try:
            resp = requests.get(url, params={
                "query": query,
                "start": start.timestamp(),
                "end": end.timestamp(),
                "step": self.step
            }, timeout=10)
            
            resp.raise_for_status()
            result = resp.json().get("data", {}).get("result", [])
            
            if not result:
                return MetricsTimeSeries(timestamps=[], values=[])
            
            timestamps = []
            values = []
            
            for item in result[0].get("values", []):
                try:
                    ts = float(item[0])
                    val = float(item[1])
                    if not np.isnan(val):
                        timestamps.append(ts)
                        values.append(val)
                except (ValueError, TypeError):
                    continue
            
            return MetricsTimeSeries(timestamps=timestamps, values=values)
        
        except Exception as e:
            logger.error(f"Time series query failed: {e}")
            return MetricsTimeSeries(timestamps=[], values=[])
    
    def get_gpu_time_series_data(self, gpu_uuid: str) -> GPUTimeSeriesData:
        """
        获取 GPU 的所有关键指标时序数据（用于 AI 分析）
        
        Args:
            gpu_uuid: GPU UUID
        
        Returns:
            GPU 时序数据
        """
        return GPUTimeSeriesData(
            gpu_id=gpu_uuid,
            gpu_util_series=self.get_time_series("DCGM_FI_DEV_GPU_UTIL", gpu_uuid),
            mem_used_series=self.get_time_series("DCGM_FI_DEV_FB_USED", gpu_uuid),
            power_series=self.get_time_series("DCGM_FI_DEV_POWER_USAGE", gpu_uuid),
            mem_copy_series=self.get_time_series("DCGM_FI_DEV_MEM_COPY_UTIL", gpu_uuid)
        )
    
    def get_all_gpu_series(self) -> List[GPUInfo]:
        """
        获取当前活跃的 GPU 列表及其标签信息
        
        Returns:
            GPU 信息列表
        """
        query = f'DCGM_FI_DEV_GPU_UTIL{self.query_condition}'
        url = f"{self.base_url}/api/v1/series"
        
        try:
            resp = requests.get(url, params={"match[]": query}, timeout=10)
            resp.raise_for_status()
            
            gpu_list = []
            for s in resp.json().get("data", []):
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
            
            logger.info(f"Found {len(gpu_list)} active GPUs")
            return gpu_list
        
        except Exception as e:
            logger.error(f"Failed to get GPU list: {e}")
            return []
    
    def _check_connection(self):
        """检查 Prometheus 连接"""
        try:
            url = f"{self.base_url}/api/v1/status/config"
            resp = requests.get(url, timeout=5)
            resp.raise_for_status()
            logger.info("Prometheus connection established")
        except Exception as e:
            logger.warning(f"Prometheus connection check failed: {e}")
    
    def health_check(self) -> bool:
        """
        健康检查
        
        Returns:
            是否健康
        """
        try:
            url = f"{self.base_url}/api/v1/query"
            resp = requests.get(url, params={"query": "up"}, timeout=5)
            resp.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Prometheus health check failed: {e}")
            return False

