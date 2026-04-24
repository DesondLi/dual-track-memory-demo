#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
双轨记忆系统 v2 快速测试
- mem0: 关键特征记忆库
- memU: 客户档案中心
"""
import sys
from pathlib import Path

base_dir = Path(__file__).parent
sys.path.insert(0, str(base_dir))

from orchestrator import DualTrackOrchestrator


def main():
    print("=" * 70)
    print("  电信客服双轨记忆系统 v2 - 快速测试")
    print("=" * 70)

    # 1. 初始化系统
    print("\n[1] 初始化双轨记忆系统")
    data_path = base_dir / "data" / "output" / "test_v2"

    orchestrator = DualTrackOrchestrator(
        base_dir=str(data_path),
        auto_trigger_profile=True,
        trigger_threshold=5,
    )
    print("    ✅ 系统初始化完成")

    # 2. 模拟对话并提取特征
    print("\n[2] 添加测试对话并提取特征")
    test_conversations = [
        ("user", "你好，我是13800138000，我家宽带最近总是掉线"),
        ("assistant", "您好，非常抱歉给您带来不便！请问是朝阳区的59元融合套餐对吗？"),
        ("user", "对的，这个问题我上个月3月15号已经投诉过一次了，当时说给我优化，结果一点改善都没有"),
        ("assistant", "非常抱歉让您再次失望！我现在就帮您升级到专家级处理"),
        ("user", "还有啊，上个月话费又多扣了15块钱，是什么爱音乐增值业务，我从来没开通啊！"),
        ("assistant", "非常抱歉！我现在就帮您取消这个业务，并且双倍返还30元话费"),
        ("user", "一定要屏蔽所有增值业务！再这样我真要去工信部投诉了"),
        ("assistant", "好的，已帮您屏蔽所有增值业务。对了，您之前提过携号转网的事，还在考虑吗？"),
        ("user", "暂时先不转了，主要是你们公司信号在我公司那边不太好，电梯里经常没信号"),
        ("assistant", "您说的是中关村科技园西区吧？我们正在那边做5G信号优化，预计下个月就能完工"),
    ]

    for role, content in test_conversations:
        result = orchestrator.add_message(role=role, content=content)
        if result["features_extracted"] > 0:
            print(f"    {role}: '{content[:30]}...' -> 提取 {result['features_extracted']} 个特征")

    print(f"\n    总计添加 {len(test_conversations)} 轮对话")

    # 3. 查看 mem0 提取的特征
    print("\n[3] mem0 - 关键特征记忆库")
    all_features = orchestrator.mem0.get_all_features()
    print(f"    共提取到 {len(all_features)} 个特征")

    categories = {}
    for feat in all_features:
        cat = getattr(feat, "category", "其他")
        key = getattr(feat, "key", "")
        value = getattr(feat, "value", "")
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(f"{key}: {value}")

    for cat, items in categories.items():
        print(f"\n    【{cat}】")
        for item in items:
            print(f"      - {item}")

    # 4. 触发 memU 建档
    print("\n[4] memU - 构建客户档案")
    result = orchestrator.force_build_profile()
    print(f"    使用 {result['features_used']} 个特征构建档案")

    # 5. 展示客户档案
    profile = orchestrator.get_profile()
    if profile:
        print("\n" + "-" * 60)
        print("    📋 客户档案摘要")
        print("-" * 60)

        if profile.risk_tags.items:
            print("\n    🚨 风险标签:")
            for item in profile.risk_tags.items:
                print(f"      - {item}")

        if profile.user_preferences.items:
            print("\n    ❤️ 用户偏好:")
            for item in profile.user_preferences.items:
                print(f"      - {item}")

        if profile.complaint_history.items:
            print("\n    ⚠️ 投诉记录:")
            for item in profile.complaint_history.items:
                print(f"      - {item}")

        if profile.insights:
            print("\n    💡 业务洞察:")
            for insight in profile.insights:
                print(f"      - {insight}")

        if profile.recommendations:
            print("\n    📌 跟进建议:")
            for rec in profile.recommendations:
                print(f"      - {rec}")

    # 6. 测试搜索功能
    print("\n[5] 双轨搜索测试")
    test_queries = ["投诉", "风险", "套餐", "增值业务"]
    for query in test_queries:
        result = orchestrator.search(query, top_k=3)
        total = result["total_results"]
        print(f"    🔍 搜索 '{query}' -> 找到 {total} 条结果")

    # 7. 统计信息
    print("\n[6] 系统统计")
    stats = orchestrator.get_stats()
    print(f"""
    mem0 特征数: {stats['mem0']['total_features']}
    memU 档案数: {stats['memu']['total_profiles']}
    最后建档:   {stats['memu']['last_build_time'][:19] if stats['memu']['last_build_time'] else '无'}
    """)

    # 清理测试数据
    orchestrator.clear_all()
    print("    🧹 测试数据已清理")

    print("\n" + "=" * 70)
    print("  ✅ 所有测试通过！")
    print("=" * 70)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
