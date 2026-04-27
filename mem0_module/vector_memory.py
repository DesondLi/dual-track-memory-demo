"""
mem0 - 关键特征记忆库（Key-Value 特征存储）

从对话中实时提取结构化特征点，以键值对形式存储
支持向量语义搜索，快速查找用户特征
"""
import json
import re
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any
import chromadb
from chromadb.config import Settings


class FeatureItem:
    """特征条目 - 结构化的键值对"""

    def __init__(
        self,
        key: str,           # 特征键（如："手机号"、"投诉类型"）
        value: str,         # 特征值
        user_id: str = "default",
        confidence: float = 1.0,  # 置信度 0-1
        source: str = "",   # 来源（对话原文片段）
        category: str = "其他",  # 分类：基本信息、投诉记录、业务意向、用户偏好、风险标签
        feature_id: Optional[str] = None,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
    ):
        self.feature_id = feature_id or self._generate_id(key, user_id)
        self.key = key
        self.value = value
        self.user_id = user_id
        self.confidence = confidence
        self.source = source
        self.category = category
        self.created_at = created_at or datetime.now().isoformat()
        self.updated_at = updated_at or datetime.now().isoformat()

    @staticmethod
    def _generate_id(key: str, user_id: str) -> str:
        """根据 key 和 user_id 生成唯一 ID"""
        return "feat_" + hashlib.md5(f"{key}_{user_id}".encode()).hexdigest()[:10]

    def to_dict(self) -> Dict:
        return {
            "feature_id": self.feature_id,
            "key": self.key,
            "value": self.value,
            "user_id": self.user_id,
            "confidence": self.confidence,
            "source": self.source,
            "category": self.category,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def to_search_text(self) -> str:
        """生成用于向量化的搜索文本"""
        return f"{self.category} {self.key} {self.value} {self.source}"

    @classmethod
    def from_dict(cls, data: Dict) -> "FeatureItem":
        return cls(**data)

    def __repr__(self) -> str:
        return f"FeatureItem({self.key}={self.value}, conf={self.confidence:.2f})"


class VectorMemory:
    """
    mem0 关键特征记忆库

    特点：
    - 存储结构化特征（键值对），不是原始对话
    - 自动分类（基本信息、投诉记录、业务意向、用户偏好、风险标签）
    - 向量语义搜索，快速查找相关特征
    - 置信度管理，支持覆盖更新
    """

    # 预设分类
    CATEGORIES = [
        "基本信息",   # 手机号、套餐、姓名、地址等
        "投诉记录",   # 投诉类型、次数、历史
        "业务意向",   # 办理/升级/拆机等意向
        "用户偏好",   # 联系方式偏好、会员偏好等
        "风险标签",   # 流失风险、投诉风险等
        "其他",
    ]

    def __init__(
        self,
        persist_directory: str,
        collection_name: str = "mem0_features",
    ):
        self.persist_directory = Path(persist_directory)
        self.collection_name = collection_name

        # 初始化 ChromaDB
        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=Settings(anonymized_telemetry=False),
        )
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"description": "mem0 key-value feature memory"},
        )

    def add_feature(
        self,
        key: str,
        value: str,
        user_id: str = "default",
        confidence: float = 1.0,
        source: str = "",
        category: str = "其他",
    ) -> FeatureItem:
        """
        添加/更新一个特征

        如果该 key 已存在，则更新 value 并提高置信度
        """
        # 检查是否已存在
        existing = self.get_feature(key, user_id)

        if existing:
            # 更新现有特征
            existing.value = value
            existing.confidence = min(existing.confidence + 0.1, 1.0)  # 置信度累加
            existing.source = source if source else existing.source
            existing.updated_at = datetime.now().isoformat()
            feature = existing
        else:
            # 创建新特征
            feature = FeatureItem(
                key=key,
                value=value,
                user_id=user_id,
                confidence=confidence,
                source=source,
                category=category,
            )

        # 向量化文本
        search_text = feature.to_search_text()

        # 元数据（Chroma 只支持简单类型）
        meta = {
            "user_id": user_id,
            "key": key,
            "value": value,  # 修复：存储 value 到 meta
            "category": category,
            "confidence": confidence,
            "updated_at": feature.updated_at,
        }

        # 写入向量库
        self.collection.upsert(
            ids=[feature.feature_id],
            documents=[search_text],
            metadatas=[meta],
        )

        return feature

    def add_features_batch(
        self,
        features: List[Dict[str, Any]],
        user_id: str = "default",
    ) -> List[FeatureItem]:
        """批量添加特征"""
        results = []
        for feat in features:
            item = self.add_feature(
                key=feat["key"],
                value=feat["value"],
                user_id=user_id,
                confidence=feat.get("confidence", 1.0),
                source=feat.get("source", ""),
                category=feat.get("category", "其他"),
            )
            results.append(item)
        return results

    def get_feature(self, key: str, user_id: str = "default") -> Optional[FeatureItem]:
        """获取指定 key 的特征"""
        feature_id = FeatureItem._generate_id(key, user_id)
        try:
            result = self.collection.get(ids=[feature_id])
            if result and result["ids"]:
                meta = result["metadatas"][0]
                return FeatureItem(
                    feature_id=result["ids"][0],
                    key=meta["key"],
                    value=meta.get("value", ""),  # value 不在 meta 里需要特殊处理
                    user_id=meta["user_id"],
                    confidence=meta.get("confidence", 1.0),
                    category=meta.get("category", "其他"),
                    updated_at=meta.get("updated_at"),
                )
        except Exception:
            pass
        return None

    def search(
        self,
        query: str,
        user_id: Optional[str] = None,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        混合搜索：精确关键词匹配优先，向量语义相似度次之

        Returns:
            匹配的特征列表，带相似度
        """
        # 构建查询过滤条件
        where_clause = {"user_id": user_id} if user_id else None

        # 执行向量搜索（多返回一些，后面重排序）
        results = self.collection.query(
            query_texts=[query],
            n_results=min(top_k * 2, 10),  # 多取一些用于重排序
            where=where_clause,
        )

        memories = []
        query_lower = query.lower()

        if results["ids"] and results["ids"][0]:
            for i, feat_id in enumerate(results["ids"][0]):
                distance = results["distances"][0][i]
                vector_similarity = 1.0 / (1.0 + distance)

                meta = results["metadatas"][0][i]

                # ===== 关键词精确匹配加权 =====
                keyword_bonus = 0.0
                # 1. key 精确匹配（最高优先级）
                if meta["key"] in query or meta["key"].lower() in query_lower:
                    keyword_bonus += 0.3
                # 2. value 精确匹配（高优先级）
                if meta.get("value", "") and meta["value"] in query:
                    keyword_bonus += 0.2
                # 3. category 精确匹配（次优先级）
                if meta.get("category", "") in query:
                    keyword_bonus += 0.1

                # 最终相似度 = 向量相似度 + 关键词加分（上限 0.95）
                final_similarity = min(vector_similarity + keyword_bonus, 0.95)

                memories.append({
                    "feature_id": feat_id,
                    "key": meta["key"],
                    "value": meta.get("value", ""),
                    "category": meta.get("category", "其他"),
                    "confidence": meta.get("confidence", 1.0),
                    "similarity": final_similarity,
                    "vector_similarity": vector_similarity,  # 原始向量分（调试用）
                    "source": "mem0",
                })

        # 按最终相似度排序
        memories.sort(key=lambda x: x["similarity"], reverse=True)
        return memories[:top_k]

    def get_all_features(
        self,
        user_id: Optional[str] = None,
        category: Optional[str] = None,
    ) -> List[FeatureItem]:
        """获取所有特征"""
        where_clause = {}
        if user_id:
            where_clause["user_id"] = user_id
        if category:
            where_clause["category"] = category

        if not where_clause:
            where_clause = None

        results = self.collection.get(where=where_clause)

        items = []
        if results["ids"]:
            for i, feat_id in enumerate(results["ids"]):
                meta = results["metadatas"][i]
                items.append(FeatureItem(
                    feature_id=feat_id,
                    key=meta["key"],
                    value=meta.get("value", ""),  # 修复：从 meta 读取 value
                    user_id=meta["user_id"],
                    confidence=meta.get("confidence", 1.0),
                    category=meta.get("category", "其他"),
                    created_at=meta.get("updated_at"),
                ))

        return items

    def count(self, user_id: Optional[str] = None) -> int:
        """统计特征数量"""
        where_clause = {"user_id": user_id} if user_id else None
        results = self.collection.get(where=where_clause, include=[])
        return len(results["ids"]) if results["ids"] else 0

    def clear(self, user_id: Optional[str] = None) -> int:
        """清空记忆"""
        if user_id:
            results = self.collection.get(where={"user_id": user_id}, include=[])
            if results["ids"]:
                count = len(results["ids"])
                self.collection.delete(ids=results["ids"])
                return count
            return 0
        else:
            count = self.count()
            self.client.delete_collection(self.collection_name)
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "mem0 key-value feature memory"},
            )
            return count

    def get_features_by_category(
        self,
        category: str,
        user_id: Optional[str] = None,
    ) -> List[FeatureItem]:
        """按分类获取特征"""
        return self.get_all_features(user_id=user_id, category=category)


class RuleBasedFeatureExtractor:
    """基于规则的特征提取器 - 从对话中提取关键特征

    每条规则定义为 (pattern, feature_key, group_index, fallback_value):
    - pattern: 正则表达式，用于匹配和捕获实际值
    - feature_key: 特征键名
    - group_index: 正则中用于提取值的分组编号（0=整句匹配，1=第一个捕获组）
    - fallback_value: 正则未匹配到捕获组时使用的默认值
    """

    # (regex_pattern, feature_key, capture_group_index, fallback_value)
    RULES = {
        "基本信息": [
            (r"(?:手机号|电话|号码)[是为]?\s*[:：]?\s*(1[3-9]\d{9})", "手机号", 1, ""),
            (r"(?<![0-9])(1[3-9]\d{9})(?![0-9])", "手机号", 1, ""),
            (r"(\d+\s*元(?:的?)?(?:融合|流量|宽带|千兆)?\s*套餐?)", "套餐类型", 1, ""),
            (r"(?:套餐|资费)[是为]\s*[:：]?\s*(.+?)(?:[，。,;.\s]|$)", "套餐类型", 1, ""),
            (r"(朝阳区|海淀区|西城区|东城区|丰台区|通州区|大兴区|浦东新区|天河区|南山区|中关村[^,，。；;？?！!]{0,10})", "所在地区", 1, ""),
            (r"(?:我叫|我是|姓名[是为]?\s*[:：]?)\s*([一-龥]{2,4})(?:[，。,;.\s]|$)", "客户姓名", 1, ""),
        ],
        "投诉记录": [
            (r"(?:投诉|不满|反馈)(?:过|了)?(?:.+?(?:宽带|网络|信号|流量|网速|上网))", "投诉类型", 0, "网络投诉"),
            (r"(?:投诉|不满|反馈)(?:过|了)?(?:.+?(?:扣费|收费|话费|费用|增值))", "投诉类型", 0, "费用投诉"),
            (r"(?:投诉|不满|反馈)[了过](?:过一次|一次)", "投诉类型", 0, "有过投诉记录"),
            (r"(掉线|断网|没信号|信号差|信号不好)", "网络问题", 1, "网络异常"),
            (r"(?:多扣|乱扣|扣费|乱收费)\s*(\d+\s*元?\s*.{0,15}?)(?:[，。,;.\s]|$)", "费用问题", 1, "费用异常"),
            (r"(爱音乐|彩铃|手机报)(?:增值业务)?", "增值业务问题", 1, "增值业务异常"),
            (r"(增值业务)", "增值业务问题", 1, "增值业务异常"),
        ],
        "业务意向": [
            (r"(千兆|升级|换套餐|套餐升级)", "套餐升级意向", 1, ""),
            (r"(副卡|办卡|办一张)", "副卡办理意向", 1, ""),
            (r"(携号转网|转网)", "携号转网意向", 1, ""),
            (r"(拆机|注销|停机)", "拆机意向", 1, ""),
        ],
        "用户偏好": [
            (r"(?:别[给]?打|不要[给]?打|不要.*电话|短信联系|发短信)", "联系偏好", 0, "短信联系"),
            (r"(爱奇艺|腾讯|优酷|芒果)", "会员偏好", 1, ""),
        ],
        "风险标签": [
            (r"(?:去|到|向|找)(?:了?)?(工信部|12345)", "越级投诉风险", 1, "越级投诉"),
            (r"(越级投诉|升级投诉)", "越级投诉风险", 1, "越级投诉"),
            (r"(流失|不用了|换运营商|不想用了)", "流失风险", 1, ""),
            (r"(第[二三四五六七八九十\d]\s*次|好几次|第三次)", "重复投诉", 1, "多次投诉"),
        ],
    }

    def extract(self, text: str) -> List[Dict[str, Any]]:
        """从文本中提取特征，使用正则捕获实际语义值"""
        features = []
        seen_keys = set()

        for category, rules in self.RULES.items():
            for pattern, feature_key, group_idx, fallback in rules:
                if feature_key in seen_keys:
                    continue
                match = re.search(pattern, text)
                if match:
                    # 尝试提取捕获组的值
                    try:
                        value = match.group(group_idx).strip()
                    except (IndexError, AttributeError):
                        value = ""
                    if not value:
                        value = fallback
                    if not value:
                        value = match.group(0).strip()

                    features.append({
                        "key": feature_key,
                        "value": value,
                        "category": category,
                        "confidence": 0.7,
                        "source": text[:80],
                    })
                    seen_keys.add(feature_key)

        return features
