"""
memU - 客户档案中心

从 mem0 的特征点出发，构建完整的 360° 用户画像
分类归档，深度分析，生成业务洞察和建议
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict, field


@dataclass
class ProfileSection:
    """档案章节"""
    name: str           # 章节名称
    icon: str           # 图标 emoji
    content: str        # 内容描述
    items: List[str] = field(default_factory=list)    # 要点列表
    summary: str = ""   # 章节摘要

    def to_dict(self) -> Dict:
        return asdict(self)


class CustomerProfile:
    """完整的客户档案"""

    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at
        self.overall_summary = ""

        # 五大档案章节
        self.basic_info: ProfileSection = ProfileSection(
            name="基本信息",
            icon="📋",
            content="用户的基础资料与在网情况",
            items=[],
        )
        self.complaint_history: ProfileSection = ProfileSection(
            name="投诉记录",
            icon="⚠️",
            content="用户的投诉历史、问题类型与处理状态",
            items=[],
        )
        self.business_intent: ProfileSection = ProfileSection(
            name="业务意向",
            icon="💼",
            content="用户潜在的业务办理与变更需求",
            items=[],
        )
        self.user_preferences: ProfileSection = ProfileSection(
            name="用户偏好",
            icon="❤️",
            content="用户的服务偏好与敏感点",
            items=[],
        )
        self.risk_tags: ProfileSection = ProfileSection(
            name="风险标签",
            icon="🚨",
            content="用户的风险等级与预警标签",
            items=[],
        )

        # 业务洞察和建议
        self.insights: List[str] = []
        self.recommendations: List[str] = []

    def add_item(self, category: str, item: str):
        """添加条目到对应章节"""
        section_map = {
            "基本信息": self.basic_info,
            "投诉记录": self.complaint_history,
            "业务意向": self.business_intent,
            "用户偏好": self.user_preferences,
            "风险标签": self.risk_tags,
        }
        section = section_map.get(category)
        if section and item not in section.items:
            section.items.append(item)
            self.updated_at = datetime.now().isoformat()

    def add_insight(self, insight: str):
        """添加业务洞察"""
        if insight not in self.insights:
            self.insights.append(insight)
            self.updated_at = datetime.now().isoformat()

    def add_recommendation(self, recommendation: str):
        """添加跟进建议"""
        if recommendation not in self.recommendations:
            self.recommendations.append(recommendation)
            self.updated_at = datetime.now().isoformat()

    # ---- 特征值语义扩展 ----
    # 将原始 key:value 扩展为包含业务解读的描述

    _VALUE_EXPANSIONS = {
        "手机号": lambda v: f"`{v}`" if v else "",
        "套餐类型": lambda v: f"{v}（建议关注套餐到期时间与续约优惠）" if v else "",
        "所在地区": lambda v: f"{v}（影响网络覆盖与服务响应速度）" if v else "",
        "客户姓名": lambda v: v if v else "",
        "投诉类型": lambda v: f"{v}（需核实处理进度与用户满意度）" if v else "",
        "网络问题": lambda v: f"**{v}** — 建议安排工程师上门检测线路与信号覆盖" if v else "",
        "费用问题": lambda v: f"**{v}** — 建议核查扣费明细，确认是否为增值业务误开" if v else "",
        "增值业务问题": lambda v: f"**{v}** — 高风险项，需立即核查开通渠道并设置业务确认锁" if v else "",
        "套餐升级意向": lambda v: f"用户有套餐升级意向（{v}），可推荐千兆融合套餐" if v else "",
        "副卡办理意向": lambda v: f"用户有副卡需求（{v}），可推荐家庭共享方案" if v else "",
        "携号转网意向": lambda v: f"⚠️ 用户有携号转网意向（{v}），需启动挽留流程" if v else "",
        "拆机意向": lambda v: f"⚠️ 用户有拆机意向（{v}），需启动挽留流程" if v else "",
        "联系偏好": lambda v: f"用户明确要求**{v}**，禁止营销电话外呼" if v else "",
        "会员偏好": lambda v: f"用户偏好{v}，套餐搭配时可优先匹配对应会员权益" if v else "",
        "越级投诉风险": lambda v: f"🔴 **高危** — 用户有越级投诉倾向（{v}），须按升级投诉流程处理" if v else "",
        "流失风险": lambda v: f"🔴 **高危** — 用户有流失倾向（{v}），须在48小时内主动回访" if v else "",
        "重复投诉": lambda v: f"🟡 用户反复投诉（{v}），属于高关注客户，须专人跟进" if v else "",
    }

    def _expand_feature(self, key: str, value: str) -> str:
        """将特征值扩展为业务语义描述"""
        expander = self._VALUE_EXPANSIONS.get(key)
        if expander:
            expanded = expander(value)
            return expanded if expanded else value
        return value

    def _generate_overall_summary(self):
        """生成档案总览摘要"""
        parts = []
        # 基本信息
        phone_items = [i for i in self.basic_info.items if "手机号" in i]
        plan_items = [i for i in self.basic_info.items if "套餐" in i]
        area_items = [i for i in self.basic_info.items if "地区" in i or "地址" in i]

        if phone_items or plan_items:
            info = "、".join(
                p for p in [phone_items[0] if phone_items else "",
                            plan_items[0] if plan_items else "",
                            area_items[0] if area_items else ""]
                if p
            )
            parts.append(f"用户{info}")

        # 投诉情况
        n_complaints = len(self.complaint_history.items)
        if n_complaints > 0:
            parts.append(f"存在{n_complaints}项投诉记录")

        # 风险
        risk_text = " ".join(self.risk_tags.items)
        if "越级" in risk_text or "高危" in risk_text:
            parts.append("有越级投诉风险")
        if "流失" in risk_text or "转网" in risk_text:
            parts.append("有流失风险")
        if "重复" in risk_text or "多次" in risk_text:
            parts.append("属重复投诉客户")

        # 意向
        if self.business_intent.items:
            parts.append(f"有{len(self.business_intent.items)}项业务意向待跟进")

        if parts:
            self.overall_summary = "，".join(parts) + "。"
        else:
            self.overall_summary = "暂无明显风险特征，按常规流程服务。"

    def _generate_section_summaries(self):
        """为每个章节生成摘要"""
        # 投诉记录摘要
        if self.complaint_history.items:
            types = []
            for item in self.complaint_history.items:
                if "网络" in item:
                    types.append("网络")
                elif "费用" in item or "扣费" in item:
                    types.append("费用")
                elif "增值" in item:
                    types.append("增值业务")
                else:
                    types.append("其他")
            self.complaint_history.summary = f"共{len(self.complaint_history.items)}项投诉，涉及：{'、'.join(types)}"

        # 风险标签摘要
        if self.risk_tags.items:
            level = "高" if any("高危" in i or "🔴" in i for i in self.risk_tags.items) else "中"
            self.risk_tags.summary = f"风险等级：**{level}**，共{len(self.risk_tags.items)}个风险标签"

        # 业务意向摘要
        if self.business_intent.items:
            self.business_intent.summary = f"共{len(self.business_intent.items)}项业务意向待跟进"

    def generate_rule_based_suggestions(self):
        """基于规则自动生成洞察和建议（含交叉分析）"""
        # 先生成章节摘要
        self._generate_section_summaries()
        self._generate_overall_summary()

        # --- 洞察生成 ---
        self.insights = []

        # 投诉相关洞察
        n_complaints = len(self.complaint_history.items)
        if n_complaints >= 3:
            self.insights.append(
                f"用户累计{n_complaints}项投诉记录，属于**高关注客户**，任何新投诉须24小时内响应"
            )
        elif n_complaints >= 1:
            self.insights.append(
                f"用户有{n_complaints}项投诉记录，需关注处理满意度，避免问题升级"
            )

        # 风险标签洞察
        risk_items = " ".join(self.risk_tags.items)
        complaint_items = " ".join(self.complaint_history.items)
        pref_items = " ".join(self.user_preferences.items)
        intent_items = " ".join(self.business_intent.items)

        if "越级" in risk_items or "12345" in risk_items:
            self.insights.append(
                "用户有越级投诉倾向（工信部/12345），属于**高危投诉用户**，"
                "须按升级投诉流程处理，所有承诺必须书面确认"
            )
        if "流失" in risk_items or "转网" in intent_items:
            self.insights.append(
                "用户有流失/携号转网倾向，属于**挽留重点对象**，"
                "建议客户经理48小时内主动联系，提供专属优惠"
            )

        # 交叉洞察：增值业务投诉 + 重复投诉
        if ("增值业务" in complaint_items or "扣费" in complaint_items) and ("重复" in risk_items or "多次" in risk_items):
            self.insights.append(
                "用户多次遭遇增值业务误开扣费，**极度敏感**，"
                "严禁未经短信确认开通任何业务，已开通的须逐一核查"
            )
        elif "增值业务" in complaint_items or "扣费" in complaint_items:
            self.insights.append(
                "用户对增值业务扣费敏感，任何业务开通须先短信确认"
            )

        # 交叉洞察：套餐升级意向 + 费用敏感
        if "升级" in intent_items and ("多扣" in complaint_items or "扣费" in complaint_items or "收费" in complaint_items):
            self.insights.append(
                "用户有套餐升级意向但同时对费用敏感，推荐套餐时须**突出性价比**，"
                "强调升级带来的实际权益而非单纯涨价"
            )

        # 交叉洞察：投诉 + 携号转网
        if n_complaints > 0 and ("转网" in intent_items or "流失" in risk_items):
            self.insights.append(
                "投诉未妥善解决是用户考虑转网的主要原因，须优先解决现有投诉后再谈挽留"
            )

        # --- 建议生成 ---
        self.recommendations = []

        # 联系偏好建议
        if "短信" in pref_items or "不要打电话" in pref_items:
            self.recommendations.append("📞 **联系偏好**：只通过短信联系，禁止营销电话外呼，已设置营销电话屏蔽")

        # 流失用户建议
        if "流失" in risk_items or "转网" in intent_items:
            self.recommendations.append("🔄 **挽留流程**：客户经理3个工作日内主动回访，提供专属优惠（如减免10元/月×6个月）")
            self.recommendations.append("🎁 **政策支持**：优先推荐千兆套餐+会员权益，用升级替代转网")

        # 增值业务建议
        if "增值业务" in complaint_items:
            self.recommendations.append("🔒 **业务安全锁**：开通业务确认锁，所有增值业务开通须用户短信二次确认")
            self.recommendations.append("💰 **费用核查**：逐一核查已开通增值业务，非主动开通的立即取消并双倍返还")

        # 网络问题建议
        if "网络" in complaint_items or "掉线" in complaint_items or "信号" in complaint_items:
            self.recommendations.append("🔧 **网络修复**：安排工程师上门检测，优先处理；如为区域覆盖问题，登记5G优化计划并告知预计完工时间")

        # 投诉处理建议
        if n_complaints > 0:
            self.recommendations.append("📝 **投诉处理**：首问负责制，全程跟进至用户确认满意；超时主动反馈进度")
            self.recommendations.append("⏰ **时效承诺**：普通投诉48小时响应，高危投诉24小时响应，明确告知处理时限")

        # 副卡办理建议
        if "副卡" in intent_items:
            self.recommendations.append("📱 **副卡办理**：可推荐5元/月副卡（首3月免费），共享主卡通话流量，适合老人使用")

        # 如果没有洞察/建议，添加默认提示
        if not self.insights:
            self.insights.append("暂无明显风险特征，继续保持常规服务")
        if not self.recommendations:
            self.recommendations.append("按标准服务流程处理即可")

    def to_markdown(self) -> str:
        """生成 Markdown 格式的完整档案"""
        lines = []

        # 标题
        lines.append("# 👤 客户档案")
        lines.append("")
        lines.append(f"> 用户标识：`{self.user_id}`")
        lines.append(f"> 档案更新：{self.updated_at[:19]}")
        lines.append("")

        # 总览摘要
        if self.overall_summary:
            lines.append("## 📊 档案总览")
            lines.append("")
            lines.append(self.overall_summary)
            lines.append("")

        # 各个章节
        sections = [
            self.basic_info,
            self.complaint_history,
            self.business_intent,
            self.user_preferences,
            self.risk_tags,
        ]

        for section in sections:
            if section.items:
                lines.append(f"## {section.icon} {section.name}")
                lines.append("")
                if section.summary:
                    lines.append(f"> {section.summary}")
                    lines.append("")
                elif section.content:
                    lines.append(f"> {section.content}")
                    lines.append("")
                for item in section.items:
                    lines.append(f"- {item}")
                lines.append("")

        # 业务洞察
        if self.insights:
            lines.append("## 💡 业务洞察")
            lines.append("")
            for insight in self.insights:
                lines.append(f"- {insight}")
            lines.append("")

        # 跟进建议
        if self.recommendations:
            lines.append("## 📌 跟进建议")
            lines.append("")
            for rec in self.recommendations:
                lines.append(f"- {rec}")
            lines.append("")

        return "\n".join(lines)

    def to_dict(self) -> Dict:
        return {
            "user_id": self.user_id,
            "updated_at": self.updated_at,
            "overall_summary": self.overall_summary,
            "basic_info": self.basic_info.to_dict(),
            "complaint_history": self.complaint_history.to_dict(),
            "business_intent": self.business_intent.to_dict(),
            "user_preferences": self.user_preferences.to_dict(),
            "risk_tags": self.risk_tags.to_dict(),
            "insights": self.insights,
            "recommendations": self.recommendations,
        }


class StructuredMemory:
    """
    memU 客户档案中心

    从 mem0 的特征出发，构建完整的客户档案
    """

    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 内存中的档案缓存
        self._profile_cache: Dict[str, CustomerProfile] = {}
        self._load_existing_profiles()

    def _load_existing_profiles(self):
        """加载已存在的档案文件（简化版：只记录存在，不做复杂解析）"""
        for md_file in self.output_dir.glob("profile_*.md"):
            filename = md_file.stem.replace("profile_", "")
            # 简单创建对象，标记档案存在
            profile = CustomerProfile(user_id=filename)
            # 至少添加一个标记项，确保搜索能匹配到
            profile.add_item("基本信息", f"用户ID: {filename}")
            self._profile_cache[filename] = profile

    def build_profile_from_features(
        self,
        features: List[Any],  # List[FeatureItem]
        user_id: str = "default",
    ) -> CustomerProfile:
        """
        从特征列表构建客户档案

        Args:
            features: mem0 中的特征列表
            user_id: 用户标识
        """
        profile = CustomerProfile(user_id=user_id)

        # 将特征按分类归档，并做语义扩展
        for feat in features:
            category = getattr(feat, "category", "其他")
            key = getattr(feat, "key", "")
            value = getattr(feat, "value", "")

            # 语义扩展：将 key:value 转为业务描述
            expanded = profile._expand_feature(key, value)
            item = f"**{key}**：{expanded}" if expanded else f"**{key}**"
            profile.add_item(category, item)

        # 基于规则生成洞察和建议
        profile.generate_rule_based_suggestions()

        # 保存到文件
        self._save_profile(profile)

        return profile

    def _save_profile(self, profile: CustomerProfile):
        """保存档案到 Markdown 文件"""
        filepath = self.output_dir / f"profile_{profile.user_id}.md"
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(profile.to_markdown())

        # 更新缓存
        self._profile_cache[profile.user_id] = profile

    def get_profile(self, user_id: str = "default") -> Optional[CustomerProfile]:
        """获取用户档案"""
        return self._profile_cache.get(user_id)

    def get_profile_markdown(self, user_id: str = "default") -> Optional[str]:
        """获取用户档案的 Markdown 内容"""
        profile = self.get_profile(user_id)
        return profile.to_markdown() if profile else None

    def search_profiles(self, query: str, top_k: int = 3) -> List[Dict]:
        """
        搜索档案 - 宽松匹配，有档案就返回相关性结果

        Returns:
            匹配的档案列表
        """
        results = []
        query_lower = query.lower()

        # 关键词扩展（增加匹配概率）
        query_keywords = set(query_lower.split())
        # 常见同义词映射
        keyword_map = {
            "投诉": ["投诉", "问题", "不满", "故障"],
            "风险": ["风险", "流失", "转网", "高危", "越级"],
            "套餐": ["套餐", "业务", "办理", "升级"],
            "偏好": ["偏好", "联系", "短信", "电话"],
        }
        for kw, synonyms in keyword_map.items():
            if kw in query_lower:
                query_keywords.update(synonyms)

        for user_id, profile in self._profile_cache.items():
            md_content = profile.to_markdown().lower()

            # 计算匹配得分
            matched_keywords = sum(1 for kw in query_keywords if kw in md_content)
            if matched_keywords > 0 or len(self._profile_cache) > 0:
                # 有关键词匹配给高分，有档案但没匹配给基础分
                score = min(matched_keywords * 0.2, 0.9) if matched_keywords > 0 else 0.3
                results.append({
                    "user_id": user_id,
                    "content_preview": profile.to_markdown()[:200] + "...",
                    "similarity": score,
                    "source": "memU",
                })

        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:top_k]

    def get_all_profiles(self) -> List[str]:
        """获取所有用户 ID 列表"""
        return list(self._profile_cache.keys())

    def clear(self) -> int:
        """清空所有档案"""
        count = len(self._profile_cache)
        for md_file in self.output_dir.glob("profile_*.md"):
            md_file.unlink()
        self._profile_cache.clear()
        return count
