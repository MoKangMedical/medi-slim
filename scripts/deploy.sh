#!/bin/bash
# MediSlim 一键部署脚本
# 用法: ./scripts/deploy.sh [port]

set -e

PORT=${1:-8090}
APP_NAME="medislim"

echo "💊 MediSlim 部署开始..."
echo "========================"

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装"
    exit 1
fi

# 停止旧进程
echo "🔄 停止旧进程..."
pkill -f "python3 app.py" 2>/dev/null || true
sleep 1

# 创建数据目录
mkdir -p data

# 启动服务
echo "🚀 启动 MediSlim (port: $PORT)..."
PORT=$PORT nohup python3 app.py > /tmp/medislim.log 2>&1 &
PID=$!
sleep 2

# 健康检查
if curl -s http://localhost:$PORT/api/stats > /dev/null 2>&1; then
    echo "✅ MediSlim 部署成功！"
    echo ""
    echo "📱 前端: http://localhost:$PORT"
    echo "📊 API:  http://localhost:$PORT/api/stats"
    echo "📝 日志: /tmp/medislim.log"
    echo "🔑 PID:  $PID"
else
    echo "❌ 部署失败，查看日志: /tmp/medislim.log"
    exit 1
fi
