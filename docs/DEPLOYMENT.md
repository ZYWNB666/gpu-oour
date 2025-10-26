# GPU Monitor 快速部署指南

## 🚀 方式一：直接运行（开发/测试）

### 1. 安装依赖
```powershell
# 创建虚拟环境
python -m venv venv
.\venv\Scripts\Activate.ps1

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置服务
修改 `gpu_monitor.py` 中的 Prometheus 地址：
```python
PROM_URL = "http://your-prometheus-server:9090"
```

### 3. 启动服务
```powershell
python gpu_monitor.py
```

或使用 uvicorn：
```powershell
uvicorn gpu_monitor:app --host 0.0.0.0 --port 8080 --reload
```

### 4. 验证服务
```powershell
# 访问服务信息
curl http://localhost:8080/

# 手动触发分析
curl http://localhost:8080/analyze

# 查看结果
curl http://localhost:8080/results
```

---

## 🐳 方式二：Docker 部署（推荐）

### 1. 构建镜像
```powershell
docker build -t gpu-monitor:latest .
```

### 2. 运行容器
```powershell
docker run -d \
  --name gpu-monitor \
  -p 8080:8080 \
  -e PROM_URL=http://prometheus:9090 \
  -e THRESHOLD=20 \
  -e INTERVAL=300 \
  gpu-monitor:latest
```

### 3. 查看日志
```powershell
docker logs -f gpu-monitor
```

### 4. 停止服务
```powershell
docker stop gpu-monitor
docker rm gpu-monitor
```

---

## 🐳 方式三：Docker Compose

### 1. 启动服务
```powershell
docker-compose up -d
```

### 2. 查看日志
```powershell
docker-compose logs -f gpu-monitor
```

### 3. 停止服务
```powershell
docker-compose down
```

---

## ☸️ 方式四：Kubernetes 部署（生产环境）

### 1. 修改配置
编辑 `k8s-deployment.yaml`，修改 Prometheus 地址：
```yaml
data:
  PROM_URL: "http://your-prometheus.namespace:9090"
```

### 2. 部署到 K8s
```powershell
kubectl apply -f k8s-deployment.yaml
```

### 3. 查看部署状态
```powershell
# 查看 Pod 状态
kubectl get pods -n gpu-monitoring

# 查看服务
kubectl get svc -n gpu-monitoring

# 查看日志
kubectl logs -f -n gpu-monitoring deployment/gpu-monitor
```

### 4. 访问服务
```powershell
# 端口转发（测试）
kubectl port-forward -n gpu-monitoring svc/gpu-monitor 8080:80

# 通过 Ingress（生产）
curl http://gpu-monitor.example.com/
```

### 5. 更新配置
```powershell
# 修改 ConfigMap
kubectl edit configmap gpu-monitor-config -n gpu-monitoring

# 重启 Pod 使配置生效
kubectl rollout restart deployment/gpu-monitor -n gpu-monitoring
```

---

## 📊 验证和测试

### 1. 健康检查
```powershell
curl http://localhost:8080/health
```

### 2. 手动触发分析
```powershell
curl http://localhost:8080/analyze
```

### 3. 查看分析结果
```powershell
# 所有 GPU 结果
curl http://localhost:8080/results

# 低利用率 GPU
curl http://localhost:8080/results/low

# 统计信息
curl http://localhost:8080/results/stats
```

---

## 🔧 常见问题

### Q1: 连接 Prometheus 失败
**A:** 检查 Prometheus 地址和网络连通性
```powershell
# 测试连接
curl http://prometheus:9090/api/v1/status/config
```

### Q2: 查询不到 GPU 数据
**A:** 检查 Prometheus 是否有 DCGM metrics
```powershell
# 在 Prometheus 中查询
DCGM_FI_DEV_GPU_UTIL{pod!=""}
```

### Q3: Docker 容器无法启动
**A:** 查看日志排查问题
```powershell
docker logs gpu-monitor
```

### Q4: K8s Pod 无法访问 Prometheus
**A:** 检查网络策略和 Service 配置
```powershell
# 测试 DNS 解析
kubectl run -it --rm debug --image=busybox --restart=Never -- nslookup prometheus.monitoring
```

---

## 🔒 安全建议

1. **生产环境**：使用 HTTPS 和认证
2. **配置管理**：使用 Secret 存储敏感信息
3. **网络隔离**：限制服务访问权限
4. **资源限制**：设置合理的 CPU/内存限制

---

## 📈 监控和告警

建议配置以下监控：
- 服务健康状态
- API 响应时间
- Prometheus 查询成功率
- GPU 分析任务执行情况

---

## 🔄 升级和维护

### 升级镜像
```powershell
# 构建新镜像
docker build -t gpu-monitor:v1.1 .

# K8s 更新
kubectl set image deployment/gpu-monitor gpu-monitor=gpu-monitor:v1.1 -n gpu-monitoring
```

### 备份配置
```powershell
# 导出配置
kubectl get configmap gpu-monitor-config -n gpu-monitoring -o yaml > backup.yaml
```

---

## 📞 技术支持

遇到问题请：
1. 查看日志
2. 检查配置
3. 参考 README.md
4. 提交 Issue

