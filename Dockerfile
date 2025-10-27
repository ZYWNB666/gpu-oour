FROM python:3.10-slim

LABEL maintainer="GPU Monitor Team"
LABEL description="GPU Utilization Monitor Service"

# 设置环境变量支持 UTF-8
ENV PYTHONIOENCODING=utf-8
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    curl \
    locales \
    && locale-gen C.UTF-8 \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用文件
COPY main.py .
COPY app/ ./app/
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
CMD ["python", "main.py"]

