#!/bin/bash

# 启动后端服务
echo "启动后端主应用..."
cd backend
python app.py &
BACKEND_PID=$!


# 启动前端服务
echo "启动前端服务..."
cd ../
npm run dev &
FRONTEND_PID=$!

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT

wait