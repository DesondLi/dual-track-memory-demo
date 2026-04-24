"""
DualTrackOrchestrator - 双轨记忆协调器

整合：
- mem0：关键特征记忆库（实时提取，向量搜索）
- memU：客户档案中心（深度建档，洞察建议）
"""
import threading
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from mem0_module import VectorMemory, RuleBasedFeatureExtractor
from memu_module import StructuredMemory


class DualTrackOrchestrator:
    """
    双轨记忆协调器 - 电信客服场景

    工作流程：
    1. 每轮对话 → mem0 实时提取特征
    2. 累计 N 轮 → 触发 memU 异步构建完整档案
    3. 查询时：同时搜索两个轨道，融合结果
    """

    def __init__(
        self,
        base_dir: str,
        auto_trigger_profile: bool = True,
        trigger_threshold: int = 10,  # 每 10 轮对话触发一次建档
        user_id: str = "default",
    ):
        base_path = Path(base_dir)

        # 初始化两个记忆系统
        self.mem0 = VectorMemory(
            persist_directory=str(base_path / "mem0_features"),
        )
        self.memu = StructuredMemory(
            output_dir=str(base_path / "memu_profiles"),
        )

        # 配置
        self.auto_trigger_profile = auto_trigger_profile
        self.trigger_threshold = trigger_threshold
        self.default_user_id = user_id

        # 状态
        self._conversation_buffer: List[Dict[str, str]] = []
        self._feature_extractor = RuleBasedFeatureExtractor()
        self._total_features_extracted: int = 0
        self._last_profile_build: Optional[str] = None

        # 异步锁
        self._build_lock = threading.Lock()

    def add_message(
        self,
        role: str,
        content: str,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        添加一条对话消息，自动提取特征

        Returns:
            处理结果统计
        """
        actual_user_id = user_id or self.default_user_id

        # 添加到对话缓冲区
        self._conversation_buffer.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        })

        # 提取特征并写入 mem0
        features = self._feature_extractor.extract(content)
        new_features_count = 0

        for feat in features:
            self.mem0.add_feature(
                key=feat["key"],
                value=feat["value"],
                user_id=actual_user_id,
                confidence=feat["confidence"],
                source=feat["source"],
                category=feat["category"],
            )
            new_features_count += 1

        self._total_features_extracted += new_features_count

        # 检查是否触发建档
        profile_triggered = False
        if (self.auto_trigger_profile
            and len(self._conversation_buffer) >= self.trigger_threshold):
            # 异步触发建档
            self._trigger_profile_build(actual_user_id)
            profile_triggered = True
            self._conversation_buffer.clear()  # 清空缓冲区

        return {
            "features_extracted": new_features_count,
            "buffer_size": len(self._conversation_buffer),
            "profile_triggered": profile_triggered,
        }

    def _trigger_profile_build(self, user_id: str):
        """异步触发客户档案构建"""
        def build_task():
            with self._build_lock:
                # 从 mem0 获取所有特征
                features = self.mem0.get_all_features(user_id=user_id)
                # 构建档案
                profile = self.memu.build_profile_from_features(
                    features=features,
                    user_id=user_id,
                )
                self._last_profile_build = datetime.now().isoformat()

        thread = threading.Thread(target=build_task, daemon=True)
        thread.start()

    def force_build_profile(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        强制立即构建客户档案（同步执行）

        Returns:
            建档结果
        """
        actual_user_id = user_id or self.default_user_id

        features = self.mem0.get_all_features(user_id=actual_user_id)
        profile = self.memu.build_profile_from_features(
            features=features,
            user_id=actual_user_id,
        )
        self._last_profile_build = datetime.now().isoformat()
        self._conversation_buffer.clear()

        return {
            "user_id": actual_user_id,
            "features_used": len(features),
            "profile_updated": True,
        }

    def search(
        self,
        query: str,
        user_id: Optional[str] = None,
        top_k: int = 5,
    ) -> Dict[str, Any]:
        """
        双轨融合搜索

        Returns:
            融合后的搜索结果
        """
        actual_user_id = user_id or self.default_user_id

        # 同时搜索两个轨道
        mem0_results = self.mem0.search(
            query=query,
            user_id=actual_user_id,
            top_k=top_k,
        )
        memu_results = self.memu.search_profiles(
            query=query,
            top_k=top_k,
        )

        # 融合结果
        all_results = mem0_results + memu_results
        all_results.sort(key=lambda x: x["similarity"], reverse=True)

        return {
            "query": query,
            "total_results": len(all_results),
            "mem0_count": len(mem0_results),
            "memu_count": len(memu_results),
            "mem0_results": mem0_results,
            "memu_results": memu_results,
            "combined_results": all_results[:top_k],
        }

    def get_profile(self, user_id: Optional[str] = None) -> Optional[Any]:
        """获取客户档案"""
        return self.memu.get_profile(user_id or self.default_user_id)

    def get_profile_markdown(self, user_id: Optional[str] = None) -> Optional[str]:
        """获取客户档案的 Markdown 内容"""
        return self.memu.get_profile_markdown(user_id or self.default_user_id)

    def get_context_for_llm(self, query: str, user_id: Optional[str] = None) -> str:
        """
        生成适合传给 LLM 的上下文

        Returns:
            格式化的上下文字符串
        """
        actual_user_id = user_id or self.default_user_id

        context_parts = []

        # 1. 从 mem0 获取相关特征
        mem0_results = self.mem0.search(query, user_id=actual_user_id, top_k=8)
        if mem0_results:
            context_parts.append("=== 关键特征记忆 ===\n")
            for r in mem0_results:
                context_parts.append(
                    f"- [{r.get('category', '其他')}] {r['key']}: {r.get('value', '')}\n"
                )
            context_parts.append("\n")

        # 2. 从 memU 获取客户档案摘要
        profile = self.memu.get_profile(actual_user_id)
        if profile:
            context_parts.append("=== 客户档案摘要 ===\n")
            # 只取风险标签和建议部分
            if profile.risk_tags.items:
                context_parts.append("【风险标签】\n")
                for item in profile.risk_tags.items[:3]:
                    context_parts.append(f"- {item}\n")
            if profile.user_preferences.items:
                context_parts.append("\n【用户偏好】\n")
                for item in profile.user_preferences.items[:3]:
                    context_parts.append(f"- {item}\n")
            if profile.recommendations:
                context_parts.append("\n【跟进建议】\n")
                for rec in profile.recommendations[:3]:
                    context_parts.append(f"- {rec}\n")

        return "".join(context_parts)

    def get_stats(self) -> Dict[str, Any]:
        """获取系统统计信息"""
        return {
            "mem0": {
                "total_features": self.mem0.count(),
            },
            "memu": {
                "total_profiles": len(self.memu.get_all_profiles()),
                "last_build_time": self._last_profile_build,
            },
            "buffer": {
                "pending_conversations": len(self._conversation_buffer),
                "trigger_threshold": self.trigger_threshold,
                "trigger_progress": f"{len(self._conversation_buffer)}/{self.trigger_threshold}",
            },
            "orchestrator": {
                "total_features_extracted": self._total_features_extracted,
                "auto_trigger_enabled": self.auto_trigger_profile,
            },
        }

    def clear_all(self) -> Dict[str, int]:
        """清空所有记忆"""
        mem0_cleared = self.mem0.clear()
        memu_cleared = self.memu.clear()
        self._conversation_buffer.clear()

        return {
            "mem0_cleared": mem0_cleared,
            "memu_cleared": memu_cleared,
            "buffer_cleared": True,
        }

    # -------- 辅助方法：电信客服预设特征 --------
    def add_telecom_feature(
        self,
        category: str,
        key: str,
        value: str,
        user_id: Optional[str] = None,
        source: str = "",
        confidence: float = 1.0,
    ):
        """添加电信客服专用特征"""
        self.mem0.add_feature(
            key=key,
            value=value,
            user_id=user_id or self.default_user_id,
            category=category,
            source=source,
            confidence=confidence,
        )
