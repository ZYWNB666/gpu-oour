# GPU Monitor - 配置检查清单

## ✅ 部署前检查清单

### 1. Prometheus 配置
- [ ] Prometheus 地址正确：`PROM_URL`
- [ ] Prometheus 可访问
- [ ] DCGM exporter 已部署
- [ ] 查询条件正确：`{pod!=""}`

**验证方法：**
```powershell
# 测试 Prometheus 连接
curl http://your-prometheus:9090/api/v1/query?query=up

# 测试 GPU metrics 是否存在
curl 'http://your-prometheus:9090/api/v1/query?query=DCGM_FI_DEV_GPU_UTIL{pod!=""}'
```

---

### 2. 阈值配置
- [ ] 低利用率阈值合理：`THRESHOLD` (推荐 15-25)
- [ ] 闲置阈值合理：`IDLE_THRESHOLD` (推荐 5-10)
- [ ] 时间窗口合理：`TIME_WINDOW_MIN` (推荐 5-15 分钟)

**验证方法：**
```powershell
curl http://localhost:8080/config
```

---

### 3. 调度配置
- [ ] 轮询周期合理：`INTERVAL` (推荐 300-600 秒)
- [ ] 并发线程数合理：`MAX_WORKERS` (推荐 4-16)

**计算公式：**
```
MAX_WORKERS ≈ GPU总数 / 10
INTERVAL = 根据实时性要求 (5-10分钟)
```

---

### 4. AI 配置（可选）
- [ ] AI_ENABLED 设置正确
- [ ] AI_API_URL 配置正确
- [ ] AI_API_KEY 已设置
- [ ] AI_MODEL 选择合适

**支持的模型：**
- OpenAI: gpt-4, gpt-3.5-turbo
- Claude: claude-3-opus, claude-3-sonnet
- 其他兼容 OpenAI 格式的 API

**验证方法：**
```powershell
# 测试 AI API
curl -X POST $AI_API_URL \
  -H "Authorization: Bearer $AI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4","messages":[{"role":"user","content":"test"}]}'
```

---

### 5. 控制接口配置（可选）
- [ ] CONTROL_API_ENABLED 设置正确
- [ ] CONTROL_API 地址正确
- [ ] 控制接口可访问
- [ ] 接口认证已配置

**测试方法：**
```powershell
# 测试控制接口
curl -X POST $CONTROL_API \
  -H "Content-Type: application/json" \
  -d '{"test": true}'
```

---

### 6. 日志配置
- [ ] LOG_LEVEL 合适 (INFO/DEBUG/WARNING)
- [ ] 日志输出路径正确
- [ ] 日志轮转已配置

**推荐配置：**
- 开发环境：DEBUG
- 测试环境：INFO
- 生产环境：WARNING

---

### 7. 网络配置
- [ ] 服务端口未被占用：8080
- [ ] 防火墙规则已配置
- [ ] 可以访问 Prometheus
- [ ] 可以访问 AI API（如果启用）
- [ ] 可以访问控制接口（如果启用）

**验证方法：**
```powershell
# 检查端口
netstat -ano | findstr :8080

# 测试网络连通性
Test-NetConnection -ComputerName prometheus -Port 9090
```

---

### 8. 资源配置
- [ ] CPU 资源充足 (推荐 2-4 核)
- [ ] 内存资源充足 (推荐 1-2 GB)
- [ ] Python 版本正确 (>= 3.8)
- [ ] 依赖包已安装

**验证方法：**
```powershell
# 检查 Python 版本
python --version

# 检查依赖包
pip list | findstr -i "fastapi prometheus numpy"
```

---

## 🔍 启动后检查

### 1. 服务启动验证
```powershell
# 1. 访问服务信息
curl http://localhost:8080/

# 2. 健康检查
curl http://localhost:8080/health

# 3. 查看配置
curl http://localhost:8080/config

# 4. 触发一次分析
curl http://localhost:8080/analyze

# 5. 查看结果
curl http://localhost:8080/results
```

