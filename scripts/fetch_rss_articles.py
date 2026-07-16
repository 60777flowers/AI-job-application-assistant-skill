#!/usr/bin/env python3
"""
RSS文章获取脚本
从we-mp-rss获取所有订阅公众号的最新文章

用法:
  python fetch_rss_articles.py [--limit 10] [--output articles.json]
"""

import urllib.request
import urllib.parse
import json
import argparse
import xml.etree.ElementTree as ET
from datetime import datetime
import os
import os


WE_MP_RSS_URL = "http://localhost:8001"
API_BASE = "/api/v1/wx"
# 请在部署后修改为你的管理员账号密码
ADMIN_USER = os.environ.get("WERSS_USER", "admin")
ADMIN_PASS = os.environ.get("WERSS_PASS", "admin@123")


def login():
    """登录we-mp-rss获取token"""
    url = f"{WE_MP_RSS_URL}{API_BASE}/auth/login"
    data = urllib.parse.urlencode({
        "username": ADMIN_USER,
        "password": ADMIN_PASS,
    }).encode("utf-8")
    
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    
    with urllib.request.urlopen(req, timeout=10) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    
    if result.get("code") == 0:
        return result["data"]["access_token"]
    else:
        raise Exception(f"登录失败: {result}")


def get_mps(token):
    """获取公众号列表"""
    url = f"{WE_MP_RSS_URL}{API_BASE}/mps"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    
    with urllib.request.urlopen(req, timeout=10) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    
    if result.get("code") == 0:
        return result["data"]["list"]
    else:
        raise Exception(f"获取公众号列表失败: {result}")


def get_articles(feed_id, limit=10):
    """获取公众号文章RSS"""
    url = f"{WE_MP_RSS_URL}/rss/{feed_id}?limit={limit}"
    
    with urllib.request.urlopen(url, timeout=15) as resp:
        xml_content = resp.read().decode("utf-8")
    
    # 解析RSS XML
    root = ET.fromstring(xml_content)
    channel = root.find("channel")
    
    articles = []
    if channel is not None:
        mp_name = channel.findtext("title", "")
        for item in channel.findall("item"):
            article = {
                "mp_name": mp_name,
                "title": item.findtext("title", ""),
                "link": item.findtext("link", ""),
                "description": item.findtext("description", ""),
                "pub_date": item.findtext("pubDate", ""),
                "guid": item.findtext("guid", ""),
            }
            articles.append(article)
    
    return articles


def main():
    parser = argparse.ArgumentParser(description="获取we-mp-rss文章")
    parser.add_argument("--limit", type=int, default=10, help="每个公众号获取的文章数量")
    parser.add_argument("--output", default=None, help="输出文件路径（默认输出到stdout）")
    args = parser.parse_args()
    
    try:
        # 登录
        print("登录we-mp-rss...")
        token = login()
        print("✅ 登录成功")
        
        # 获取公众号列表
        mps = get_mps(token)
        print(f"📋 共订阅 {len(mps)} 个公众号")
        
        all_articles = []
        
        for mp in mps:
            mp_id = mp["id"]
            mp_name = mp.get("mp_name", "未知")
            print(f"\n📰 获取 [{mp_name}] 的文章...")
            
            try:
                articles = get_articles(mp_id, limit=args.limit)
                print(f"   获取到 {len(articles)} 篇文章")
                all_articles.extend(articles)
                
                for art in articles[:3]:  # 只显示前3篇
                    print(f"   - {art['title']} ({art['pub_date']})")
                if len(articles) > 3:
                    print(f"   ... 还有 {len(articles) - 3} 篇")
            except Exception as e:
                print(f"   ❌ 获取失败: {e}")
        
        # 输出结果
        result = {
            "fetch_time": datetime.now().isoformat(),
            "total_mps": len(mps),
            "total_articles": len(all_articles),
            "articles": all_articles,
        }
        
        output = json.dumps(result, ensure_ascii=False, indent=2)
        
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output)
            print(f"\n💾 结果已保存到: {args.output}")
        else:
            print(f"\n📄 共获取 {len(all_articles)} 篇文章")
        
        return all_articles
    
    except Exception as e:
        print(f"❌ 错误: {e}")
        return []


if __name__ == "__main__":
    main()
