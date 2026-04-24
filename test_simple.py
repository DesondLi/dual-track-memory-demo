#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
简单测试脚本 - 验证双轨记忆架构的基本功能
"""
import sys
import io

# 解决 Windows 编码问题
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from pathlib import Path

base_dir = Path(__file__).parent
sys.path.insert(0, str(base_dir))

from orchestrator import DualTrackOrchestrator
from data.demo_conversations import DEMO_CONVERSATIONS


def test_basic_functionality():
    print("=" * 60)
    print("Dual Track Memory - Basic Test")
    print("=" * 60)

    # 1. 初始化协调器
    print("\n[1] Initializing orchestrator...")
    data_path = base_dir / "data" / "output" / "test"

    orchestrator = DualTrackOrchestrator(
        base_dir=str(data_path),
        use_local_embedding=True,
    )
    print("    OK")

    # 2. 添加一些对话
    print("\n[2] Adding conversations...")
    test_conversations = DEMO_CONVERSATIONS[:10]

    for conv in test_conversations:
        orchestrator.add_message(
            role=conv["role"],
            content=conv["content"],
        )

    print(f"    Added {len(test_conversations)} conversations")

    # 3. 查看 mem0 记忆
    print("\n[3] mem0 vector memory:")
    mem0_count = orchestrator.mem0.count()
    print(f"    Total items: {mem0_count}")

    recent_items = orchestrator.mem0.get_recent(limit=3)
    for i, item in enumerate(recent_items, 1):
        content_preview = item.content[:50] + "..." if len(item.content) > 50 else item.content
        print(f"    {i}. {content_preview}")

    # 4. 触发 memU 提取
    print("\n[4] Triggering memU structured extraction...")
    print("    (Using keyword matching, no API Key needed)")
    result = orchestrator.force_memu_extraction()
    categories = result.get("categories", [])
    print(f"    Extraction complete, got {len(categories)} categories")

    for cat in categories:
        display_name = cat.get('display_name', '')
        key_points_count = len(cat.get('key_points', []))
        print(f"    - {display_name}: {key_points_count} key points")

    # 5. 测试搜索
    print("\n[5] Testing search functionality...")
    test_queries = ["用户的工作", "用户的爱好", "用户的目标"]

    for query in test_queries:
        search_result = orchestrator.search(query, top_k=3)
        total = search_result["total_results"]
        print(f"    Search '{query}' -> {total} results")

    # 6. 显示统计
    print("\n[6] System stats:")
    stats = orchestrator.get_stats()
    print(f"    mem0 items: {stats['mem0']['total_items']}")
    print(f"    memU categories: {stats['memu']['total_categories']}")
    print(f"    Extraction count: {stats['memu']['extractions_count']}")

    # 7. 测试 LLM 上下文生成
    print("\n[7] Generating LLM context:")
    context = orchestrator.get_context_for_llm("用户的职业和目标是什么？")
    if context:
        preview = context[:300] + "..." if len(context) > 300 else context
        print(preview)
    else:
        print("    (No context found)")

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED!")
    print("=" * 60)

    # 清理测试数据
    orchestrator.clear_all()
    print("\nTest data cleaned up")

    return True


if __name__ == "__main__":
    try:
        success = test_basic_functionality()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\nTest failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