### 2. Metrics 导出验证
```powershell
# 访问 metrics 端点
curl http://localhost:8080/metrics

# 检查关键指标
curl http://localhost:8080/metrics | findstr gpu_utilization_score
```

### 3. 日志检查
```powershell
# 查看启动日志
# 应该看到：
# - Prometheus connection established
# - Scheduler started
# - Found X active GPUs
```

### 4. 功能测试
```powershell
# 测试手动分析
curl http://localhost:8080/analyze

# 测试 AI 分析（如果启用）
curl http://localhost:8080/analyze?use_ai=true

# 查看低利用率 GPU
curl http://localhost:8080/results/low

# 查看统计信息
curl http://localhost:8080/results/stats
```

---

## ⚠️ 常见问题检查

### 问题 1: 连接 Prometheus 失败
**检查：**
- [ ] PROM_URL 配置正确
- [ ] 网络连通性
- [ ] Prometheus 服务运行正常

### 问题 2: 查询不到 GPU 数据
**检查：**
- [ ] DCGM exporter 已部署
- [ ] GPU metrics 存在
- [ ] 查询条件正确 `{pod!=""}`

### 问题 3: AI 分析失败
**检查：**
- [ ] AI_ENABLED=true
- [ ] AI_API_URL 正确
- [ ] AI_API_KEY 有效
- [ ] 网络可访问 AI API

### 问题 4: Metrics 未更新
**检查：**
- [ ] 调度器运行正常
- [ ] 最近一次分析时间
- [ ] 是否有错误日志

### 问题 5: 性能问题
**检查：**
- [ ] MAX_WORKERS 是否过大
- [ ] INTERVAL 是否过小
- [ ] GPU 数量是否过多

---

## 📊 监控建议

### 1. Prometheus 抓取配置
```yaml
scrape_configs:
  - job_name: 'gpu-monitor'
    static_configs:
      - targets: ['gpu-monitor:8080']
    metrics_path: '/metrics'
    scrape_interval: 30s
    scrape_timeout: 10s
```

### 2. 告警规则配置
```yaml
groups:
  - name: gpu-monitor-alerts
    rules:
      # 服务不可用
      - alert: GPUMonitorDown
        expr: up{job="gpu-monitor"} == 0
        for: 5m
        
      # 分析失败率高
      - alert: AnalysisErrorRateHigh
        expr: rate(gpu_analysis_errors_total[5m]) > 0.1
        for: 10m
      
      # 低利用率 GPU 过多
      - alert: TooManyIdleGPUs
        expr: gpu_low_utilization_count > 10
        for: 30m
```

### 3. Grafana Dashboard
**推荐面板：**
- GPU 评分分布直方图
- 低利用率 GPU 列表
- 命名空间使用统计
- AI 分析成功率
- 服务性能指标

---

## 🎯 性能优化建议

### 1. 大规模集群（>100 GPU）
```python
MAX_WORKERS = 16  # 增加并发
INTERVAL = 600    # 减少频率
TIME_WINDOW_MIN = 5  # 减小窗口
```

### 2. 启用 AI 分析
```python
INTERVAL = 600  # AI 分析较慢，增加间隔
# 或者分批分析，不是每次都用 AI
```

### 3. 资源受限环境
```python
MAX_WORKERS = 4
INTERVAL = 300
AI_ENABLED = false  # 禁用 AI
```

---

## ✅ 生产环境最终检查

- [ ] 所有配置已验证
- [ ] 服务可正常启动
- [ ] Prometheus 可抓取 metrics
- [ ] 日志输出正常
- [ ] 监控告警已配置
- [ ] 文档已更新
- [ ] 备份方案已准备
- [ ] 回滚方案已准备

---

## 📞 获取帮助

如有问题：
1. 查看日志文件
2. 检查健康检查端点
3. 参考 README.md
4. 提交 Issue

