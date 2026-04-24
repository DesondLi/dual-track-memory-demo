#!/usr/bin/env python
"""
快速测试脚本 - 验证双轨记忆架构的基本功能
"""
import sys
from pathlib import Path

base_dir = Path(__file__).parent
sys.path.insert(0, str(base_dir))

from orchestrator import DualTrackOrchestrator
from data.demo_conversations import DEMO_CONVERSATIONS


def test_basic_functionality():
    print("=" * 60)
    print("🧪 双轨记忆架构 - 快速测试")
    print("=" * 60)

    # 1. 初始化协调器
    print("\n1️⃣  初始化协调器...")
    data_path = base_dir / "data" / "output" / "test"

    orchestrator = DualTrackOrchestrator(
        base_dir=str(data_path),
        use_local_embedding=True,  # 使用本地嵌入，无需 API Key
    )
    print("   ✅ 初始化完成")

    # 2. 添加一些对话
    print("\n2️⃣  添加对话...")
    test_conversations = DEMO_CONVERSATIONS[:10]

    for conv in test_conversations:
        orchestrator.add_message(
            role=conv["role"],
            content=conv["content"],
        )

    print(f"   ✅ 添加了 {len(test_conversations)} 条对话")

    # 3. 查看 mem0 记忆
    print("\n3️⃣  mem0 向量记忆:")
    mem0_count = orchestrator.mem0.count()
    print(f"   总条数: {mem0_count}")

    recent_items = orchestrator.mem0.get_recent(limit=3)
    for i, item in enumerate(recent_items, 1):
        print(f"   {i}. {item.content[:50]}...")

    # 4. 触发 memU 提取
    print("\n4️⃣  触发 memU 结构化提取...")
    print("   (使用关键词匹配模式，无需 API Key)")
    result = orchestrator.force_memu_extraction()
    categories = result.get("categories", [])
    print(f"   ✅ 提取完成，得到 {len(categories)} 个分类")

    for cat in categories:
        print(f"   - {cat.get('icon')} {cat.get('display_name')}: {len(cat.get('key_points', []))} 个关键点")

    # 5. 测试搜索
    print("\n5️⃣  测试搜索功能...")
    test_queries = ["用户的工作", "用户的爱好", "用户的目标"]

    for query in test_queries:
        search_result = orchestrator.search(query, top_k=3)
        total = search_result["total_results"]
        print(f"   🔍 '{query}' → 找到 {total} 条结果")

    # 6. 显示统计
    print("\n6️⃣  系统统计:")
    stats = orchestrator.get_stats()
    print(f"   mem0 条目: {stats['mem0']['total_items']}")
    print(f"   memU 分类数: {stats['memu']['total_categories']}")
    print(f"   提取次数: {stats['memu']['extractions_count']}")

    # 7. 测试 LLM 上下文生成
    print("\n7️⃣  生成 LLM 上下文:")
    context = orchestrator.get_context_for_llm("用户的职业和目标是什么？")
    if context:
        print(context[:300] + "..." if len(context) > 300 else context)
    else:
        print("   (无上下文)")

    print("\n" + "=" * 60)
    print("✅ 所有测试通过！")
    print("=" * 60)

    # 清理测试数据
    orchestrator.clear_all()
    print("\n🧹 测试数据已清理")

    return True


if __name__ == "__main__":
    try:
        success = test_basic_functionality()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
