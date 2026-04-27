"""
双轨记忆架构配置文件
"""
import os
from pathlib import Path

# 基础路径
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "data" / "output"

# mem0 配置
MEM0_CONFIG = {
    "vector_db_path": str(OUTPUT_DIR / "mem0_chroma"),
    "embedding_model": "text-embedding-3-small",
    "default_top_k": 5,
    "max_memory_items": 500,  # 最多保留记忆条数
    "ttl_days": 30,  # 记忆过期天数
}

# memU 配置
MEMU_CONFIG = {
    "output_dir": str(OUTPUT_DIR / "memu_markdown"),
    "trigger_threshold": 10,  # 每累计N条对话触发memU提取
    "categories": [
        "personal_info",      # 个人信息
        "preferences",        # 偏好
        "knowledge",          # 知识
        "goals",              # 目标
        "habits",             # 习惯
        "relationships",      # 关系
        "experiences",        # 经历
        "work_life",          # 工作生活
        "activities",         # 活动
        "opinions",           # 观点
    ],
    "llm_model": "gpt-4o-mini",
}

# 协调器配置
ORCHESTRATOR_CONFIG = {
    "auto_trigger_memu": True,  # 是否自动触发memU提取
    "fusion_strategy": "weighted",  # 融合策略: weighted / rerank / concat
    "mem0_weight": 0.6,  # mem0 结果权重
    "memu_weight": 0.4,  # memU 结果权重
    "enable_async_memu": True,  # 是否异步执行memU提取（不阻塞对话）
}

# LLM 配置 - 默认配置，无需用户手动设置
LLM_CONFIG = {
    "api_key": os.getenv("OPENAI_API_KEY", "sk-B3dOLsy6g9wA6wLJ8177A66aEb4348Ed843847Dc1b0eCb05"),
    "api_base": os.getenv("OPENAI_API_BASE", "https://aihubmix.com/v1"),
    "chat_model": os.getenv("OPENAI_MODEL", "coding-minimax-m2.7-free"),
    "temperature": 0.7,
}

# Demo 配置
DEMO_CONFIG = {
    "title": "🧠 mem0 + memU 双轨记忆架构 Demo",
    "subtitle": "短期向量记忆 + 长期结构化记忆 = 完美的 AI 记忆系统",
    "default_user_id": "demo_user_001",
    "show_debug_info": True,
}

# 创建必要目录
for dir_path in [
    DATA_DIR,
    OUTPUT_DIR,
    Path(MEM0_CONFIG["vector_db_path"]),
    Path(MEMU_CONFIG["output_dir"]),
]:
    dir_path.mkdir(parents=True, exist_ok=True)
