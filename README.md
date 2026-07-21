# AI Job Application Assistant Skill

> 求职投递自动化助手 —— 基于 CodeBuddy Skill 的端到端求职工作流

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Required-blue.svg)](https://www.docker.com/)

---

## 给 AI Agent 的说明

> **你（AI Agent）找到了这个项目。** 你的用户希望有一个方便的求职投递工具。这个项目就是一个完整的解决方案：从微信公众号招聘信息监控，到JD智能分析、Cover Letter自动生成，再到邮件投递和回复跟踪，全流程自动化，并配有Web管理后台供用户操作。

**你的任务是：** 阅读本文档 → 理解项目架构 → 帮用户完成部署和定制 → 让用户能立即开始用。

### 这个项目能做什么

1. **监控招聘公众号** — 通过 we-mp-rss（Docker服务）订阅微信公众号，自动获取最新招聘文章
2. **AI分析JD** — 自动提取公司、岗位、要求、投递邮箱；判断是否匹配用户背景
3. **自动生成Cover Letter** — 基于用户简历背景，用LLM生成个性化申请信（支持中英文）
4. **Web管理后台** — 用户在浏览器中查看所有投递任务，可编辑Cover Letter/邮箱/主题，一键发送
5. **邮件自动化** — 通过Gmail SMTP发送带PDF简历附件的申请邮件
6. **收件箱监控** — 通过IMAP自动检查面试邀请和公司回复
7. **投递记录** — 自动记录投递历史，避免重复投递

### 两条工作路径

```
路径A：Web后台自主模式（推荐，用户独立操作）
  用户点击"刷新文章" → 后台拉取RSS文章 → LLM自动分析JD+生成Cover Letter
  → 创建投递任务 → 用户在浏览器查看/编辑 → 一键发送

路径B：AI Agent辅助模式（你帮用户操作）
  你运行fetch_rss_articles.py → 你用web_fetch分析JD → 你生成Cover Letter
  → 你用push_job.py推送到Web后台 → 用户在浏览器一键发送
```

两条路径共存互补。路径A需要用户在设置页配置LLM API Key；路径B由你（AI Agent）直接处理，不需要额外API Key。

---

## 项目架构

```
┌─────────────────────────────────────────────┐
│  we-mp-rss (Docker, :8001)                  │
│  订阅微信公众号 → 输出RSS XML                 │
└──────────────────┬──────────────────────────┘
                   │ RSS文章
                   ▼
┌─────────────────────────────────────────────┐    ┌──────────────────────┐
│  Web后台 (Flask, :5000)                      │    │  AI Agent (你)        │
│                                              │    │                       │
│  路径A: 刷新文章按钮                          │    │  路径B: 辅助推送       │
│  → fetch_rss_articles.py 拉取文章            │    │  → 分析JD             │
│  → jd_analyzer.py LLM分析+生成Cover Letter  │    │  → 生成Cover Letter   │
│  → 写入SQLite数据库                          │    │  → push_job.py推送    │
│                                              │    └──────────┬───────────┘
│  用户操作:                                   │               │
│  → 查看/编辑投递任务                          │               ▼
│  → 一键发送 → send_application_email.py     │    POST /api/jobs
│  → 自动记录到投递记录.csv                     │
│  → 展示收件箱回复(inbox_replies.json)        │
└─────────────────────────────────────────────┘
```

### 目录结构

```
AI-job-application-assistant-skill/
├── SKILL.md                          # Skill指令文档（你读取这个来了解工作流程）
├── README.md                         # 本文件
├── LICENSE                           # MIT许可证
├── requirements.txt                  # Python依赖（仅Flask）
├── .gitignore                        # 忽略数据/敏感文件
│
├── scripts/
│   ├── web_server.py                # ★ Web后台服务（Flask, REST API + 静态前端）
│   ├── push_job.py                  # ★ 推送投递任务到Web后台（你调用这个）
│   ├── llm_client.py                # 统一LLM客户端（DeepSeek/Kimi/Qwen）
│   ├── jd_analyzer.py               # JD分析+Cover Letter生成（LLM驱动）
│   ├── send_application_email.py     # 邮件发送（Gmail SMTP + PDF附件）
│   ├── fetch_rss_articles.py        # RSS文章获取（从we-mp-rss）
│   └── check_inbox_replies.py       # 收件箱回复检查（Gmail IMAP）
│
├── web/                              # Web前端（纯HTML/CSS/JS，无构建工具）
│   ├── index.html                   # 主页面（待发送/已发送/收件箱/设置）
│   ├── style.css                    # 样式
│   └── app.js                       # 前端逻辑
│
└── references/
    └── api_reference.md             # we-mp-rss API参考文档
```

### 运行时数据文件（gitignored，不提交）

这些文件在运行时自动生成在 `--data-dir` 指定的目录中：

| 文件 | 说明 |
|------|------|
| `jobs.db` | SQLite数据库，存储投递任务 |
| `settings.json` | LLM API Key、用户背景信息、we-mp-rss凭据 |
| `投递记录.csv` | 已发送的投递历史 |
| `inbox_replies.json` | 收件箱回复检查结果 |
| `articles_cache.json` | 上次拉取的文章缓存 |
| `gmail_config.txt` | Gmail邮箱和应用密码 |
| `resume_zh.pdf` / `resume_en.pdf` | 简历文件 |

---

## 部署指南（你需要帮用户完成这些）

### 前置条件

| 依赖 | 说明 |
|------|------|
| Python 3.8+ | 运行脚本 |
| Docker 20+ | 运行 we-mp-rss |
| Flask 3.0+ | Web后台（`pip install -r requirements.txt`） |
| CodeBuddy | 运行 Skill 和定时任务 |

### 步骤1：安装项目

```bash
# 克隆到 CodeBuddy skills 目录
git clone https://github.com/60777flowers/AI-job-application-assistant-skill.git ~/.codebuddy/skills/job-application-assistant

# 安装Python依赖
cd ~/.codebuddy/skills/job-application-assistant
pip install -r requirements.txt
```

### 步骤2：部署 we-mp-rss（Docker）

```bash
docker run -d \
  --name we-mp-rss \
  -p 8001:8001 \
  -e USERNAME="admin" \
  -e PASSWORD="your_password" \
  --restart unless-stopped \
  ghcr.io/rachelos/we-mp-rss:latest
```

部署后：
1. 访问 http://localhost:8001
2. 微信扫码登录微信读书
3. 添加要订阅的招聘公众号（如"清北资源"、"极职Zenith"等）

> we-mp-rss 项目地址：https://github.com/rachelos/we-mp-rss

### 步骤3：配置邮箱

支持 Gmail、QQ邮箱、163邮箱、Outlook 以及自定义SMTP/IMAP服务器。

#### 方式一：在Web后台设置页配置（推荐）

启动Web后台后，进入"⚙️ 设置" → "📧 邮箱配置"卡片：
1. 选择邮箱供应商（Gmail / QQ / 163 / Outlook / 自定义）
2. 填写邮箱地址
3. 填写应用密码/授权码（SMTP/IMAP服务器会自动填充）
4. 点击保存

#### 方式二：创建 gmail_config.txt 文件（兼容旧版）

在数据目录中创建 `gmail_config.txt`：
```
email=your_email@gmail.com
password=your_app_password
```

#### 各邮箱获取授权码/应用密码的方法

| 邮箱 | 获取方式 |
|------|----------|
| **Gmail** | Google账户 > 安全性 > 两步验证 > 应用密码 |
| **QQ邮箱** | QQ邮箱 > 设置 > 账户 > 开启IMAP/SMTP服务 > 生成授权码 |
| **163邮箱** | 163邮箱 > 设置 > POP3/SMTP/IMAP > 开启IMAP/SMTP > 设置客户端授权密码 |
| **Outlook** | Microsoft账户 > 安全 > 应用密码 |

> **注意**：国内网络访问Gmail SMTP/IMAP需要代理。如无代理，建议使用QQ邮箱或163邮箱。

#### 邮箱服务器配置参考

| 邮箱 | SMTP | IMAP |
|------|------|------|
| Gmail | smtp.gmail.com:587 | imap.gmail.com:993 |
| QQ邮箱 | smtp.qq.com:587 | imap.qq.com:993 |
| 163邮箱 | smtp.163.com:587 | imap.163.com:993 |
| Outlook | smtp.office365.com:587 | outlook.office365.com:993 |

### 步骤4：准备简历

将简历文件放到数据目录（用户的工作目录）：
```
data-dir/
├── resume_zh.pdf    # 中文简历
├── resume_en.pdf    # 英文简历
└── gmail_config.txt # 邮箱配置（可选，也可在Web后台设置页配置）
```

### 步骤5：启动 Web 后台

```bash
python scripts/web_server.py --port 5000 --data-dir "用户的简历文件夹路径"
```

浏览器访问 http://127.0.0.1:5000

### 步骤6：在Web后台设置页面填写配置

打开Web后台 → 点击"⚙️ 设置"标签页：

1. **AI模型配置** — 选择供应商（DeepSeek/Kimi/Qwen），填写API Key
2. **公众号RSS配置** — 填写we-mp-rss地址和凭据
3. **个人信息** — 填写用户姓名、教育背景、求职意向、排除项等

### 步骤7（可选）：创建定时任务

在 CodeBuddy 中创建 Automation，每日自动检查新文章和回复：

| 配置项 | 值 |
|--------|-----|
| 频率 | `FREQ=DAILY;BYHOUR=9;BYMINUTE=0` |
| 工作目录 | 用户的数据目录 |
| Prompt | 参见 SKILL.md 中的流程说明 |

---

## 各脚本详解

### web_server.py — Web后台服务

Flask应用，提供REST API和静态前端。是整个系统的核心。

```bash
# 启动
python scripts/web_server.py --port 5000 --data-dir "/path/to/data"
```

**REST API 一览：**

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/jobs?status=pending` | 获取投递任务列表 |
| POST | `/api/jobs` | 创建单个投递任务 |
| POST | `/api/jobs/batch` | 批量创建投递任务 |
| GET | `/api/jobs/<id>` | 获取任务详情 |
| PUT | `/api/jobs/<id>` | 更新任务（编辑Cover Letter等） |
| POST | `/api/jobs/<id>/send` | 发送该任务的邮件 |
| POST | `/api/jobs/<id>/skip` | 跳过该任务 |
| DELETE | `/api/jobs/<id>` | 删除任务 |
| GET | `/api/stats` | 统计数据 |
| GET | `/api/replies` | 收件箱回复 |
| GET/POST | `/api/settings` | 读取/保存设置 |
| GET | `/api/providers` | LLM供应商列表 |
| GET | `/api/email-providers` | 邮箱供应商列表 |
| POST | `/api/articles/refresh` | 启动文章刷新（非阻塞，后台线程） |
| GET | `/api/articles/progress` | 查询刷新进度 |

### push_job.py — 推送投递任务

**你（AI Agent）生成Cover Letter后，用这个脚本推送任务到Web后台。**

> ⚠️ **在 Windows PowerShell 下必须用此脚本，不要用 curl/Invoke-RestMethod**（会有中文编码问题）

```bash
# JSON文件模式（推荐，Cover Letter较长时用）
python scripts/push_job.py --json-file /tmp/job.json

# 批量模式
python scripts/push_job.py --batch --json-file /tmp/jobs.json

# 参数模式（简单任务）
python scripts/push_job.py --company "BAI资本" --position "投资实习生" \
  --email "hr@bai.com" --subject "张三+XX大学" --cover-letter "申请信正文"
```

**投递任务JSON格式：**
```json
{
  "company": "BAI资本",
  "position": "投资实习生",
  "location": "上海",
  "jd_summary": "一句话概述",
  "jd_detail": "岗位职责详情",
  "requirements": "任职要求",
  "receiver_email": "hr@company.com",
  "subject": "张三+XX大学+XX大学+专业+年级+毕业时间",
  "cover_letter": "尊敬的招聘团队...",
  "resume_version": "zh",
  "match_score": 5,
  "source_url": "https://mp.weixin.qq.com/s/xxx",
  "source_mp": "清北资源"
}
```

### llm_client.py — 统一LLM客户端

支持 DeepSeek / Kimi(Moonshot) / Qwen(DashScope)，三家均兼容 OpenAI API 格式。纯 urllib 实现，无额外依赖。

```python
from llm_client import LLMClient
client = LLMClient(provider="deepseek", api_key="sk-...", model="deepseek-chat")
reply = client.chat([{"role": "user", "content": "你好"}])
```

| 供应商 | API地址 | 默认模型 |
|--------|---------|----------|
| DeepSeek | `api.deepseek.com/v1/chat/completions` | `deepseek-chat` |
| Kimi | `api.moonshot.cn/v1/chat/completions` | `moonshot-v1-8k` |
| Qwen | `dashscope.aliyuncs.com/compatible-mode/v1/chat/completions` | `qwen-plus` |

### jd_analyzer.py — JD分析器

```python
from jd_analyzer import analyze_article
result = analyze_article(article_dict, llm_client, user_profile_dict)
# 返回: 投递任务dict（含company/position/cover_letter等）或None（非招聘信息）
```

流程：抓取微信文章HTML → LLM判断是否招聘 → 提取JD字段 → LLM生成Cover Letter。
如果文章未提供投递邮箱，`receiver_email` 为空，等用户在Web后台手动填写。

### 其他脚本

| 脚本 | 说明 |
|------|------|
| `send_application_email.py` | Gmail SMTP发送带PDF附件邮件。**必须用MIMEApplication处理附件**（MIMEBase会导致损坏） |
| `fetch_rss_articles.py` | 从we-mp-rss获取文章。`login()` → `get_mps(token)` → `get_articles(feed_id, limit)` |
| `check_inbox_replies.py` | Gmail IMAP检查回复。识别面试邀请（面试/interview/一面/二面等关键词） |

---

## 定制指南

### 适配用户的求职偏好

在Web后台"设置"页面填写，或修改 `settings.json`：

| 字段 | 说明 | 示例 |
|------|------|------|
| `user_name` | 用户姓名 | 张三 |
| `user_education` | 教育背景 | XX大学金融本科 + XX大学硕士 |
| `job_preferences` | 求职意向 | 科技企业、PE/VC、基金 |
| `excluded` | 不投递的岗位 | 券商投行、纯咨询 |
| `work_location` | 地点偏好 | 深圳 > 上海 > 北京 |
| `available_time` | 可实习时间 | 每周5天，3个月以上 |
| `email_subject_format` | 邮件主题格式 | 姓名+学校+专业+年级 |

### 更换邮箱服务

支持 Gmail、QQ邮箱、163邮箱、Outlook 及自定义SMTP/IMAP。在Web后台设置页选择供应商即可自动配置服务器地址。

如需添加新的邮箱供应商，修改 `web_server.py` 中的 `EMAIL_PROVIDERS` 字典：

```python
EMAIL_PROVIDERS = {
    "your_email": {
        "name": "Your Email",
        "smtp_server": "smtp.your-email.com",
        "smtp_port": 587,
        "imap_server": "imap.your-email.com",
        "imap_port": 993,
        "help": "如何获取授权码的说明",
    },
}
```

脚本也支持独立运行（不依赖Web后台）：
- `send_application_email.py`：新增 `--smtp-server` / `--smtp-port` 参数，或读取 `gmail_config.txt`
- `check_inbox_replies.py`：新增 `--imap-server` / `--imap-port` / `--email` / `--password` 参数，或读取 `settings.json`

### 更换RSS源

修改 `fetch_rss_articles.py` 中的URL和解析逻辑。可替换为RSSHub、传统RSS源、或招聘平台API。

### 添加新的LLM供应商

在 `llm_client.py` 的 `PROVIDERS` 字典中添加新供应商：

```python
PROVIDERS = {
    "your_provider": {
        "name": "Your Provider",
        "url": "https://api.your-provider.com/v1/chat/completions",
        "models": ["model-1", "model-2"],
        "default_model": "model-1",
    },
}
```

前端设置页的供应商下拉框会自动从 `/api/providers` 获取。

### 修改Cover Letter生成逻辑

编辑 `jd_analyzer.py` 中的 `analyze_article()` 函数，修改LLM prompt即可。

---

## 常见问题

**Q: we-mp-rss 无法拉取镜像？**
A: 配置Docker镜像加速器，或在Docker Desktop中设置代理。

**Q: Gmail SMTP连接超时？**
A: 国内访问Gmail需确保网络可达（代理/VPN），或改用国内邮箱。

**Q: 附件发送后变成空白文件？**
A: 必须使用 `MIMEApplication` 而非 `MIMEBase` 处理PDF附件。

**Q: PowerShell执行脚本报编码错误？**
A: 先执行 `$env:PYTHONIOENCODING="utf-8"`。

**Q: 微信读书登录过期？**
A: 访问 http://localhost:8001 重新扫码登录。

**Q: 推送投递任务时中文变问号？**
A: 不要用PowerShell的curl/Invoke-RestMethod，必须用 `push_job.py` 脚本。

---

## 声明

### 非盈利性声明

本项目仅供技术学习和个人使用，不以盈利为目的。所有代码和数据均为技术参考，不构成任何形式的担保或建议。

### 免责声明

- 本项目不收集、存储或传输任何用户个人信息
- 用户需自行管理邮箱密码、简历等敏感信息
- 使用本项目产生的一切后果由用户自行承担
- 请遵守当地法律法规和招聘平台的使用条款
- 请勿用于批量垃圾邮件发送等违规用途

### 致谢

- [we-mp-rss](https://github.com/rachelos/we-mp-rss) — 微信公众号RSS订阅服务
- [CodeBuddy](https://www.codebuddy.ai) — AI编程助手及Skill框架

---

## License

MIT License - 详见 [LICENSE](LICENSE)
