#!/usr/bin/env python3
"""
求职邮件发送脚本
通过Gmail SMTP发送带PDF附件的求职申请邮件

用法:
  python send_application_email.py --to email@example.com --subject "邮件主题" --body "邮件正文" --attach "/path/to/resume.pdf"
"""

import smtplib
import argparse
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication


def load_config(config_path=None):
    """加载Gmail配置"""
    if config_path is None:
        # 尝试从工作目录加载
        possible_paths = [
            os.path.join(os.getcwd(), "gmail_config.txt"),
            os.path.join(os.path.expanduser("~"), "gmail_config.txt"),
        ]
        for p in possible_paths:
            if os.path.exists(p):
                config_path = p
                break
    
    config = {"email": "", "password": ""}
    if config_path and os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("email="):
                    config["email"] = line.split("=", 1)[1].strip()
                elif line.startswith("password=") or line.startswith("app_password="):
                    config["password"] = line.split("=", 1)[1].strip()
    
    if not config["email"] or not config["password"]:
        raise ValueError(
            "Gmail配置缺失！请创建 gmail_config.txt 文件，内容如下：\n"
            "email=your_email@gmail.com\n"
            "password=your_app_password\n"
            "\n"
            "获取应用密码：Google账户 > 安全性 > 两步验证 > 应用密码"
        )
    
    return config


def send_email(receiver_email, subject, body, attachment_path=None, sender_email=None,
               app_password=None, smtp_server="smtp.gmail.com", smtp_port=587):
    """
    发送带附件的邮件

    Args:
        receiver_email: 收件人邮箱
        subject: 邮件主题
        body: 邮件正文
        attachment_path: 附件文件路径（可选）
        sender_email: 发件人邮箱
        app_password: 邮箱应用密码/授权码
        smtp_server: SMTP服务器地址（默认smtp.gmail.com）
        smtp_port: SMTP端口（默认587）
    """
    if sender_email is None or app_password is None:
        config = load_config()
        sender_email = sender_email or config["email"]
        app_password = app_password or config["password"]

    # 创建邮件对象
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject

    # 添加邮件正文
    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    # 添加附件
    if attachment_path and os.path.exists(attachment_path):
        with open(attachment_path, "rb") as attachment:
            part = MIMEApplication(attachment.read(), _subtype="pdf")

        part.add_header(
            'Content-Disposition',
            'attachment',
            filename=('utf-8', '', os.path.basename(attachment_path))
        )
        msg.attach(part)
        print(f"附件已添加: {os.path.basename(attachment_path)} ({os.path.getsize(attachment_path)} bytes)")
    elif attachment_path:
        print(f"警告: 附件文件不存在: {attachment_path}")

    # 发送邮件
    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, app_password)
        text = msg.as_string()
        server.sendmail(sender_email, receiver_email, text)
        server.quit()
        print("✅ 邮件发送成功！")
        print(f"   收件人: {receiver_email}")
        print(f"   主题: {subject}")
        if attachment_path:
            print(f"   附件: {os.path.basename(attachment_path)}")
        return True
    except Exception as e:
        print(f"❌ 邮件发送失败: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="求职邮件发送工具")
    parser.add_argument("--to", required=True, help="收件人邮箱")
    parser.add_argument("--subject", required=True, help="邮件主题")
    parser.add_argument("--body", required=True, help="邮件正文（或@filename读取文件）")
    parser.add_argument("--attach", help="附件文件路径")
    parser.add_argument("--sender", help="发件人邮箱（默认从配置文件读取）")
    parser.add_argument("--password", help="Gmail应用密码（默认从配置文件读取）")
    
    args = parser.parse_args()
    
    # 处理 @filename 语法
    body = args.body
    if body.startswith("@") and os.path.exists(body[1:]):
        with open(body[1:], "r", encoding="utf-8") as f:
            body = f.read()
    
    success = send_email(
        receiver_email=args.to,
        subject=args.subject,
        body=body,
        attachment_path=args.attach,
        sender_email=args.sender,
        app_password=args.password,
    )
    
    exit(0 if success else 1)


if __name__ == "__main__":
    main()
