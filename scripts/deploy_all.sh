#!/bin/bash
# MediSlim 全套服务一键部署
# 用法: bash scripts/deploy_all.sh

set -e

echo "╔══════════════════════════════════════════════╗"
echo "║   MediSlim 全套服务部署                       ║"
echo "╚══════════════════════════════════════════════╝"

cd "$(dirname "$0")/.."

# 创建数据目录
mkdir -p data content_engine/data content_engine/output

# 停止旧进程
echo "🔄 停止旧进程..."
for port in 8090 8091 8092 8093 8096 8097 8098 8099 8100 8101; do
    pid=$(lsof -ti :$port 2>/dev/null || true)
    if [ -n "$pid" ]; then
        kill $pid 2>/dev/null || true
    fi
done
sleep 2

# 启动函数
start_service() {
    local name=$1
    local port=$2
    local script=$3
    local log="/tmp/medislim_${name}.log"
    
    nohup python3 "$script" > "$log" 2>&1 &
    local pid=$!
    sleep 1
    
    # 健康检查
    if curl -s --connect-timeout 3 "http://localhost:$port/" > /dev/null 2>&1 || \
       curl -s --connect-timeout 3 "http://localhost:$port/api/stats" > /dev/null 2>&1 || \
       curl -s --connect-timeout 3 "http://localhost:$port/api/health" > /dev/null 2>&1 || \
       curl -s --connect-timeout 3 "http://localhost:$port/api/funnel" > /dev/null 2>&1 || \
       curl -s --connect-timeout 3 "http://localhost:$port/api/queue-status" > /dev/null 2>&1; then
        echo "   ✅ $name (port $port) pid=$pid"
    else
        echo "   ⚠️ $name (port $port) 启动中... pid=$pid"
    fi
}

echo ""
echo "🚀 启动服务..."

start_service "app"          8090 app.py
start_service "landing"      8091 landing.py
start_service "flow_engine"  8092 flow_engine.py
start_service "admin"        8093 admin.py
start_service "preview"      8096 content_engine/preview_server.py
start_service "tracking"     8097 content_engine/tracking.py
start_service "smart_landing" 8098 smart_landing.py
start_service "xhs_queue"    8099 xhs_queue.py
start_service "scheduler"    8100 content_engine/scheduler.py
start_service "ab_testing"   8101 content_engine/ab_testing.py

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║   ✅ 全部服务已启动                           ║"
echo "╠══════════════════════════════════════════════╣"
echo "║                                              ║"
echo "║   📱 主业务:      http://localhost:8090       ║"
echo "║   🌐 落地页:      http://localhost:8091       ║"
echo "║   🔄 业务流:      http://localhost:8092       ║"
echo "║   📊 管理后台:    http://localhost:8093       ║"
echo "║   🎨 内容预览:    http://localhost:8096       ║"
echo "║   📈 漏斗看板:    http://localhost:8097/api/dashboard ║"
echo "║   🌐 智能落地页:  http://localhost:8098       ║"
echo "║   📮 发布队列:    http://localhost:8099       ║"
echo "║   📅 智能排期:    http://localhost:8100       ║"
echo "║   🧪 A/B测试:     http://localhost:8101       ║"
echo "║                                              ║"
echo "╚══════════════════════════════════════════════╝"
echo ""
echo "📝 日志目录: /tmp/medislim_*.log"
