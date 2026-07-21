#!/usr/bin/env python3
"""
JD 分析器 — 使用 LLM 从微信公众号文章中提取 JD 信息并生成 Cover Letter

流程:
  1. 抓取微信文章 HTML，提取正文
  2. LLM 分析：判断是否为招聘信息，提取公司/岗位/要求/邮箱等
  3. LLM 生成 Cover Letter（基于用户背景）
  4. 返回结构化投递任务数据
"""

import re
import json
import urllib.request
import urllib.error
from html.parser import HTMLParser

from llm_client import LLMClient


# ── HTML 正文提取 ────────────────────────────────────────

class _TextExtractor(HTMLParser):
    """简单的 HTML 文本提取器"""

    def __init__(self):
        super().__init__()
        self.text_parts = []
        self._skip = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self._skip = True

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript"):
            self._skip = False
        if tag in ("p", "div", "br", "section", "h1", "h2", "h3", "li"):
            self.text_parts.append("\n")

    def handle_data(self, data):
        if not self._skip:
            self.text_parts.append(data)


def fetch_article_text(url, timeout=15):
    """
    抓取微信文章 URL，返回正文文本。
    如果抓取失败，返回空字符串（调用方可降级用 RSS description）。
    """
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            html = resp.read().decode("utf-8", errors="replace")

        # 微信文章正文在 id="js_content" 的 div 中
        match = re.search(r'id="js_content"[^>]*>(.*?)</div>\s*(?:<div|<script)', html, re.S)
        if match:
            html_fragment = match.group(1)
        else:
            # 降级：取整个 body
            body_match = re.search(r'<body[^>]*>(.*?)</body>', html, re.S)
            html_fragment = body_match.group(1) if body_match else html

        extractor = _TextExtractor()
        extractor.feed(html_fragment)
        text = "".join(extractor.text_parts)
        # 清理多余空行
        text = re.sub(r'\n{3,}', '\n\n', text).strip()
        # 限制长度（避免超出 LLM token 限制）
        if len(text) > 8000:
            text = text[:8000] + "\n...(内容过长，已截断)"
        return text
    except Exception as e:
        return ""


# ── LLM 分析 ────────────────────────────────────────────

def analyze_article(article, llm_client, user_profile):
    """
    分析单篇文章，返回投递任务 dict 或 None（不是招聘信息时）

    Args:
        article: {"title":..., "link":..., "description":..., "pub_date":..., "mp_name":...}
        llm_client: LLMClient 实例
        user_profile: 用户背景信息 dict

    Returns:
        dict (投递任务) 或 None
    """
    title = article.get("title", "")
    link = article.get("link", "")
    description = article.get("description", "")
    mp_name = article.get("mp_name", "")

    # 抓取文章正文
    article_text = fetch_article_text(link)
    if not article_text:
        article_text = description or title

    # ── 第一步：判断是否为招聘信息 + 提取JD ──
    jd_prompt = f"""你是一个招聘信息分析助手。请分析以下微信公众号文章，判断是否为招聘信息（实习/校招/社招）。

如果是招聘信息，请提取以下字段并以 JSON 格式返回：
{{
  "is_recruitment": true,
  "company": "公司名称",
  "position": "岗位名称",
  "location": "工作地点（没有则为空字符串）",
  "jd_summary": "一句话概述岗位",
  "jd_detail": "岗位职责（完整原文）",
  "requirements": "任职要求（完整原文）",
  "receiver_email": "投递邮箱（如果文章中有明确邮箱地址则填写，否则为空字符串）",
  "email_subject_format": "邮件主题命名要求（如文章中提及）",
  "match_score": 1到5的整数，表示与用户背景的匹配度,
  "is_english_jd": true或false，JD是否为英文
}}

如果不是招聘信息，返回：
{{"is_recruitment": false}}

用户背景：{user_profile.get('education', '')}，求职意向：{user_profile.get('job_preferences', '')}，排除项：{user_profile.get('excluded', '')}

文章标题：{title}
来源公众号：{mp_name}
文章正文：
{article_text}

请只返回 JSON，不要有其他内容。"""

    messages = [
        {"role": "system", "content": "你是招聘信息分析助手，只返回JSON格式数据。"},
        {"role": "user", "content": jd_prompt},
    ]

    try:
        jd_result = llm_client.chat_json(messages, temperature=0.1, max_tokens=2048, timeout=60)
    except Exception as e:
        return {"error": f"LLM分析失败: {e}", "title": title, "link": link}

    if not jd_result.get("is_recruitment", False):
        return None

    # ── 第二步：生成 Cover Letter ──
    is_english = jd_result.get("is_english_jd", False)
    resume_version = "en" if is_english else "zh"

    # 如果邮箱为空，说明需要用户手动获取
    receiver_email = jd_result.get("receiver_email", "")

    # 生成 Cover Letter
    lang_instruction = "Please write the cover letter in English." if is_english else "请用中文撰写申请信。"

    cl_prompt = f"""你是一个求职申请信撰写助手。请根据以下信息撰写一封简洁、专业的Cover Letter。

{lang_instruction}

申请岗位信息：
- 公司：{jd_result.get('company', '')}
- 岗位：{jd_result.get('position', '')}
- 岗位职责：{jd_result.get('jd_detail', '')}
- 任职要求：{jd_result.get('requirements', '')}

申请人背景：
- 姓名：{user_profile.get('name', '')}
- 教育背景：{user_profile.get('education', '')}
- 求职意向：{user_profile.get('job_preferences', '')}
- 可实习时间：{user_profile.get('available_time', '')}

要求：
1. 简洁有力，不超过300字
2. 突出与岗位要求的匹配点
3. 语气专业、诚恳
4. 直接输出信件正文，不要加"Dear"等前缀解释
5. 末尾署名：{user_profile.get('name', '')}"""

    cl_messages = [
        {"role": "system", "content": "你是求职申请信撰写助手。"},
        {"role": "user", "content": cl_prompt},
    ]

    try:
        cover_letter = llm_client.chat(cl_messages, temperature=0.7, max_tokens=1024, timeout=60)
    except Exception as e:
        cover_letter = f"（Cover Letter 生成失败: {e}）"

    # 构建邮件主题
    subject_format = jd_result.get("email_subject_format", "")
    if subject_format:
        subject = subject_format
    else:
        # 默认格式：姓名+本科院校+研究生院校+专业+年级+毕业时间
        subject = user_profile.get("email_subject_format", f"{user_profile.get('name', '')}+简历")

    # 返回投递任务
    return {
        "company": jd_result.get("company", ""),
        "position": jd_result.get("position", ""),
        "location": jd_result.get("location", ""),
        "jd_summary": jd_result.get("jd_summary", ""),
        "jd_detail": jd_result.get("jd_detail", ""),
        "requirements": jd_result.get("requirements", ""),
        "receiver_email": receiver_email,
        "subject": subject,
        "cover_letter": cover_letter,
        "resume_version": resume_version,
        "match_score": jd_result.get("match_score", 3),
        "source_url": link,
        "source_mp": mp_name,
        "email_subject_format": subject_format,
    }
