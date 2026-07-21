#!/usr/bin/env python3
"""
求职投递 Web 管理后台
提供 REST API 供 AI Agent 写入投递任务、供前端一键发送邮件。

用法:
  python scripts/web_server.py [--port 5000] [--host 127.0.0.1] [--data-dir .]

首次运行前请安装依赖:
  pip install flask
"""

import os
import sys
import json
import csv
import sqlite3
import argparse
import threading
from datetime import datetime

from flask import Flask, request, jsonify, send_from_directory

# ── 路径常量 ──────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
WEB_DIR = os.path.join(PROJECT_DIR, "web")

# 将 scripts 目录加入 path，方便复用现有模块
sys.path.insert(0, SCRIPT_DIR)

app = Flask(__name__, static_folder=None)


# ── 数据库 ────────────────────────────────────────────────
def get_db_path():
    return os.path.join(app.config["DATA_DIR"], "jobs.db")


def get_db():
    db = sqlite3.connect(get_db_path())
    db.row_factory = sqlite3.Row
    return db


def init_db():
    db = get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS jobs (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            company       TEXT NOT NULL,
            position      TEXT NOT NULL,
            location      TEXT DEFAULT '',
            jd_summary    TEXT DEFAULT '',
            jd_detail     TEXT DEFAULT '',
            requirements  TEXT DEFAULT '',
            receiver_email TEXT DEFAULT '',
            subject       TEXT DEFAULT '',
            cover_letter  TEXT DEFAULT '',
            resume_version TEXT DEFAULT 'zh',
            match_score   INTEGER DEFAULT 3,
            source_url    TEXT DEFAULT '',
            source_mp     TEXT DEFAULT '',
            status        TEXT DEFAULT 'pending',
            created_at    TEXT,
            sent_at       TEXT DEFAULT '',
            error_message TEXT DEFAULT ''
        );
    """)
    db.commit()
    db.close()


# ── 简历路径查找 ──────────────────────────────────────────
def find_resume(version):
    """在数据目录和项目目录下查找简历文件"""
    names = [f"resume_{version}.pdf", f"简历_{version}.pdf"]
    search_dirs = [app.config["DATA_DIR"], PROJECT_DIR, os.getcwd()]
    for d in search_dirs:
        for name in names:
            path = os.path.join(d, name)
            if os.path.exists(path):
                return path
    return None


# ── 投递记录 CSV ─────────────────────────────────────────
RECORD_CSV_FIELDS = [
    "日期", "公司", "岗位", "工作地点", "投递邮箱",
    "邮件主题", "简历版本", "状态",
]


def append_record(job):
    """将已发送的投递追加到 投递记录.csv"""
    csv_path = os.path.join(app.config["DATA_DIR"], "投递记录.csv")
    file_exists = os.path.exists(csv_path)
    with open(csv_path, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=RECORD_CSV_FIELDS)
        if not file_exists:
            writer.writeheader()
        writer.writerow({
            "日期": job["sent_at"] or datetime.now().strftime("%Y-%m-%d %H:%M"),
            "公司": job["company"],
            "岗位": job["position"],
            "工作地点": job["location"],
            "投递邮箱": job["receiver_email"],
            "邮件主题": job["subject"],
            "简历版本": job["resume_version"],
            "状态": "已发送",
        })


# ══════════════════════════════════════════════════════════
#  REST API
# ══════════════════════════════════════════════════════════

@app.route("/api/jobs", methods=["GET"])
def list_jobs():
    """获取投递任务列表，支持 ?status=pending|sent|all"""
    status = request.args.get("status", "all")
    db = get_db()
    if status == "all":
        rows = db.execute("SELECT * FROM jobs ORDER BY id DESC").fetchall()
    else:
        rows = db.execute(
            "SELECT * FROM jobs WHERE status=? ORDER BY id DESC", (status,)
        ).fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/jobs", methods=["POST"])
def create_job():
    """AI Agent 创建新的投递任务"""
    data = request.get_json(force=True)
    required = ["company", "position"]
    for field in required:
        if not data.get(field):
            return jsonify({"error": f"缺少必填字段: {field}"}), 400

    db = get_db()
    cur = db.execute("""
        INSERT INTO jobs (company, position, location, jd_summary, jd_detail,
                          requirements, receiver_email, subject, cover_letter,
                          resume_version, match_score, source_url, source_mp,
                          status, created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?, 'pending', ?)
    """, (
        data.get("company", ""),
        data.get("position", ""),
        data.get("location", ""),
        data.get("jd_summary", ""),
        data.get("jd_detail", ""),
        data.get("requirements", ""),
        data.get("receiver_email", ""),
        data.get("subject", ""),
        data.get("cover_letter", ""),
        data.get("resume_version", "zh"),
        data.get("match_score", 3),
        data.get("source_url", ""),
        data.get("source_mp", ""),
        datetime.now().strftime("%Y-%m-%d %H:%M"),
    ))
    db.commit()
    job_id = cur.lastrowid
    db.close()
    return jsonify({"id": job_id, "message": "投递任务已创建"}), 201


@app.route("/api/jobs/batch", methods=["POST"])
def create_jobs_batch():
    """AI Agent 批量创建投递任务"""
    data = request.get_json(force=True)
    jobs = data.get("jobs", [])
    if not jobs:
        return jsonify({"error": "jobs 列表为空"}), 400

    db = get_db()
    ids = []
    for item in jobs:
        cur = db.execute("""
            INSERT INTO jobs (company, position, location, jd_summary, jd_detail,
                              requirements, receiver_email, subject, cover_letter,
                              resume_version, match_score, source_url, source_mp,
                              status, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?, 'pending', ?)
        """, (
            item.get("company", ""),
            item.get("position", ""),
            item.get("location", ""),
            item.get("jd_summary", ""),
            item.get("jd_detail", ""),
            item.get("requirements", ""),
            item.get("receiver_email", ""),
            item.get("subject", ""),
            item.get("cover_letter", ""),
            item.get("resume_version", "zh"),
            item.get("match_score", 3),
            item.get("source_url", ""),
            item.get("source_mp", ""),
            datetime.now().strftime("%Y-%m-%d %H:%M"),
        ))
        ids.append(cur.lastrowid)
    db.commit()
    db.close()
    return jsonify({"ids": ids, "count": len(ids), "message": f"已创建 {len(ids)} 个投递任务"}), 201


@app.route("/api/jobs/<int:job_id>", methods=["GET"])
def get_job(job_id):
    db = get_db()
    row = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    db.close()
    if not row:
        return jsonify({"error": "任务不存在"}), 404
    return jsonify(dict(row))


@app.route("/api/jobs/<int:job_id>", methods=["PUT"])
def update_job(job_id):
    """更新投递任务（如编辑 Cover Letter、修改邮箱等）"""
    data = request.get_json(force=True)
    allowed = [
        "company", "position", "location", "jd_summary", "jd_detail",
        "requirements", "receiver_email", "subject", "cover_letter",
        "resume_version", "match_score", "source_url", "source_mp", "status",
    ]
    db = get_db()
    row = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    if not row:
        db.close()
        return jsonify({"error": "任务不存在"}), 404

    updates = {k: data[k] for k in allowed if k in data}
    if updates:
        set_clause = ", ".join(f"{k}=?" for k in updates)
        values = list(updates.values()) + [job_id]
        db.execute(f"UPDATE jobs SET {set_clause} WHERE id=?", values)
        db.commit()
    db.close()
    return jsonify({"message": "已更新"})


@app.route("/api/jobs/<int:job_id>", methods=["DELETE"])
def delete_job(job_id):
    db = get_db()
    db.execute("DELETE FROM jobs WHERE id=?", (job_id,))
    db.commit()
    db.close()
    return jsonify({"message": "已删除"})


@app.route("/api/jobs/<int:job_id>/send", methods=["POST"])
def send_job(job_id):
    """一键发送：调用 send_application_email.py 发送邮件"""
    db = get_db()
    row = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    if not row:
        db.close()
        return jsonify({"error": "任务不存在"}), 404

    job = dict(row)
    db.close()

    # 校验必填项
    if not job["receiver_email"]:
        return jsonify({"error": "收件人邮箱为空，请先填写投递邮箱"}), 400
    if not job["subject"]:
        return jsonify({"error": "邮件主题为空"}), 400
    if not job["cover_letter"]:
        return jsonify({"error": "Cover Letter 为空"}), 400

    # 查找简历
    resume_path = find_resume(job["resume_version"])
    if not resume_path:
        return jsonify({
            "error": f"未找到 {job['resume_version']} 版本简历，请将 resume_{job['resume_version']}.pdf 放到数据目录"
        }), 400

    # 调用现有邮件发送模块
    try:
        from send_application_email import send_email
        settings = load_settings()
        success = send_email(
            receiver_email=job["receiver_email"],
            subject=job["subject"],
            body=job["cover_letter"],
            attachment_path=resume_path,
            sender_email=settings.get("email_address", "") or None,
            app_password=settings.get("email_password", "") or None,
            smtp_server=settings.get("smtp_server", "smtp.gmail.com"),
            smtp_port=settings.get("smtp_port", 587),
        )
    except Exception as e:
        success = False
        err_msg = str(e)
    else:
        err_msg = ""

    # 更新数据库
    db = get_db()
    if success:
        sent_at = datetime.now().strftime("%Y-%m-%d %H:%M")
        db.execute(
            "UPDATE jobs SET status='sent', sent_at=?, error_message='' WHERE id=?",
            (sent_at, job_id),
        )
        db.commit()
        db.close()
        # 记录到 CSV
        updated_job = dict(job)
        updated_job["sent_at"] = sent_at
        append_record(updated_job)
        return jsonify({"message": "邮件发送成功！", "sent_at": sent_at})
    else:
        db.execute(
            "UPDATE jobs SET status='failed', error_message=? WHERE id=?",
            (err_msg or "发送失败", job_id),
        )
        db.commit()
        db.close()
        return jsonify({"error": err_msg or "邮件发送失败"}), 500


@app.route("/api/jobs/<int:job_id>/skip", methods=["POST"])
def skip_job(job_id):
    """跳过该投递任务"""
    db = get_db()
    db.execute("UPDATE jobs SET status='skipped' WHERE id=?", (job_id,))
    db.commit()
    db.close()
    return jsonify({"message": "已跳过"})


@app.route("/api/stats", methods=["GET"])
def stats():
    db = get_db()
    pending = db.execute("SELECT COUNT(*) as c FROM jobs WHERE status='pending'").fetchone()["c"]
    sent = db.execute("SELECT COUNT(*) as c FROM jobs WHERE status='sent'").fetchone()["c"]
    failed = db.execute("SELECT COUNT(*) as c FROM jobs WHERE status='failed'").fetchone()["c"]
    skipped = db.execute("SELECT COUNT(*) as c FROM jobs WHERE status='skipped'").fetchone()["c"]
    db.close()
    return jsonify({"pending": pending, "sent": sent, "failed": failed, "skipped": skipped})


@app.route("/api/replies", methods=["GET"])
def get_replies():
    """读取收件箱回复 JSON（由 AI Agent 定期写入 inbox_replies.json）"""
    replies_path = os.path.join(app.config["DATA_DIR"], "inbox_replies.json")
    if os.path.exists(replies_path):
        with open(replies_path, "r", encoding="utf-8") as f:
            return jsonify(json.load(f))
    return jsonify({"replies": [], "message": "暂无回复数据，请先运行 check_inbox_replies.py"})


# ══════════════════════════════════════════════════════════
#  设置管理
# ══════════════════════════════════════════════════════════

DEFAULT_SETTINGS = {
    "llm_provider": "deepseek",
    "llm_api_key": "",
    "llm_model": "",
    "we_mp_rss_url": "http://localhost:8001",
    "we_mp_rss_user": "admin",
    "we_mp_rss_pass": "admin@123",
    "user_name": "",
    "user_education": "",
    "job_preferences": "",
    "excluded": "",
    "work_location": "",
    "available_time": "",
    "email_subject_format": "",
    "email_provider": "gmail",
    "email_address": "",
    "email_password": "",
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "imap_server": "imap.gmail.com",
    "imap_port": 993,
}

# 邮箱供应商预设
EMAIL_PROVIDERS = {
    "gmail": {
        "name": "Gmail",
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "imap_server": "imap.gmail.com",
        "imap_port": 993,
        "help": "Google账户 > 安全性 > 两步验证 > 应用密码",
    },
    "qq": {
        "name": "QQ邮箱",
        "smtp_server": "smtp.qq.com",
        "smtp_port": 587,
        "imap_server": "imap.qq.com",
        "imap_port": 993,
        "help": "QQ邮箱 > 设置 > 账户 > 开启IMAP/SMTP服务 > 生成授权码",
    },
    "163": {
        "name": "163邮箱",
        "smtp_server": "smtp.163.com",
        "smtp_port": 587,
        "imap_server": "imap.163.com",
        "imap_port": 993,
        "help": "163邮箱 > 设置 > POP3/SMTP/IMAP > 开启IMAP/SMTP > 设置客户端授权密码",
    },
    "outlook": {
        "name": "Outlook / Hotmail",
        "smtp_server": "smtp.office365.com",
        "smtp_port": 587,
        "imap_server": "outlook.office365.com",
        "imap_port": 993,
        "help": "Microsoft账户 > 安全 > 应用密码",
    },
    "custom": {
        "name": "自定义",
        "smtp_server": "",
        "smtp_port": 587,
        "imap_server": "",
        "imap_port": 993,
        "help": "手动填写SMTP/IMAP服务器信息",
    },
}


def get_settings_path():
    return os.path.join(app.config["DATA_DIR"], "settings.json")


def load_settings():
    path = get_settings_path()
    settings = dict(DEFAULT_SETTINGS)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            saved = json.load(f)
            settings.update(saved)
    return settings


def save_settings(settings):
    path = get_settings_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)


@app.route("/api/settings", methods=["GET"])
def get_settings():
    settings = load_settings()
    # 脱敏：API key 和邮箱密码只返回是否已设置
    has_key = bool(settings.get("llm_api_key"))
    has_email_pass = bool(settings.get("email_password"))
    safe = dict(settings)
    safe["llm_api_key"] = "***" if has_key else ""
    safe["llm_api_key_set"] = has_key
    safe["email_password"] = "***" if has_email_pass else ""
    safe["email_password_set"] = has_email_pass
    return jsonify(safe)


@app.route("/api/settings", methods=["POST"])
def update_settings():
    data = request.get_json(force=True)
    settings = load_settings()
    for k, v in data.items():
        if k in DEFAULT_SETTINGS:
            # 敏感字段收到 "***" 或空值时保留原值
            if k in ("llm_api_key", "email_password") and (v == "***" or v == ""):
                continue
            settings[k] = v
    save_settings(settings)
    return jsonify({"message": "设置已保存"})


@app.route("/api/providers", methods=["GET"])
def get_providers():
    """返回支持的 LLM 供应商列表"""
    from llm_client import get_provider_info
    return jsonify(get_provider_info())


@app.route("/api/email-providers", methods=["GET"])
def get_email_providers():
    """返回支持的邮箱供应商列表"""
    return jsonify(EMAIL_PROVIDERS)


# ══════════════════════════════════════════════════════════
#  文章刷新 + LLM 分析（线程化 + 进度查询）
# ══════════════════════════════════════════════════════════

_refresh_progress = {
    "running": False,
    "phase": "idle",        # idle / fetching / analyzing / done / error
    "current": 0,
    "total": 0,
    "current_title": "",
    "current_mp": "",
    "created": 0,
    "skipped": 0,
    "errors": [],
    "message": "",
}
_progress_lock = threading.Lock()


def _do_refresh(limit, do_analyze, settings):
    """后台线程：拉取文章 + LLM 分析"""
    def update(**kw):
        with _progress_lock:
            _refresh_progress.update(kw)

    update(phase="fetching", message="正在连接 we-mp-rss 拉取文章...", current=0, total=0,
           created=0, skipped=0, errors=[])

    # 1. 拉取文章
    try:
        from fetch_rss_articles import login, get_mps, get_articles
        import fetch_rss_articles as frss
        frss.WE_MP_RSS_URL = settings.get("we_mp_rss_url", "http://localhost:8001")
        frss.ADMIN_USER = settings.get("we_mp_rss_user", "admin")
        frss.ADMIN_PASS = settings.get("we_mp_rss_pass", "admin@123")

        token = login()
        mps = get_mps(token)
        all_articles = []
        for mp in mps:
            articles = get_articles(mp["id"], limit=limit)
            for a in articles:
                a["mp_name"] = mp.get("mp_name", "")
            all_articles.extend(articles)
    except Exception as e:
        update(phase="error", running=False, message=f"拉取文章失败: {e}")
        return

    # 保存文章缓存
    articles_path = os.path.join(app.config["DATA_DIR"], "articles_cache.json")
    with open(articles_path, "w", encoding="utf-8") as f:
        json.dump({
            "fetch_time": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "total": len(all_articles),
            "articles": all_articles,
        }, f, ensure_ascii=False, indent=2)

    if not do_analyze or len(all_articles) == 0:
        update(phase="done", running=False, total=len(all_articles),
               message=f"已拉取 {len(all_articles)} 篇文章")
        return

    # 2. LLM 分析
    update(phase="analyzing", total=len(all_articles), current=0,
           message=f"正在用AI分析 {len(all_articles)} 篇文章...")

    from llm_client import LLMClient
    from jd_analyzer import analyze_article

    user_profile = {
        "name": settings.get("user_name", ""),
        "education": settings.get("user_education", ""),
        "job_preferences": settings.get("job_preferences", ""),
        "excluded": settings.get("excluded", ""),
        "work_location": settings.get("work_location", ""),
        "available_time": settings.get("available_time", ""),
        "email_subject_format": settings.get("email_subject_format", ""),
    }

    llm = LLMClient(
        provider=settings.get("llm_provider", "deepseek"),
        api_key=settings.get("llm_api_key", ""),
        model=settings.get("llm_model", "") or None,
    )

    db = get_db()
    existing_urls = set(
        row[0] for row in db.execute("SELECT source_url FROM jobs WHERE source_url != ''").fetchall()
    )

    created = 0
    skipped = 0
    errors = []

    for i, article in enumerate(all_articles):
        link = article.get("link", "")
        title = article.get("title", "")
        mp_name = article.get("mp_name", "")

        update(current=i + 1, current_title=title, current_mp=mp_name,
               created=created, skipped=skipped)

        # 去重
        if link and link in existing_urls:
            skipped += 1
            update(skipped=skipped)
            continue

        try:
            result = analyze_article(article, llm, user_profile)
        except Exception as e:
            errors.append(f"{title}: {e}")
            update(errors=list(errors))
            continue

        if result is None:
            skipped += 1
            update(skipped=skipped)
            continue

        if "error" in result:
            errors.append(f"{title}: {result['error']}")
            update(errors=list(errors))
            continue

        db.execute("""
            INSERT INTO jobs (company, position, location, jd_summary, jd_detail,
                              requirements, receiver_email, subject, cover_letter,
                              resume_version, match_score, source_url, source_mp,
                              status, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?, 'pending', ?)
        """, (
            result.get("company", ""),
            result.get("position", ""),
            result.get("location", ""),
            result.get("jd_summary", ""),
            result.get("jd_detail", ""),
            result.get("requirements", ""),
            result.get("receiver_email", ""),
            result.get("subject", ""),
            result.get("cover_letter", ""),
            result.get("resume_version", "zh"),
            result.get("match_score", 3),
            result.get("source_url", ""),
            result.get("source_mp", ""),
            datetime.now().strftime("%Y-%m-%d %H:%M"),
        ))
        db.commit()
        existing_urls.add(link)
        created += 1
        update(created=created)

    db.close()

    msg = f"完成！共 {len(all_articles)} 篇，创建 {created} 个任务，跳过 {skipped} 篇"
    update(phase="done", running=False, current=len(all_articles),
           created=created, skipped=skipped, message=msg)


@app.route("/api/articles/refresh", methods=["POST"])
def refresh_articles():
    """启动后台文章刷新（非阻塞），返回后前端轮询 /api/articles/progress"""
    with _progress_lock:
        if _refresh_progress["running"]:
            return jsonify({"error": "刷新正在进行中，请等待完成"}), 409

    data = request.get_json(silent=True) or {}
    limit = data.get("limit", 10)
    do_analyze = data.get("analyze", True)
    settings = load_settings()

    if do_analyze and not settings.get("llm_api_key"):
        return jsonify({"error": "LLM API Key 未配置，请先在设置页面填写"}), 400

    # 启动后台线程
    with _progress_lock:
        _refresh_progress.update({
            "running": True, "phase": "fetching", "current": 0, "total": 0,
            "current_title": "", "current_mp": "", "created": 0, "skipped": 0,
            "errors": [], "message": "正在启动...",
        })

    t = threading.Thread(target=_do_refresh, args=(limit, do_analyze, settings), daemon=True)
    t.start()

    return jsonify({"message": "刷新已启动", "total_estimate": limit})


@app.route("/api/articles/progress", methods=["GET"])
def articles_progress():
    """查询文章刷新进度"""
    with _progress_lock:
        return jsonify(dict(_refresh_progress))


@app.route("/api/articles", methods=["GET"])
def get_articles():
    """获取上次拉取的文章列表"""
    articles_path = os.path.join(app.config["DATA_DIR"], "articles_cache.json")
    if os.path.exists(articles_path):
        with open(articles_path, "r", encoding="utf-8") as f:
            return jsonify(json.load(f))
    return jsonify({"total": 0, "articles": [], "message": "暂无文章数据，请点击刷新"})


# ══════════════════════════════════════════════════════════
#  静态文件 — 提供前端页面
# ══════════════════════════════════════════════════════════

@app.route("/")
def index():
    return send_from_directory(WEB_DIR, "index.html")


@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory(WEB_DIR, filename)


# ══════════════════════════════════════════════════════════
#  入口
# ══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="求职投递 Web 管理后台")
    parser.add_argument("--port", type=int, default=5000, help="端口号（默认5000）")
    parser.add_argument("--host", default="127.0.0.1", help="监听地址（默认127.0.0.1）")
    parser.add_argument(
        "--data-dir",
        default=os.getcwd(),
        help="数据目录（存放 jobs.db、投递记录.csv、简历等，默认当前目录）",
    )
    args = parser.parse_args()

    app.config["DATA_DIR"] = os.path.abspath(args.data_dir)
    init_db()

    print("=" * 50)
    print("  求职投递 Web 管理后台")
    print("=" * 50)
    print(f"  数据目录: {app.config['DATA_DIR']}")
    print(f"  数据库:   {get_db_path()}")
    print(f"  Web目录:  {WEB_DIR}")
    print(f"  访问地址: http://{args.host}:{args.port}")
    print("=" * 50)

    app.run(host=args.host, port=args.port, debug=True)


if __name__ == "__main__":
    main()
