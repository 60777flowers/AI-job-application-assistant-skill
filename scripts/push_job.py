#!/usr/bin/env python3
"""
推送投递任务到 Web 管理后台
AI Agent 通过此脚本将分析好的投递任务写入Web后台，避免PowerShell编码问题。

用法1 — 单个任务（参数模式）:
  python scripts/push_job.py --company "BAI资本" --position "投资实习生" --email "hr@bai.com" --subject "主题" --cover-letter "正文"

用法2 — 单个任务（JSON文件模式，推荐）:
  python scripts/push_job.py --json-file job.json

用法3 — 批量任务（JSON文件模式）:
  python scripts/push_job.py --batch --json-file jobs.json

JSON文件格式（单个）:
  {
    "company": "BAI资本",
    "position": "投资实习生",
    "location": "上海",
    "receiver_email": "hr@bai.com",
    "subject": "张三+XX大学+XX大学",
    "cover_letter": "尊敬的...",
    "jd_summary": "摘要",
    "jd_detail": "详情",
    "requirements": "要求",
    "resume_version": "zh",
    "match_score": 5,
    "source_url": "https://...",
    "source_mp": "清北资源"
  }

JSON文件格式（批量）:
  {"jobs": [{...}, {...}]}
"""

import argparse
import json
import sys
import urllib.request
import urllib.error

DEFAULT_URL = "http://127.0.0.1:5000"


def post_json(url, data):
    """发送JSON POST请求，返回响应"""
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return True, result
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        try:
            err_msg = json.loads(err_body).get("error", err_body)
        except (json.JSONDecodeError, ValueError):
            err_msg = err_body
        return False, {"error": err_msg}
    except urllib.error.URLError as e:
        return False, {"error": f"无法连接Web后台: {e.reason}（请确认 web_server.py 正在运行）"}


def main():
    parser = argparse.ArgumentParser(description="推送投递任务到Web管理后台")
    parser.add_argument("--server", default=DEFAULT_URL, help="Web后台地址（默认 http://127.0.0.1:5000）")
    parser.add_argument("--json-file", help="从JSON文件读取任务数据（推荐，避免编码问题）")
    parser.add_argument("--batch", action="store_true", help="批量模式（需配合 --json-file）")
    parser.add_argument("--company", help="公司名称")
    parser.add_argument("--position", help="岗位名称")
    parser.add_argument("--location", help="工作地点")
    parser.add_argument("--email", dest="receiver_email", help="投递邮箱")
    parser.add_argument("--subject", help="邮件主题")
    parser.add_argument("--cover-letter", help="Cover Letter正文")
    parser.add_argument("--jd-summary", help="JD摘要")
    parser.add_argument("--jd-detail", help="JD详情")
    parser.add_argument("--requirements", help="任职要求")
    parser.add_argument("--resume-version", default="zh", choices=["zh", "en"], help="简历版本")
    parser.add_argument("--match-score", type=int, default=3, help="匹配度1-5")
    parser.add_argument("--source-url", help="来源文章URL")
    parser.add_argument("--source-mp", help="来源公众号")
    args = parser.parse_args()

    # JSON文件模式
    if args.json_file:
        with open(args.json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        if args.batch:
            url = f"{args.server}/api/jobs/batch"
        else:
            url = f"{args.server}/api/jobs"
        ok, result = post_json(url, data)
    else:
        # 参数模式
        if not args.company or not args.position:
            parser.error("参数模式需要至少 --company 和 --position（或使用 --json-file）")
        job = {
            "company": args.company,
            "position": args.position,
            "location": args.location or "",
            "receiver_email": args.receiver_email or "",
            "subject": args.subject or "",
            "cover_letter": args.cover_letter or "",
            "jd_summary": args.jd_summary or "",
            "jd_detail": args.jd_detail or "",
            "requirements": args.requirements or "",
            "resume_version": args.resume_version,
            "match_score": args.match_score,
            "source_url": args.source_url or "",
            "source_mp": args.source_mp or "",
        }
        url = f"{args.server}/api/jobs"
        ok, result = post_json(url, job)

    if ok:
        print("✅ " + result.get("message", "成功"))
        if "id" in result:
            print(f"   任务ID: {result['id']}")
        if "count" in result:
            print(f"   共 {result['count']} 个任务")
    else:
        print("❌ " + result.get("error", "失败"), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
