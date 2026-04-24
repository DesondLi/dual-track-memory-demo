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


def main():
    print("=" * 70)
    print("  Telecom Customer Service - Dual Track Memory Demo")
    print("=" * 70)

    # 1. 初始化双轨系统
    print("\n[1] Initializing Dual Track Memory System")
    print("    * mem0 (short-term) - ChromaDB vector storage")
    print("    * memU (long-term)  - Structured classification, Markdown output")

    data_path = base_dir / "data" / "output" / "telecom_demo"
    orchestrator = DualTrackOrchestrator(
        base_dir=str(data_path),
        use_local_embedding=True,
        auto_trigger_memu=True,
        trigger_threshold=15,
    )
    print("    System initialized successfully!")

    # 2. 添加对话记录
    print(f"\n[2] Importing customer conversations")
    print(f"    Total conversations: {len(DEMO_CONVERSATIONS)}")
    print("\n    Conversation preview:")
    for i, conv in enumerate(DEMO_CONVERSATIONS[:4], 1):
        role = "User" if conv["role"] == "user" else "Agent"
        content = conv["content"][:50] + "..." if len(conv["content"]) > 50 else conv["content"]
        print(f"    {role}: {content}")

    for conv in DEMO_CONVERSATIONS:
        orchestrator.add_message(
            role=conv["role"],
            content=conv["content"],
            user_id="13800138000",
        )

    print(f"\n    All {len(DEMO_CONVERSATIONS)} conversations imported to mem0")

    # 3. 触发 memU 长期记忆提取
    print("\n[3] Triggering memU structured memory extraction")
    print("    Analyzing conversations to extract user profile...")
    result = orchestrator.force_memu_extraction(user_id="13800138000")

    categories = result.get("categories", [])
    print(f"\n    Extraction complete! {len(categories)} categories identified")

    for cat in categories:
        display_name = cat.get('display_name', '')
        key_points = cat.get('key_points', [])
        print(f"\n    [{display_name}]")
        for point in key_points[:3]:
            print(f"      - {point}")

    # 4. 双轨搜索演示
    print("\n[4] Dual Track Search Demo")
    print("    Searching both short-term and long-term memory...")

    test_queries = [
        "phone number and package",
        "complaint history",
        "user preferences",
        "value-added service charge",
        "churn risk",
    ]

    for query in test_queries:
        print(f"\n    {'-'*50}")
        print(f"    Search: {query}")
        print(f"    {'-'*50}")

        search_result = orchestrator.search(query, top_k=2)

        mem0_results = search_result.get("mem0_results", [])
        if mem0_results:
            print(f"\n    [mem0 Short-term] {len(mem0_results)} matches")
            for r in mem0_results[:1]:
                content = r["content"][:50] + "..."
                print(f"      {r['similarity']:.0%} sim: {content}")

        memu_results = search_result.get("memu_results", [])
        if memu_results:
            print(f"\n    [memU Long-term] {len(memu_results)} matches")
            for r in memu_results[:1]:
                print(f"      {r['similarity']:.0%} sim: {r.get('display_name', '')}")

    # 5. 生成给 LLM 的上下文
    print("\n[5] LLM Context Generation")
    print("    Context for agent response reference:")
    context = orchestrator.get_context_for_llm("user complaint history and notes")
    print(context[:300] + "..." if len(context) > 300 else context)

    # 6. 系统统计
    print("\n[6] System Statistics")
    stats = orchestrator.get_stats()
    print(f"""
    System Overview
    ---------------
    mem0 Short-term Memory
      - Total items: {stats['mem0']['total_items']}

    memU Long-term Memory
      - Categories: {stats['memu']['total_categories']}
      - Extractions: {stats['memu']['extractions_count']}

    Orchestrator
      - Auto-trigger threshold: {stats['buffer']['trigger_threshold']} conversations
    """)

    print("=" * 70)
    print("  Demo Completed Successfully!")
    print("=" * 70)

    # 清理测试数据
    orchestrator.clear_all()


if __name__ == "__main__":
    main()
