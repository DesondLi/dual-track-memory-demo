"""
TelecomAgent - 电信客服智能坐席

消费 mem0 + memU 双轨记忆，生成上下文感知的客服回答
完整闭环：用户提问 → 双轨检索 → 上下文组装 → LLM 推理 → 结构化回答
"""
import os
import re
from typing import Dict, Any, Optional
from openai import OpenAI

# 导入默认配置
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import LLM_CONFIG


# 电信坐席 System Prompt - 精简版（更快）
SYSTEM_PROMPT = """\
你是一名电信客服坐席，根据客户记忆档案回答问题。

输出要求：
- 专业、简洁、高效
- 基于档案信息，不要编造
- 给出具体处理建议和话术"""


class TelecomAgent:
    """电信客服智能坐席 Agent"""

    @staticmethod
    def _clean_llm_output(text: str) -> str:
        """清理 LLM 输出中的思考过程标签"""
        # 移除 <think>...</think> 块（含换行）
        text = re.sub(r'<think>.*?</think>\s*', '', text, flags=re.DOTALL)
        # 移除残留的 <think> 开标签（未闭合）
        text = re.sub(r'<think>\s*$', '', text, flags=re.MULTILINE)
        # 移除 &#8203; 零宽字符
        text = text.replace('​', '')
        return text.strip()

    def __init__(
        self,
        orchestrator: Any,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
    ):
        self.orchestrator = orchestrator
        # 使用 config.py 中的默认配置，环境变量和传入参数可覆盖
        self.model = model or os.getenv("AIHUBMIX_MODEL", os.getenv("OPENAI_MODEL", LLM_CONFIG["chat_model"]))
        self.temperature = temperature

        # 初始化 LLM 客户端（优先传入参数，其次环境变量，最后使用 config.py 默认配置）
        key = api_key or os.getenv("AIHUBMIX_API_KEY", os.getenv("OPENAI_API_KEY", LLM_CONFIG["api_key"]))
        base = api_base or os.getenv("AIHUBMIX_API_BASE", os.getenv("OPENAI_API_BASE", LLM_CONFIG["api_base"]))

        if not key:
            self.client = None
            self.init_error = "API Key 为空"
        else:
            try:
                import httpx
                # Streamlit Cloud 可能有网络限制，增加超时和自定义客户端
                http_client = httpx.Client(timeout=60.0, follow_redirects=True)
                self.client = OpenAI(
                    api_key=key,
                    base_url=base,
                    timeout=60.0,
                    max_retries=3,
                    http_client=http_client,
                )
                # 简单测试连接（只列模型，不做完整验证）
                self.client.models.list()
                self.init_error = None
            except Exception as e:
                self.client = None
                self.init_error = f"{type(e).__name__}: {str(e)}"

    @property
    def is_available(self) -> bool:
        """LLM 是否可用"""
        return self.client is not None

    @property
    def error_message(self) -> str:
        """获取初始化错误信息"""
        return getattr(self, 'init_error', None)

    def answer(
        self,
        query: str,
        user_id: Optional[str] = None,
        show_context: bool = False,
    ) -> Dict[str, Any]:
        """
        基于双轨记忆回答用户问题

        Args:
            query: 用户问题
            user_id: 用户标识
            show_context: 是否返回中间上下文（用于 demo 展示）

        Returns:
            包含回答和中间过程的字典
        """
        result = {
            "query": query,
            "context_mem0": [],
            "context_memu": "",
            "full_prompt": "",
            "answer": "",
            "error": None,
        }

        # 1. 从 mem0 检索相关特征（减少返回数量，加快速度）
        mem0_results = self.orchestrator.mem0.search(
            query=query,
            user_id=user_id or self.orchestrator.default_user_id,
            top_k=5,  # 从8减少到5，加快速度
        )
        result["context_mem0"] = [
            {
                "key": r.get("key", ""),
                "value": r.get("value", ""),
                "category": r.get("category", "其他"),
                "similarity": r.get("similarity", 0),
            }
            for r in mem0_results
        ]

        # 2. 从 memU 获取客户档案
        profile = self.orchestrator.get_profile(user_id)
        if profile:
            result["context_memu"] = profile.to_markdown()

        # 3. 组装上下文（传完整档案给 LLM，不只是摘要）
        context_parts = []

        # mem0 特征
        if result["context_mem0"]:
            context_parts.append("=== mem0 关键特征 ===")
            for feat in result["context_mem0"]:
                context_parts.append(f"- [{feat['category']}] {feat['key']}: {feat['value']}")
            context_parts.append("")

        # memU 完整档案
        if result["context_memu"]:
            context_parts.append("=== memU 客户档案 ===")
            context_parts.append(result["context_memu"])

        context = "\n".join(context_parts)

        # 4. 组装精简 prompt（加快速度）
        user_message = f"客户问题：{query}\n\n客户档案：\n{context}"

        result["full_prompt"] = user_message

        # 5. 调用 LLM（优化参数）
        if not self.is_available:
            result["answer"] = self._fallback_answer(query, context, profile)
            result["error"] = "LLM 不可用（未配置 API Key），使用规则降级回答"
        else:
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    temperature=0.6,  # 降低温度，加快输出
                    max_tokens=1000,  # 限制最大token数
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_message},
                    ],
                )
                result["answer"] = self._clean_llm_output(response.choices[0].message.content)
            except Exception as e:
                result["answer"] = self._fallback_answer(query, context, profile)
                result["error"] = f"LLM 调用失败: {e}"

        return result

    def answer_stream(
        self,
        query: str,
        user_id: Optional[str] = None,
    ):
        """流式回答生成器 - 更快显示结果"""
        if not self.is_available:
            yield self._fallback_answer(query, "", self.orchestrator.get_profile(user_id))
            return

        # 快速版本：简化上下文组装
        mem0_results = self.orchestrator.mem0.search(
            query=query,
            user_id=user_id or self.orchestrator.default_user_id,
            top_k=3,
        )
        profile = self.orchestrator.get_profile(user_id)

        # 极简上下文
        context_parts = []
        for feat in mem0_results[:3]:
            context_parts.append(f"- {feat.get('key', '')}: {feat.get('value', '')}")
        if profile:
            context_parts.append(f"- 风险: {', '.join(profile.risk_tags.items[:2])}")
            context_parts.append(f"- 建议: {', '.join(profile.recommendations[:2])}")

        context = "\n".join(context_parts)
        user_message = f"客户问题：{query}\n\n关键信息：\n{context}"

        try:
            stream = self.client.chat.completions.create(
                model=self.model,
                temperature=0.6,
                max_tokens=800,
                stream=True,
                messages=[
                    {"role": "system", "content": "你是电信客服，简洁专业回答问题。"},
                    {"role": "user", "content": user_message},
                ],
            )
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception:
            yield "（连接超时，请稍后重试）"

    def _fallback_answer(
        self,
        query: str,
        context: str,
        profile: Any,
    ) -> str:
        """无 LLM 时的规则降级回答"""
        lines = []
        lines.append("根据客户档案信息，为您生成以下服务建议：")
        lines.append("")

        # 根据查询意图给出不同回答
        query_lower = query.lower()

        if any(kw in query for kw in ["投诉", "问题", "不满"]):
            if profile and profile.complaint_history.items:
                lines.append("**投诉处理建议：**")
                if profile.insights:
                    for insight in profile.insights[:3]:
                        lines.append(f"- {insight}")
                if profile.recommendations:
                    for rec in profile.recommendations[:3]:
                        lines.append(f"- {rec}")

        elif any(kw in query for kw in ["套餐", "升级", "办理", "业务"]):
            if profile and profile.business_intent.items:
                lines.append("**业务办理建议：**")
                for item in profile.business_intent.items:
                    lines.append(f"- {item}")
                lines.append("")
                lines.append("根据用户偏好，推荐方案时需注意性价比。")

        elif any(kw in query for kw in ["风险", "流失", "转网", "越级"]):
            if profile and profile.risk_tags.items:
                lines.append("**风险评估：**")
                for item in profile.risk_tags.items:
                    lines.append(f"- {item}")
                if profile.insights:
                    lines.append("")
                    lines.append("**风险洞察：**")
                    for insight in profile.insights:
                        lines.append(f"- {insight}")

        elif any(kw in query for kw in ["偏好", "联系", "习惯"]):
            if profile and profile.user_preferences.items:
                lines.append("**用户偏好信息：**")
                for item in profile.user_preferences.items:
                    lines.append(f"- {item}")

        else:
            # 通用回答：基于档案摘要
            if profile:
                if profile.overall_summary:
                    lines.append(f"**客户概况：** {profile.overall_summary}")
                if profile.risk_tags.items:
                    lines.append("")
                    lines.append("**风险标签：**")
                    for item in profile.risk_tags.items:
                        lines.append(f"- {item}")
                if profile.recommendations:
                    lines.append("")
                    lines.append("**跟进建议：**")
                    for rec in profile.recommendations[:5]:
                        lines.append(f"- {rec}")
            else:
                lines.append("暂无客户档案，请先构建客户档案。")

        return "\n".join(lines)
