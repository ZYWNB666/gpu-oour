#!/usr/bin/env python3
"""
GPU Monitor 测试脚本

用于测试服务的各个接口功能
"""

import requests
import json
from typing import Dict, Any

BASE_URL = "http://localhost:8080"

def print_section(title: str):
    """打印分隔线"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def test_endpoint(name: str, url: str, method: str = "GET") -> Dict[Any, Any]:
    """测试单个端点"""
    print(f"\n[TEST] {name}")
    print(f"URL: {method} {url}")
    
    try:
        if method == "GET":
            resp = requests.get(url, timeout=10)
        else:
            resp = requests.post(url, timeout=10)
        
        print(f"Status: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
            print("✅ SUCCESS")
            return data
        else:
            print(f"❌ FAILED: {resp.text}")
            return {}
    
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return {}

def main():
    """主测试流程"""
    print_section("GPU Monitor Service - API Tests")
    
    # 1. 测试服务信息
    print_section("1. Service Info")
    test_endpoint("Service Info", f"{BASE_URL}/")
    
    # 2. 测试健康检查
    print_section("2. Health Check")
    test_endpoint("Health Check", f"{BASE_URL}/health")
    
    # 3. 触发分析
    print_section("3. Trigger Analysis")
    test_endpoint("Trigger Analysis", f"{BASE_URL}/analyze")
    
    print("\n⏳ Waiting 3 seconds for analysis to complete...")
    import time
    time.sleep(3)
    
    # 4. 获取分析结果
    print_section("4. Get Results")
    results = test_endpoint("Get Results", f"{BASE_URL}/results")
    
    if results:
        print(f"\n📊 Found {len(results)} GPU(s)")
    
    # 5. 获取低利用率GPU
    print_section("5. Get Low Utilization GPUs")
    low_util = test_endpoint("Low Utilization", f"{BASE_URL}/results/low")
    
    if low_util:
        print(f"\n⚠️  Low utilization count: {low_util.get('count', 0)}")
    
    # 6. 获取统计信息
    print_section("6. Get Statistics")
    stats = test_endpoint("Statistics", f"{BASE_URL}/results/stats")
    
    if stats:
        print(f"\n📈 Summary:")
        print(f"  Total GPUs: {stats.get('total_gpus', 0)}")
        print(f"  Avg Score: {stats.get('avg_score', 0)}%")
        print(f"  Low Utilization: {stats.get('low_utilization_count', 0)}")
    
    print_section("Test Completed")
    print("✅ All tests finished!")

if __name__ == "__main__":
    main()

