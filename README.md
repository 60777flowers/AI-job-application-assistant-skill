# AI Job Application Assistant Skill

> 求职投递自动化助手 —— 基于 CodeBuddy Skill 的端到端求职工作流

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Required-blue.svg)](https://www.docker.com/)

---

## 项目简介

这是一个 [CodeBuddy](https://www.codebuddy.ai) Skill，帮助求职者实现从**招聘信息发现**到**简历投递**再到**回复跟踪**的全流程自动化。

### 核心能力

| 能力 | 说明 |
|------|------|
| 公众号RSS监控 | 通过 we-mp-rss 自动获取订阅的招聘公众号最新文章 |
| JD智能分析 | 自动提取岗位信息，根据用户偏好筛选匹配岗位 |
| 多语言支持 | 根据JD语言自动选择中文/英文简历和Cover Letter |
| 邮件自动化 | 通过Gmail SMTP发送带附件的申请邮件 |
| 收件箱监控 | 通过IMAP自动检查面试邀请和公司回复 |
| 投递记录 | 自动记录投递历史，避免重复投递 |
| 定时任务 | 每日自动执行监控、筛选、检查回复 |

### 工作流架构

```
┌─────────────────────────────────────────┐
│ 订阅层：we-mp-rss (Docker)               │
│ - 订阅招聘公众号                          │
│ - 输出RSS feed                           │
└──────────────┬──────────────────────────┘
               ↓
┌─────────────────────────────────────────┐
│ 触发层：CodeBuddy Automation             │
│ - FREQ=DAILY;BYHOUR=9                   │
│ - 每日上午9点自动执行                     │
└──────────────┬──────────────────────────┘
               ↓
┌─────────────────────────────────────────┐
│ 处理层：Job Application Assistant Skill   │
│ 1. fetch_rss_articles.py → 获取文章JSON  │
│ 2. web_fetch → 提取JD信息                │
│ 3. AI筛选 → 匹配求职意向                  │
│ 4. JD语言识别 → 选择简历版本              │
│ 5. 生成Cover Letter                      │
│ 6. 重命名简历附件                         │
│ 7. send_application_email.py → SMTP发送  │
│ 8. check_inbox_replies.py → IMAP检查回复 │
│ 9. 记录到投递记录.csv                     │
└──────────────┬──────────────────────────┘
               ↓
┌─────────────────────────────────────────┐
│ 输出层                                   │
│ - 每日招聘汇总Markdown                    │
│ - 收件箱回复汇总（面试邀请重点标注）        │
│ - 投递状态跟踪表                          │
└─────────────────────────────────────────┘
```

---

## 快速开始

### 1. 环境要求

| 依赖 | 版本要求 | 说明 |
|------|----------|------|
| Python | 3.8+ | 运行脚本 |
| Docker | 20+ | 运行 we-mp-rss |
| CodeBuddy | 最新版 | 运行 Skill 和 Automation |

Python 依赖（标准库，无需额外安装）：
- `smtplib`, `imaplib`, `email` — 邮件发送和接收
- `urllib`, `json`, `xml` — RSS获取和解析
- `argparse`, `os`, `datetime` — 工具库

### 2. 安装步骤

#### 步骤1：安装 Skill

```bash
# 克隆仓库到 CodeBuddy skills 目录
git clone https://github.com/60777flowers/AI-job-application-assistant-skill.git ~/.codebuddy/skills/job-application-assistant
```

#### 步骤2：部署 we-mp-rss

```bash
# 拉取并启动 we-mp-rss 容器
docker run -d \
  --name we-mp-rss \
  -p 8001:8001 \
  -e DB="sqlite:///data/we_mp_rss.db" \
  -e USERNAME="admin" \
  -e PASSWORD="your_password_here" \
  --restart unless-stopped \
  ghcr.io/rachelos/we-mp-rss:latest

# 访问 http://localhost:8001
# 微信扫码登录微信读书
# 添加要订阅的招聘公众号
```

> we-mp-rss 项目地址：https://github.com/rachelos/we-mp-rss

#### 步骤3：配置 Gmail

1. 开启 Google 两步验证
2. 生成应用专用密码（Google账户 > 安全性 > 应用密码）
3. 创建 `gmail_config.txt`：

```
email=your_email@gmail.com
password=your_app_password
```

#### 步骤4：准备简历文件

将中文和英文简历放置到工作目录：
```
your-workspace/
├── resume_zh.pdf    # 中文简历
├── resume_en.pdf    # 英文简历
└── gmail_config.txt # Gmail配置
```

#### 步骤5：创建定时任务

在 CodeBuddy 中创建 Automation：

| 配置项 | 值 |
|--------|-----|
| 名称 | 每日招聘监控与邮件回复检查 |
| 频率 | `FREQ=DAILY;BYHOUR=9;BYMINUTE=0` |
| 工作目录 | 你的简历文件夹路径 |
| 状态 | ACTIVE |

Automation prompt 模板请参考 `SKILL.md` 中的流程说明。

---

## AI Agent 使用指南

### 安装后需要与用户确认的信息

| # | 确认项 | 用途 | 示例 |
|---|--------|------|------|
| 1 | Gmail邮箱地址 | SMTP/IMAP登录 | user@gmail.com |
| 2 | Gmail应用密码 | SMTP/IMAP认证 | xxxx xxxx xxxx xxxx |
| 3 | 中文简历路径 | 中文JD投递 | /path/to/resume_zh.pdf |
| 4 | 英文简历路径 | 英文JD投递 | /path/to/resume_en.pdf |
| 5 | 求职意向 | AI筛选岗位 | 科技/PE/VC/基金等 |
| 6 | 工作地点偏好 | 岗位排序 | 深圳 > 上海 > 北京 |
| 7 | 可实习时间 | Cover Letter内容 | 每周5天，3个月以上 |
| 8 | 排除项 | 过滤不投递的岗位 | 券商投行、纯咨询等 |
| 9 | 邮件命名规则 | 邮件主题格式 | 按招聘方要求命名 |

### 工作流执行

AI Agent 收到用户指令后，按以下顺序执行：

1. **检查服务状态**：`docker ps --filter name=we-mp-rss`
2. **获取文章**：运行 `fetch_rss_articles.py`
3. **筛选岗位**：根据用户偏好AI筛选
4. **展示推荐列表**：输出表格让用户选择
5. **生成Cover Letter**：用户确认后生成
6. **发送邮件**：运行 `send_application_email.py`
7. **检查回复**：运行 `check_inbox_replies.py`
8. **记录投递**：更新 `投递记录.csv`

### 脚本调用方式

```bash
# Windows PowerShell 需先设置编码
$env:PYTHONIOENCODING="utf-8"

# 获取RSS文章
python scripts/fetch_rss_articles.py --limit 15 --output daily_articles.json

# 发送申请邮件
python scripts/send_application_email.py \
  --to "recruit@company.com" \
  --subject "姓名+学校+岗位" \
  --body "Cover Letter正文" \
  --attach "/path/to/resume.pdf"

# 检查收件箱回复
python scripts/check_inbox_replies.py --days 7 --output replies.json
```

---

## 二次开发指南

### 目录结构

```
job-application-assistant/
├── SKILL.md                          # Skill主文档（AI Agent读取）
├── README.md                         # 本文件
├── LICENSE                           # MIT许可证
├── scripts/
│   ├── send_application_email.py     # 邮件发送脚本
│   ├── fetch_rss_articles.py        # RSS文章获取脚本
│   └── check_inbox_replies.py       # 收件箱检查脚本
└── references/
    └── api_reference.md             # we-mp-rss API参考文档
```

### 扩展方向

#### 1. 支持其他邮箱服务

当前仅支持Gmail。扩展其他邮箱需修改：

- `send_application_email.py`：修改SMTP服务器地址和端口
- `check_inbox_replies.py`：修改IMAP服务器地址和端口

常见邮箱配置：

| 邮箱 | SMTP | IMAP |
|------|------|------|
| Gmail | smtp.gmail.com:587 | imap.gmail.com:993 |
| Outlook | smtp.office365.com:587 | outlook.office365.com:993 |
| QQ邮箱 | smtp.qq.com:587 | imap.qq.com:993 |
| 163邮箱 | smtp.163.com:587 | imap.163.com:993 |

#### 2. 支持其他RSS源

当前依赖 we-mp-rss 获取微信公众号文章。可扩展：

- RSSHub：支持更多平台（B站、微博、知乎等）
- 传统RSS源：直接解析XML
- API接入：直接调用招聘平台API

修改 `fetch_rss_articles.py` 中的URL和解析逻辑即可。

#### 3. AI筛选逻辑增强

当前筛选逻辑由 AI Agent 的 prompt 驱动。可扩展：

- 基于向量相似度的岗位匹配
- 基于规则的硬性过滤（薪资、地点、学历要求）
- 历史投递学习（避免推荐相似但不合适的岗位）

#### 4. 多用户支持

当前为单用户设计。多用户扩展需：

- 配置文件分用户管理
- 投递记录按用户隔离
- Gmail配置按用户切换

#### 5. 通知渠道扩展

当前通过 CodeBuddy Automation 推送通知。可扩展：

- 微信推送（Server酱、PushPlus）
- 钉钉/飞书 Webhook
- Telegram Bot

### 脚本API说明

#### send_application_email.py

```python
from send_application_email import send_email

send_email(
    receiver_email="recruit@company.com",
    subject="申请邮件主题",
    body="Cover Letter正文",
    attachment_path="/path/to/resume.pdf",
    sender_email="your@gmail.com",      # 可选，从配置读取
    app_password="your_app_password",    # 可选，从配置读取
)
```

#### fetch_rss_articles.py

```python
from fetch_rss_articles import login, get_mps, get_articles

token = login()
mps = get_mps(token)
for mp in mps:
    articles = get_articles(mp["id"], limit=10)
    for article in articles:
        print(article["title"], article["link"])
```

#### check_inbox_replies.py

```python
from check_inbox_replies import check_inbox

replies = check_inbox(days=7)
for reply in replies:
    if reply["is_interview"]:
        print(f"[面试] {reply['subject']}")
```

---

## 常见问题

### Q: we-mp-rss 无法拉取镜像？
A: 国内网络可能需要配置Docker镜像加速器，或在Docker Desktop中设置代理。

### Q: Gmail SMTP连接超时？
A: 国内访问Gmail需确保网络可达（代理/VPN），或改用国内邮箱（QQ/163）。

### Q: 附件发送后变成空白文件？
A: 必须使用 `MIMEApplication` 而非 `MIMEBase` 处理PDF附件，详见SKILL.md中的故障排查。

### Q: PowerShell执行脚本报编码错误？
A: 先执行 `$env:PYTHONIOENCODING="utf-8"` 设置编码。

### Q: 微信读书登录过期怎么办？
A: 访问 http://localhost:8001 管理后台，重新扫码登录微信读书。

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
