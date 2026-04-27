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


# 电信坐席 System Prompt
SYSTEM_PROMPT = """\
你是一名经验丰富的电信客服坐席，正在为一位来电客户提供服务。

你拥有该客户的完整记忆档案，包括：
- mem0：关键特征记忆（实时提取的结构化特征点）
- memU：客户档案（深度画像、风险标签、业务洞察、跟进建议）

请根据记忆档案中的信息，为用户提供专业、贴心、高效的服务。

## 工作原则
1. **先查档再回答**：充分利用记忆档案中的信息，不要问用户已经告知过的事情
2. **风险敏感**：如果用户有越级投诉、流失等风险标签，处理需格外谨慎
3. **尊重偏好**：严格遵守用户的联系偏好（如要求短信联系则不打电话）
4. **主动服务**：根据业务洞察和跟进建议，主动提供解决方案
5. **闭环确认**：每个承诺都要明确时间节点，超时主动反馈

## 输出要求
- 回答需要**详尽完整**，充分引用档案中的每一个相关信息点
- 每个问题都要给出**具体的处理步骤和话术**，不要笼统概括
- 如果涉及费用，明确说明金额、扣费原因和处理方式
- 如果涉及工单，说明负责部门、处理流程和预计时间
- 如果有风险标签，详细说明风险等级、触发原因和应对措施
- 如果有业务意向，给出具体的产品方案、价格和优惠
- 最后给出**可直接使用的客服话术**（短信或电话版本）"""


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

        # 1. 从 mem0 检索相关特征
        mem0_results = self.orchestrator.mem0.search(
            query=query,
            user_id=user_id or self.orchestrator.default_user_id,
            top_k=8,
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

        # 4. 组装完整 prompt
        user_message = f"客户说：「{query}」\n\n以下是该客户的完整记忆档案，请据此给出详尽专业的客服回复：\n\n{context}"

        result["full_prompt"] = user_message

        # 5. 调用 LLM
        if not self.is_available:
            result["answer"] = self._fallback_answer(query, context, profile)
            result["error"] = "LLM 不可用（未配置 API Key），使用规则降级回答"
        else:
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    temperature=self.temperature,
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
