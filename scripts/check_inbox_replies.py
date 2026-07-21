#!/usr/bin/env python3
"""
Gmail收件箱求职回复检查脚本
通过IMAP读取Gmail收件箱，搜索投递公司的回复邮件

用法:
  python check_inbox_replies.py [--days 7] [--output replies.json]
"""

import imaplib
import email
import email.header
import json
import argparse
import os
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime


# 邮箱配置 - 通过环境变量、命令行参数或settings.json读取
GMAIL_USER = os.environ.get("GMAIL_USER", "")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")
IMAP_SERVER = os.environ.get("IMAP_SERVER", "imap.gmail.com")
IMAP_PORT = int(os.environ.get("IMAP_PORT", "993"))

# 已投递公司邮箱列表（从投递记录.csv动态读取更佳，这里作为示例）
KNOWN_REPLY_EMAILS = [
    # 示例：部署后替换为你投递过的公司邮箱
    # "recruit@example.com",
    # "hr@example.com",
]

# 求职相关关键词
KEYWORDS = ["面试", "offer", "简历", "感谢", "申请", "岗位", "实习", 
            "interview", "application", "resume", "position", "intern"]


def decode_header(header_value):
    """解码邮件头"""
    if not header_value:
        return ""
    decoded = email.header.decode_header(header_value)
    parts = []
    for content, charset in decoded:
        if isinstance(content, bytes):
            try:
                parts.append(content.decode(charset or "utf-8", errors="replace"))
            except (LookupError, TypeError):
                parts.append(content.decode("utf-8", errors="replace"))
        else:
            parts.append(str(content))
    return " ".join(parts)


def extract_email_address(from_header):
    """从From头提取邮箱地址"""
    if "<" in from_header and ">" in from_header:
        start = from_header.index("<") + 1
        end = from_header.index(">")
        return from_header[start:end].lower()
    return from_header.lower()


def get_email_body(msg):
    """提取邮件正文"""
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition", ""))
            if content_type == "text/plain" and "attachment" not in content_disposition:
                try:
                    charset = part.get_content_charset() or "utf-8"
                    payload = part.get_payload(decode=True)
                    body = payload.decode(charset, errors="replace")
                    break
                except Exception:
                    pass
            elif content_type == "text/html" and "attachment" not in content_disposition and not body:
                try:
                    charset = part.get_content_charset() or "utf-8"
                    payload = part.get_payload(decode=True)
                    body = payload.decode(charset, errors="replace")
                except Exception:
                    pass
    else:
        try:
            charset = msg.get_content_charset() or "utf-8"
            payload = msg.get_payload(decode=True)
            body = payload.decode(charset, errors="replace")
        except Exception:
            pass
    return body.strip()[:500]  # 只取前500字符


