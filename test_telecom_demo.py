#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
电信客服场景 - 双轨记忆系统演示
"""
import sys
from pathlib import Path

base_dir = Path(__file__).parent
sys.path.insert(0, str(base_dir))

from orchestrator import DualTrackOrchestrator
from data.demo_conversations import DEMO_CONVERSATIONS


def print_header(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def main():
    print_header("📞 电信客服场景 - 双轨记忆系统演示")

    # 1. 初始化双轨系统
    print_header("1️⃣  初始化双轨记忆系统")
    print("""
    🟢 mem0 (短期记忆)  - ChromaDB 向量数据库
       └─ 功能：快速存取近期对话，语义相似度搜索

    🟣 memU (长期记忆)  - 结构化分类，Markdown 归档
       └─ 功能：深度理解用户画像，提取关键信息，分类归档
    """)

    data_path = base_dir / "data" / "output" / "telecom_demo"
    orchestrator = DualTrackOrchestrator(
        base_dir=str(data_path),
        use_local_embedding=True,
        auto_trigger_memu=True,
        trigger_threshold=15,
    )
    print("✅ 系统初始化完成")

    # 2. 添加对话记录
    print_header("2️⃣  导入用户对话记录 (模拟客服对话)")
    print(f"共 {len(DEMO_CONVERSATIONS)} 轮对话")
    print("\n对话摘要：")
    for i, conv in enumerate(DEMO_CONVERSATIONS[:6], 1):
        role = "👤 用户" if conv["role"] == "user" else "🤖 客服"
        content = conv["content"][:50] + "..." if len(conv["content"]) > 50 else conv["content"]
        print(f"  {role}: {content}")
    print("  ... (后续对话省略)")

    for conv in DEMO_CONVERSATIONS:
        orchestrator.add_message(
            role=conv["role"],
            content=conv["content"],
            user_id="13800138000",  # 用户手机号作为 ID
        )

    print(f"\n✅ {len(DEMO_CONVERSATIONS)} 轮对话已导入 mem0 短期记忆")

    # 3. 触发 memU 长期记忆提取
    print_header("3️⃣  触发 memU 长期记忆提取")
    print("正在分析对话内容，提取用户画像和关键信息...")
    result = orchestrator.force_memu_extraction(user_id="13800138000")

    categories = result.get("categories", [])
    print(f"\n✅ 提取完成，共识别 {len(categories)} 个信息分类")

    for cat in categories:
        display_name = cat.get('display_name', '')
        icon = cat.get('icon', '📄')
        key_points = cat.get('key_points', [])
        print(f"\n  {icon} {display_name}")
        for point in key_points[:3]:
            print(f"    • {point}")

    # 4. 双轨搜索演示
    print_header("4️⃣  双轨搜索演示 - 同时搜索短期 + 长期记忆")

    test_queries = [
        ("用户手机号和套餐", "基础信息查询"),
        ("用户投诉过什么问题", "投诉记录查询"),
        ("用户有什么偏好和禁忌", "用户偏好查询"),
        ("增值业务扣费", "具体问题查询"),
        ("用户有没有流失风险", "风险评估查询"),
    ]

    for query, desc in test_queries:
        print(f"\n{'─' * 60}")
        print(f"🔍 搜索: {query} ({desc})")
        print(f"{'─' * 60}")

        search_result = orchestrator.search(query, top_k=3)

        # mem0 结果（短期记忆 - 具体对话）
        mem0_results = search_result.get("mem0_results", [])
        if mem0_results:
            print(f"\n  🟢 mem0 短期记忆匹配 ({len(mem0_results)} 条):")
            for r in mem0_results[:2]:
                content = r["content"][:60] + "..." if len(r["content"]) > 60 else r["content"]
                print(f"    相似度 {r['similarity']:.1%}: {content}")

        # memU 结果（长期记忆 - 结构化知识）
        memu_results = search_result.get("memu_results", [])
        if memu_results:
            print(f"\n  🟣 memU 长期记忆匹配 ({len(memu_results)} 条):")
            for r in memu_results[:2]:
                print(f"    匹配度 {r['similarity']:.1%}: {r.get('display_name', '')}")

    # 5. 生成给 LLM 的上下文
    print_header("5️⃣  生成给 LLM 的上下文 (客服回复参考)")

    context = orchestrator.get_context_for_llm("这个用户有什么投诉记录？需要注意什么？")
    print(context)

    # 6. 系统统计
    print_header("6️⃣  系统状态统计")
    stats = orchestrator.get_stats()
    print(f"""
    📊 系统概览
    ├─ mem0 短期记忆
    │  └─ 记忆条目数: {stats['mem0']['total_items']}
    │
    ├─ memU 长期记忆
    │  ├─ 分类数量: {stats['memu']['total_categories']}
    │  └─ 提取次数: {stats['memu']['extractions_count']}
    │
    └─ 协调器状态
       └─ 自动提取阈值: {stats['buffer']['trigger_threshold']} 轮对话
    """)

    print_header("✅ 演示完成！")
    print("""
    双轨记忆系统工作原理总结：

    1️⃣  每条对话实时写入 mem0 向量记忆 (亚秒级)
    2️⃣  累计 N 轮对话后，异步触发 memU 深度提取
    3️⃣  查询时同时搜索两个轨道，融合结果
    4️⃣  mem0 提供精准上下文，memU 提供用户画像

    🎯 应用场景：客服坐席辅助、用户画像分析、风险预警
    """)

    # 清理测试数据
    orchestrator.clear_all()


if __name__ == "__main__":
    main()
