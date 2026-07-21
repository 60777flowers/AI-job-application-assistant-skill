---
name: job-application-assistant
description: >-
  求职投递自动化助手。当用户需要投递简历、发送求职邮件、监控招聘公众号新文章、
  或提到"投递"、"求职"、"实习"、"招聘"、"cover letter"、"申请信"时触发此skill。
  该skill整合了微信公众号RSS监控、JD智能分析、多语言简历选择、自动化邮件发送等全流程能力。
---

# 求职投递自动化助手

## 概述

本skill为求职者提供端到端的自动化求职投递流程，包括：
1. 通过 we-mp-rss 监控微信公众号招聘文章
2. 自动提取JD关键信息（岗位、公司、要求、投递方式）
3. 根据JD语言智能选择简历版本（中文/英文）和Cover Letter语言
4. **AI Agent将分析好的投递任务推送到Web管理后台**，用户在浏览器中查看、编辑、一键发送
5. 通过Gmail SMTP自动发送带附件的申请邮件（由Web后台触发）
6. 通过IMAP自动检查收件箱中的求职回复（面试邀请等），结果在Web后台展示
7. 记录投递历史，避免重复投递

## Web管理后台（核心交互界面）

本skill提供本地Web管理后台，是AI Agent与用户之间的桥梁：
- **AI Agent** 负责获取JD、分析匹配度、生成Cover Letter，将结果通过API写入数据库
- **用户** 在浏览器中查看所有待发送任务，可编辑Cover Letter/邮箱/主题，确认后一键发送

### 启动Web后台

```bash
# 首次需安装Flask
pip install flask

# 启动服务（--data-dir 指定简历、数据库、投递记录所在目录）
python scripts/web_server.py --port 5000 --data-dir "简历文件夹路径"
```

启动后访问 http://127.0.0.1:5000

### Web后台功能

