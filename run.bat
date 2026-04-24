@echo off
REM 启动双轨记忆架构 Demo (Windows)

cd /d "%~dp0"

REM 检查是否安装了依赖
python -c "import streamlit" 2>nul
if errorlevel 1 (
    echo 安装依赖中...
    pip install -r requirements.txt
)

echo 启动双轨记忆架构 Demo...
echo 访问 http://localhost:8501 查看界面
streamlit run app.py --server.port=8501
