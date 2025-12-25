#!/usr/bin/env python3
"""
Kong 连接诊断工具
用于诊断 Kong Admin API 连接问题
"""
import asyncio
import sys
import httpx
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from config import load_config


async def diagnose_kong():
    """诊断 Kong 连接问题"""
    print("=" * 60)
    print("Kong 连接诊断工具")
    print("=" * 60)
    print()
    
    # 加载配置
    try:
        config = load_config()
        kong_config = config.kong
        print(f"✓ 配置文件加载成功")
        print(f"  - Kong 启用: {kong_config.enabled}")
        print(f"  - Admin URL: {kong_config.admin_url}")
        print(f"  - 超时时间: {kong_config.timeout}秒")
        print()
    except Exception as e:
        print(f"✗ 配置文件加载失败: {e}")
        return
    
    if not kong_config.enabled:
        print("⚠ Kong 集成未启用，请在 config.yaml 中设置 kong.enabled: true")
        return
    
    # 测试连接
    admin_url = kong_config.admin_url.rstrip('/')
    print(f"正在测试连接到: {admin_url}")
    print()
    
    try:
        async with httpx.AsyncClient(timeout=kong_config.timeout) as client:
            # 测试根路径
            print("1. 测试根路径 (/)...")
            try:
                response = await client.get(f"{admin_url}/")
                if response.status_code == 200:
                    data = response.json()
                    version = data.get("version", "unknown")
                    print(f"   ✓ 连接成功！Kong 版本: {version}")
                else:
                    print(f"   ✗ 连接失败: HTTP {response.status_code}")
                    print(f"   响应内容: {response.text[:200]}")
                    return
            except httpx.ConnectError as e:
                print(f"   ✗ 连接错误: {e}")
                print()
                print("   可能的原因:")
                print("   1. Kong 服务未启动")
                print("   2. Admin URL 配置错误")
                print("   3. 网络连接问题")
                print()
                print("   建议:")
                if "localhost" in admin_url or "127.0.0.1" in admin_url:
                    print("   - 如果应用在 Docker 容器中运行，请使用 'http://kong:8001'")
                    print("   - 如果应用在本地运行，请确保 Kong 服务在 localhost:8001 运行")
                else:
                    print(f"   - 请检查 {admin_url} 是否可访问")
                return
            except httpx.TimeoutException as e:
                print(f"   ✗ 连接超时: {e}")
                print("   可能的原因: Kong 服务响应太慢或网络问题")
                return
            except Exception as e:
                print(f"   ✗ 未知错误: {e}")
                return
            
            print()
            
            # 测试 /services 端点
            print("2. 测试 /services 端点...")
            try:
                response = await client.get(f"{admin_url}/services")
                if response.status_code == 200:
                    data = response.json()
                    services = data.get("data", [])
                    print(f"   ✓ 成功！找到 {len(services)} 个服务")
                else:
                    print(f"   ✗ 失败: HTTP {response.status_code}")
                    print(f"   响应内容: {response.text[:200]}")
            except Exception as e:
                print(f"   ✗ 错误: {e}")
            
            print()
            
            # 测试 /routes 端点
            print("3. 测试 /routes 端点...")
            try:
                response = await client.get(f"{admin_url}/routes")
                if response.status_code == 200:
                    data = response.json()
                    routes = data.get("data", [])
                    print(f"   ✓ 成功！找到 {len(routes)} 个路由")
                else:
                    print(f"   ✗ 失败: HTTP {response.status_code}")
            except Exception as e:
                print(f"   ✗ 错误: {e}")
            
            print()
            print("=" * 60)
            print("诊断完成！")
            print("=" * 60)
            
    except Exception as e:
        print(f"✗ 诊断过程出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(diagnose_kong())