| 功能 | 说明 |
|------|------|
| 待发送/已发送 | 查看投递任务列表，编辑Cover Letter/邮箱/主题，一键发送 |
| 收件箱回复 | 展示 `inbox_replies.json` 中的求职回复，面试邀请高亮 |
| **设置** | 配置 LLM API Key（DeepSeek/Kimi/Qwen）、用户背景信息、we-mp-rss凭据 |
| **刷新文章** | 一键从公众号拉取最新文章，LLM自动分析JD+生成Cover Letter+创建投递任务 |
| **公众号管理** | 外链跳转到 we-mp-rss 管理后台 (http://localhost:8001)，添加/管理公众号 |

> **刷新文章流程**：用户点击"刷新文章" → 后端调用 `fetch_rss_articles.py` 拉取文章 → 调用 `jd_analyzer.py` 用LLM分析每篇文章 → 非招聘信息自动跳过 → 招聘信息创建投递任务（含Cover Letter）→ 如果JD未提供邮箱则留空，等用户手动填写。

### Web后台 API（供AI Agent调用）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/jobs?status=pending` | 获取待发送任务列表 |
| POST | `/api/jobs` | 创建单个投递任务 |
| POST | `/api/jobs/batch` | 批量创建投递任务 |
| GET | `/api/jobs/<id>` | 获取任务详情 |
| PUT | `/api/jobs/<id>` | 更新任务（编辑Cover Letter等） |
| POST | `/api/jobs/<id>/send` | 发送该任务的邮件 |
| POST | `/api/jobs/<id>/skip` | 跳过该任务 |
| DELETE | `/api/jobs/<id>` | 删除任务 |
| GET | `/api/stats` | 获取统计数据（待发送/已发送/失败数量） |
| GET | `/api/replies` | 获取收件箱回复 |

### 创建投递任务的JSON格式

```json
{
  "company": "BAI资本",
  "position": "投资实习生",
  "location": "上海",
  "jd_summary": "BAI资本招聘投资实习生...",
  "jd_detail": "岗位职责：\n1. 行业研究...\n2. 项目尽职调查...",
  "requirements": "1. 重点大学本科或以上...\n2. 对投资有热情...",
  "receiver_email": "internbai.sh@gmail.com",
  "subject": "张三+XX大学+XX大学+专业+年级+毕业时间",
  "cover_letter": "尊敬的BAI资本招聘团队：\n\n我是XX大学XX专业的硕士研究生...",
  "resume_version": "zh",
  "match_score": 5,
  "source_url": "https://mp.weixin.qq.com/s/xxx",
  "source_mp": "清北资源"
}
```

## 前置条件（需与用户确认）

部署此skill前，需要与用户确认以下信息：

### 1. 硬件与服务依赖
- **Docker Desktop**（Windows/Mac）或 **Docker Engine**（Linux）
- **we-mp-rss** 服务（Docker本地部署，用于微信公众号RSS订阅）
  - 部署方式：`docker run -d --name we-mp-rss -p 8001:8001 ghcr.io/rachelos/we-mp-rss:latest`
  - 管理后台：http://localhost:8001
  - 默认账号：admin / admin@123（请部署后修改）
  - 需用户微信扫码登录微信读书以启用公众号订阅

### 2. Gmail配置
需用户提供：
- Gmail邮箱地址
- Gmail应用专用密码（非登录密码）
  - 获取方式：Google账户 > 安全性 > 两步验证 > 应用密码
- 保存为工作目录下的 `gmail_config.txt`，格式：
  ```
  email=your_email@gmail.com
  password=your_app_password
  ```

### 3. 简历文件
需确认：
- 简历存放路径（工作目录或绝对路径）
- 中文简历文件名（如 `resume_zh.pdf`）
- 英文简历文件名（如 `resume_en.pdf`）

### 4. 用户求职偏好（需逐项确认）
- 求职意向（哪些行业/岗位）
- 工作地点偏好（优先顺序）
- 可实习时间（每周几天，几个月以上）
- 排除项（不投递的岗位类型）
- 邮件主题命名规则（默认按招聘方要求）

## 核心配置

### 服务地址
- **we-mp-rss**: http://localhost:8001
- **API基础路径**: `/api/v1/wx`
- **RSS路径**: `/rss/{feed_id}`（无需认证）
- **管理后台**: 浏览器访问 http://localhost:8001

### Gmail SMTP/IMAP配置
- SMTP服务器：smtp.gmail.com:587 (TLS)
- IMAP服务器：imap.gmail.com:993 (SSL)
- 配置文件：工作目录下 `gmail_config.txt`

### 简历文件
工作目录下存放中文和英文两个版本的简历：
- `resume_zh.pdf` — 中文版
- `resume_en.pdf` — 英文版

### 用户求职偏好（示例，需按用户实际填写）
- **求职意向**：科技企业、PE/VC、基金等
- **工作地点偏好**：深圳 > 上海 > 北京（示例）
- **可实习时间**：每周5天，3个月以上
- **排除项**：券商投行（IPO/FA/承做等）、纯咨询岗位
- **邮件主题命名**：按照招聘方要求命名
- **简历附件**：需重命名为与邮件主题一致
- **语言选择规则**：根据JD语言选择对应语言版本（中文JD→中文简历+中文申请信，英文JD→英文简历+英文Cover Letter）

## 工作流程

### 流程1：监控新招聘文章（定时触发）

1. **获取公众号列表**：调用 `GET /api/v1/wx/mps`（需Bearer token认证）
2. **登录获取token**：`POST /api/v1/wx/auth/login`，body为 `username=admin&password=admin@123`
3. **遍历每个公众号**：调用 `GET /rss/{feed_id}?limit=10` 获取最新文章RSS XML
4. **解析RSS**：提取每篇文章的 title、link（微信文章URL）、pubDate
5. **去重**：与 `投递记录.csv` 对比，跳过已处理的文章
6. **AI筛选**：根据用户求职意向筛选，排除不投递的岗位类型
7. **输出推荐列表**：生成直观的表格，包含序号、公司、岗位、地点、匹配度、投递方式
8. **保存汇总**：将推荐列表保存为 `daily_report_日期.md` 到工作目录

#### 推荐列表输出格式示例

```
## 今日招聘筛选结果

共获取 N 篇文章，筛选出 M 篇匹配岗位

| # | 公司 | 岗位 | 地点 | 匹配度 | 投递方式 |
|---|------|------|------|--------|----------|
| 1 | BAI资本 | 投资实习生 | 上海 | ⭐⭐⭐⭐⭐ | internbai.sh@gmail.com |
| 2 | 软银中国 | 投资实习生 | 上海 | ⭐⭐⭐⭐⭐ | sbcvc_recruit@126.com |
| 3 | CMC资本 | 股权投资实习生 | 上海/北京 | ⭐⭐⭐⭐⭐ | 需回复"极职Zenith"→"CMC" |

### 需要你手动获取邮箱的岗位：

1. **CMC资本**：打开微信 → 搜索公众号"极职Zenith" → 回复关键词"CMC" → 获取投递邮箱
2. **小米**：打开微信 → 搜索公众号"极职Zenith" → 回复关键词"小米" → 获取投递邮箱

获取到邮箱后，回复"投递+序号"（如"投递1,2"），将自动生成Cover Letter并发送邮件。
```

### 流程2：单篇文章投递（用户触发或定时触发）

1. **提取JD**：使用 `web_fetch` 工具抓取微信文章内容，提取：
   - 公司名称
   - 岗位名称
   - 岗位职责
   - 任职要求
   - 工作地点
   - 投递邮箱
   - 邮件命名要求
2. **判断语言**：JD为英文→使用英文简历和英文Cover Letter；JD为中文→使用中文简历和中文申请信
3. **匹配评估**：根据用户背景评估匹配度
4. **生成Cover Letter**：基于简历内容，撰写简洁的申请信，突出匹配点
5. **推送到Web后台**：调用 `POST /api/jobs` 将投递任务写入数据库（需确保web_server.py正在运行）

   **⚠️ 重要：必须使用 push_job.py 脚本推送，不要用 PowerShell 的 curl/Invoke-RestMethod**（会有中文编码问题）：

   ```bash
   # 方式1：JSON文件模式（推荐，Cover Letter较长时用此方式）
   # 先将任务数据写入临时JSON文件，再推送
   python scripts/push_job.py --json-file /tmp/job.json

   # 方式2：批量推送
   python scripts/push_job.py --batch --json-file /tmp/jobs.json

   # 方式3：参数模式（适合简单任务）
   python scripts/push_job.py --company "BAI资本" --position "投资实习生" --email "hr@bai.com" --subject "主题" --cover-letter "正文"
   ```

6. **通知用户**：告知用户已将投递任务推送到Web后台，请在浏览器中查看并确认发送
7. **用户操作**：用户在Web后台查看任务详情，可编辑Cover Letter/邮箱/主题，点击"一键发送"
8. **邮件发送**：Web后台调用 `send_application_email.py` 发送邮件，并自动记录到 `投递记录.csv`

> **批量推送**：如果有多篇文章需要投递，可使用 `POST /api/jobs/batch` 一次性推送多个任务。

### 流程3：收件箱求职回复检查（定时触发）

1. **运行IMAP检查脚本**：执行 `python scripts/check_inbox_replies.py --days 7 --output inbox_replies.json`
   - 脚本通过IMAP连接Gmail
   - 搜索最近7天的邮件
   - 匹配已投递公司的回复邮箱
   - 搜索求职关键词（面试/offer/简历/感谢/申请/岗位/实习/interview等）
2. **识别面试邀请**：脚本自动判断是否包含面试关键词（面试/interview/一面/二面/终面/笔试等）
3. **输出结果**：
   - 结果保存为 `inbox_replies.json`，Web后台自动读取并在"收件箱回复"标签页展示
   - 面试邀请会以红色高亮标注，提醒用户尽快回复
4. **更新投递记录**：如收到回复，更新 `投递记录.csv` 中的状态列

### 流程4：投递记录查询

查询 `投递记录.csv`，展示已投递的公司、岗位、日期、状态。
字段：日期,公司,岗位,工作地点,投递邮箱,邮件主题,简历版本,状态

## 关键脚本

### scripts/web_server.py
Web管理后台服务（Flask），是AI Agent与用户交互的核心界面。
- AI Agent通过REST API将投递任务写入数据库
- 用户在浏览器中查看、编辑、一键发送
- 自动调用 `send_application_email.py` 发送邮件并记录到 `投递记录.csv`
- 自动读取 `inbox_replies.json` 在前端展示收件箱回复

启动方式：`python scripts/web_server.py --port 5000 --data-dir "简历文件夹路径"`
依赖：`pip install flask`

### scripts/push_job.py
推送投递任务到Web管理后台。AI Agent生成Cover Letter后，通过此脚本将任务写入数据库。
**必须使用此脚本而非curl/Invoke-RestMethod**，避免PowerShell中文编码问题。
调用方式：`python scripts/push_job.py --json-file job.json` 或 `python scripts/push_job.py --company "..." --position "..." ...`

### scripts/llm_client.py
统一 LLM 客户端，支持 DeepSeek / Kimi(Moonshot) / Qwen(DashScope)，三家均兼容 OpenAI API 格式。
Web后台的"刷新文章"功能通过此模块调用 LLM 分析JD和生成Cover Letter。
API Key 在 Web后台设置页面配置，存储在 `settings.json`。

### scripts/jd_analyzer.py
JD 分析器，使用 LLM 从微信公众号文章中提取 JD 信息并生成 Cover Letter。
流程：抓取文章HTML → LLM判断是否招聘信息 → 提取公司/岗位/要求/邮箱 → LLM生成Cover Letter。
如果文章中未提供投递邮箱，`receiver_email` 为空，等用户在Web后台手动填写。

### scripts/send_application_email.py
通过Gmail SMTP发送带PDF附件的邮件。使用MIMEApplication处理附件，utf-8编码中文文件名。
调用方式：`python scripts/send_application_email.py --to email@example.com --subject "主题" --body "正文" --attach resume.pdf`

### scripts/fetch_rss_articles.py
从we-mp-rss获取所有订阅公众号的最新文章，输出JSON格式。
调用方式：`python scripts/fetch_rss_articles.py --limit 10 --output articles.json`
注意：Windows下需先执行 `$env:PYTHONIOENCODING="utf-8"` 避免编码错误

### scripts/check_inbox_replies.py
通过Gmail IMAP检查收件箱中的求职回复邮件。
调用方式：`python scripts/check_inbox_replies.py --days 7 --output replies.json`

## 邮件发送故障排查

### 问题1：附件发送空白/损坏
- **根因**：使用 `MIMEBase` + `encoders.encode_base64` 处理PDF附件时编码不完整
- **解决方案**：必须使用 `MIMEApplication` 替代

### 问题2：中文文件名乱码
- **解决方案**：使用 `('utf-8', '', filename)` 三元组编码文件名

### 问题3：附件路径错误
- **解决方案**：使用原始字符串 `r"path"`，发送前验证文件存在且大小 > 0

### 问题4：PowerShell控制台编码错误
- **解决方案**：执行脚本前设置 `$env:PYTHONIOENCODING="utf-8"`

### 发送邮件前的检查清单
1. 检查附件文件存在：`os.path.exists(attachment_path)`
2. 检查附件大小 > 1000 bytes
3. 检查附件是有效PDF（文件头为 `%PDF`）
4. 验证收件人邮箱格式
5. 首次使用先发送测试邮件给自己确认

## 注意事项

1. **we-mp-rss服务必须运行**：通过 `docker ps` 检查，如未运行则 `docker start we-mp-rss`
2. **Web管理后台必须运行**：投递流程依赖Web后台，启动命令 `python scripts/web_server.py --data-dir "简历文件夹路径"`
3. **微信读书登录可能过期**：如RSS返回空，需在管理后台重新扫码登录
4. **附件必须使用MIMEApplication**：使用MIMEBase会导致附件损坏
5. **投递前用户在Web后台确认**：AI Agent推送任务后，由用户在浏览器中点击"一键发送"
6. **记录所有投递**：Web后台发送邮件后自动写入 `投递记录.csv`，避免重复投递
