#!/bin/bash
# 启动双轨记忆架构 Demo

# 进入脚本所在目录
cd "$(dirname "$0")"

# 检查是否安装了依赖
if ! python -c "import streamlit" 2>/dev/null; then
    echo "安装依赖中..."
    pip install -r requirements.txt
fi

# 启动 Streamlit
echo "启动双轨记忆架构 Demo..."
echo "访问 http://localhost:8501 查看界面"
streamlit run app.py --server.port=8501
