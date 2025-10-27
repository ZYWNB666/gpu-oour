"""
AI 分析模块
"""

import requests
import json
import logging
from typing import Optional

from .config import config
from .models import GPUTimeSeriesData, AIAnalysisResult
from .exceptions import AIAnalysisError

logger = logging.getLogger(__name__)


class AIAnalyzer:
    """AI 分析器"""
    
    def __init__(self):
        self.enabled = config.AI_ENABLED
        self.api_url = config.AI_API_URL
        self.api_key = config.AI_API_KEY
        self.model = config.AI_MODEL
        self.threshold = config.AI_THRESHOLD
        self.max_tokens = config.AI_MAX_TOKENS
    
    def analyze_gpu(
        self,
        gpu_id: str,
        time_series_data: GPUTimeSeriesData,
        raw_score: float
    ) -> Optional[AIAnalysisResult]:
        """
        使用 AI 分析 GPU 使用情况
        
        Args:
            gpu_id: GPU ID
            time_series_data: GPU 时序数据
            raw_score: 原始评分
        
        Returns:
            AI 分析结果
        """
        if not self.enabled:
            logger.debug("AI analysis is disabled")
            return None
        
        try:
            # 构建 AI Prompt
            prompt = self._build_prompt(time_series_data, raw_score)
            
            # 调用 AI API
            ai_response = self._call_ai_api(prompt)
            
            # 解析响应
            result = self._parse_response(gpu_id, ai_response, raw_score)
            
            logger.info(f"AI analysis for {gpu_id}: {result.status} (confidence: {result.confidence})")
            return result
        
        except Exception as e:
            logger.error(f"AI analysis failed for {gpu_id}: {e}")
            return None
    
    def _build_prompt(self, data: GPUTimeSeriesData, raw_score: float) -> str:
        """
        构建 AI 分析 Prompt
        
        Args:
            data: GPU 时序数据
            raw_score: 原始评分
        
        Returns:
            Prompt 文本
        """
        # 计算统计特征
        gpu_util_stats = self._calculate_stats(data.gpu_util_series.values)
        mem_used_stats = self._calculate_stats(data.mem_used_series.values)
        power_stats = self._calculate_stats(data.power_series.values)
        
        prompt = f"""请分析以下 GPU 在最近 {config.TIME_WINDOW_MIN} 分钟的使用情况，判断是否在进行有效计算。

## GPU 指标数据

1. **GPU 核心利用率**
   - 平均值: {gpu_util_stats['mean']:.2f}%
   - 最小值: {gpu_util_stats['min']:.2f}%
   - 最大值: {gpu_util_stats['max']:.2f}%
   - 标准差: {gpu_util_stats['std']:.2f}%
   - 变化率: {gpu_util_stats['change_rate']:.2f}%

2. **显存使用**
   - 平均值: {mem_used_stats['mean']/1e9:.2f} GB
   - 最小值: {mem_used_stats['min']/1e9:.2f} GB
   - 最大值: {mem_used_stats['max']/1e9:.2f} GB
   - 标准差: {mem_used_stats['std']/1e9:.2f} GB

3. **功率使用**
   - 平均值: {power_stats['mean']:.2f} W
   - 最小值: {power_stats['min']:.2f} W
   - 最大值: {power_stats['max']:.2f} W
   - 标准差: {power_stats['std']:.2f} W

4. **系统评分**: {raw_score:.1f}/100

## 分析要求

请根据以上数据判断 GPU 的使用状态，并输出 JSON 格式结果：

```json
{{
    "status": "active" | "idle" | "suspicious",
    "confidence": 0.0-1.0,
    "reason": "判断理由（中文，简洁明了）",
    "recommendation": "操作建议（中文）",
    "adjusted_score": 0-100
}}
```

**判断标准：**
- `active`: GPU 正在进行有效计算（训练/推理）
- `idle`: GPU 完全闲置或未被有效使用
- `suspicious`: 状态可疑，需要人工确认

**注意事项：**
1. 考虑指标的波动性和趋势
2. GPU 利用率波动大可能表示正在训练
3. 显存占用高但利用率低可能是模型加载后未训练
4. 功率低通常表示闲置状态
5. 如果系统评分与实际情况不符，可以调整 adjusted_score

请直接返回 JSON，不要包含任何其他文字。"""

        return prompt
    
    def _calculate_stats(self, values: list) -> dict:
        """计算统计特征"""
        if not values:
            return {
                'mean': 0, 'min': 0, 'max': 0, 
                'std': 0, 'change_rate': 0
            }
        
        import numpy as np
        arr = np.array(values)
        
        change_rate = 0
        if len(arr) > 1:
            change_rate = abs(arr[-1] - arr[0]) / (arr[0] + 1e-6) * 100
        
        return {
            'mean': float(np.mean(arr)),
            'min': float(np.min(arr)),
            'max': float(np.max(arr)),
            'std': float(np.std(arr)),
            'change_rate': float(change_rate)
        }
    
    def _call_ai_api(self, prompt: str) -> dict:
        """
        调用 AI API
        
        Args:
            prompt: Prompt 文本
        
        Returns:
            API 响应
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # 支持 OpenAI/Claude 等多种 API 格式
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "你是一个专业的 GPU 使用情况分析专家，能够根据监控数据准确判断 GPU 是否在被有效使用。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.3,
            "max_completion_tokens": self.max_tokens  # 使用 max_completion_tokens 以支持推理模型
        }
        
        resp = requests.post(
            self.api_url,
            headers=headers,
            json=payload,
            timeout=30
        )
        
        resp.raise_for_status()
        response_data = resp.json()
        
        # 调试日志：输出响应结构
        logger.debug(f"AI API response status: {resp.status_code}")
        logger.debug(f"AI API response keys: {response_data.keys() if response_data else 'None'}")
        
        return response_data
    
    def _parse_response(
        self,
        gpu_id: str,
        response: dict,
        raw_score: float
    ) -> AIAnalysisResult:
        """
        解析 AI API 响应
        
        Args:
            gpu_id: GPU ID
            response: API 响应
            raw_score: 原始评分
        
        Returns:
            解析后的结果
        """
        try:
            # 检查响应结构
            if not response:
                raise ValueError("AI API 返回空响应")
            
            # OpenAI 格式
            if "choices" not in response:
                logger.error(f"Unexpected response format. Keys: {response.keys()}")
                logger.error(f"Response content: {response}")
                raise ValueError("响应格式不正确：缺少 'choices' 字段")
            
            if not response["choices"]:
                raise ValueError("choices 列表为空")
            
            choice = response["choices"][0]
            finish_reason = choice.get("finish_reason", "unknown")
            content = choice["message"]["content"]
            
            # 调试日志
            logger.debug(f"AI finish_reason: {finish_reason}")
            logger.debug(f"AI raw content (first 200 chars): {content[:200] if content else 'Empty'}")
            
            if not content or not content.strip():
                if finish_reason == "length":
                    raise ValueError(f"AI 达到最大 token 限制，输出被截断。请增加 max_completion_tokens 参数")
                raise ValueError(f"AI 返回内容为空（finish_reason: {finish_reason}）")
            
            # 提取 JSON
            content = content.strip()
            if content.startswith("```json"):
                content = content.split("```json")[1].split("```")[0]
            elif content.startswith("```"):
                content = content.split("```")[1].split("```")[0]
            
            content = content.strip()
            logger.debug(f"Extracted JSON content: {content[:200]}")
            
            data = json.loads(content)
            
            return AIAnalysisResult(
                gpu_id=gpu_id,
                status=data["status"],
                confidence=float(data["confidence"]),
                reason=data["reason"],
                recommendation=data["recommendation"],
                raw_score=raw_score,
                ai_adjusted_score=float(data.get("adjusted_score", raw_score))
            )
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response: {e}")
            logger.error(f"Content to parse: {content if 'content' in locals() else 'N/A'}")
            # 返回默认结果
            return AIAnalysisResult(
                gpu_id=gpu_id,
                status="suspicious",
                confidence=0.0,
                reason="AI 响应 JSON 解析失败",
                recommendation="建议人工检查",
                raw_score=raw_score,
                ai_adjusted_score=None
            )
        except Exception as e:
            logger.error(f"Failed to parse AI response: {e}")
            logger.error(f"Response structure: {response if response else 'None'}")
            # 返回默认结果
            return AIAnalysisResult(
                gpu_id=gpu_id,
                status="suspicious",
                confidence=0.0,
                reason=f"AI 分析失败: {str(e)}",
                recommendation="建议人工检查",
                raw_score=raw_score,
                ai_adjusted_score=None
            )


# 创建全局 AI 分析器实例
ai_analyzer = AIAnalyzer()