def check_inbox(days=7, imap_server=None, imap_port=None, email_user=None, email_pass=None):
    """检查邮箱收件箱中的求职回复"""
    imap_server = imap_server or IMAP_SERVER
    imap_port = imap_port or IMAP_PORT
    email_user = email_user or GMAIL_USER
    email_pass = email_pass or GMAIL_APP_PASSWORD

    if not email_user or not email_pass:
        print("错误: 邮箱地址或密码未配置")
        print("请通过以下方式之一配置:")
        print("  1. 环境变量: GMAIL_USER, GMAIL_APP_PASSWORD, IMAP_SERVER, IMAP_PORT")
        print("  2. 命令行参数: --email --password --imap-server --imap-port")
        print("  3. settings.json (Web后台设置页配置)")
        return []

    print(f"连接IMAP服务器 {imap_server}:{imap_port}...")
    
    try:
        mail = imaplib.IMAP4_SSL(imap_server, imap_port)
        mail.login(email_user, email_pass)
        mail.select("inbox")
        print("登录成功")
    except Exception as e:
        print(f"登录失败: {e}")
        return []
    
    # 计算日期范围
    since_date = (datetime.now() - timedelta(days=days)).strftime("%d-%b-%Y")
    
    # 搜索最近N天的邮件
    try:
        status, messages = mail.search(None, f'(SINCE {since_date})')
        if status != "OK":
            print("搜索邮件失败")
            return []
        
        mail_ids = messages[0].split()
        print(f"找到 {len(mail_ids)} 封最近{days}天的邮件")
    except Exception as e:
        print(f"搜索邮件出错: {e}")
        return []
    
    replies = []
    
    for mail_id in mail_ids:
        try:
            status, msg_data = mail.fetch(mail_id, "(RFC822)")
            if status != "OK":
                continue
            
            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)
            
            # 提取邮件信息
            from_header = decode_header(msg.get("From", ""))
            subject = decode_header(msg.get("Subject", ""))
            date_str = msg.get("Date", "")
            from_email = extract_email_address(from_header)
            
            # 判断是否为求职相关回复
            is_known_reply = any(known_email in from_email for known_email in KNOWN_REPLY_EMAILS)
            
            # 检查关键词
            body = get_email_body(msg)
            has_keyword = any(kw.lower() in (subject + body).lower() for kw in KEYWORDS)
            
            if is_known_reply or has_keyword:
                # 判断是否为面试邀请
                is_interview = any(kw in (subject + body) for kw in 
                    ["面试", "interview", "一面", "二面", "终面", "群面", 
                     "笔试", "assessment", " Assessment Center"])
                
                reply = {
                    "from": from_header,
                    "from_email": from_email,
                    "subject": subject,
                    "date": date_str,
                    "body_preview": body[:200],
                    "is_known_reply": is_known_reply,
                    "is_interview": is_interview,
                }
                replies.append(reply)
                
                if is_interview:
                    print(f"  [面试邀请] {subject} - {from_header}")
                elif is_known_reply:
                    print(f"  [已知回复] {subject} - {from_header}")
                else:
                    print(f"  [关键词匹配] {subject} - {from_header}")
        
        except Exception as e:
            continue
    
    mail.logout()
    return replies


def main():
    parser = argparse.ArgumentParser(description="邮箱收件箱求职回复检查")
    parser.add_argument("--days", type=int, default=7, help="检查最近N天的邮件")
    parser.add_argument("--output", default=None, help="输出文件路径")
    parser.add_argument("--email", help="邮箱地址（覆盖环境变量）")
    parser.add_argument("--password", help="邮箱应用密码/授权码（覆盖环境变量）")
    parser.add_argument("--imap-server", help="IMAP服务器地址（覆盖环境变量）")
    parser.add_argument("--imap-port", type=int, help="IMAP端口（覆盖环境变量）")
    args = parser.parse_args()

    # 尝试从 settings.json 读取配置（如果环境变量/CLI参数未提供）
    if not args.email and not GMAIL_USER:
        settings_path = os.path.join(os.getcwd(), "settings.json")
        if not os.path.exists(settings_path):
            # 也尝试脚本所在目录的上级
            settings_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "settings.json")
        if os.path.exists(settings_path):
            with open(settings_path, "r", encoding="utf-8") as f:
                s = json.load(f)
            args.email = s.get("email_address", "")
            args.password = s.get("email_password", "")
            args.imap_server = args.imap_server or s.get("imap_server", "")
            args.imap_port = args.imap_port or s.get("imap_port", 993)

    print(f"检查最近 {args.days} 天的收件箱...")
    replies = check_inbox(
        days=args.days,
        imap_server=args.imap_server,
        imap_port=args.imap_port,
        email_user=args.email,
        email_pass=args.password,
    )
    
    print(f"\n找到 {len(replies)} 封求职相关邮件")
    
    # 检查是否有面试邀请
    interviews = [r for r in replies if r["is_interview"]]
    if interviews:
        print(f"\n{'='*50}")
        print(f"有 {len(interviews)} 封面试邀请，请尽快查看！")
        for inv in interviews:
            print(f"  - {inv['subject']} ({inv['from']})")
        print(f"{'='*50}")
    
    # 输出JSON
    result = {
        "check_time": datetime.now().isoformat(),
        "days_checked": args.days,
        "total_replies": len(replies),
        "interview_invitations": len(interviews),
        "replies": replies,
    }
    
    output = json.dumps(result, ensure_ascii=False, indent=2)
    
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"\n结果已保存到: {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
