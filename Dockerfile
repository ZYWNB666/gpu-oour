FROM python:3.10-slim

LABEL maintainer="GPU Monitor Team"
LABEL description="GPU Utilization Monitor Service"

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用文件
COPY gpu_monitor.py .
COPY config.yaml .

# 创建非 root 用户
RUN useradd -m -u 1000 monitor && \
    chown -R monitor:monitor /app

USER monitor

# 暴露端口
EXPOSE 8080

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# 启动服务
CMD ["uvicorn", "gpu_monitor:app", "--host", "0.0.0.0", "--port", "8080"]

