# 双轨记忆系统 - 项目记忆

## 最新更新
- **日期**: 2026-04-27
- **变更**: LLM 配置已内置默认值，无需用户手动配置
- **默认 API Key**: sk-B3dOLsy6g9wA6wLJ8177A66aEb4348Ed843847Dc1b0eCb05
- **默认 API Base**: https://aihubmix.com/v1
- **默认模型**: coding-minimax-m2.7-free

## 修改文件
1. `config.py` - 更新 LLM_CONFIG 使用默认配置
2. `agent_module/telecom_agent.py` - 导入 config 并使用默认配置初始化
3. `app.py` - 移除智能坐席页面的 LLM 配置 UI，简化为状态显示

## 遗留事项
- 暂无

## 下一步计划
- 可考虑添加模型选择下拉菜单（如果需要切换模型）
