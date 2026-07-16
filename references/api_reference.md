# we-mp-rss API 参考

## 基础信息

- **服务地址**: http://localhost:8001
- **API基础路径**: `/api/v1/wx`
- **管理后台**: 浏览器访问 http://localhost:8001
- **Docker容器名**: we-mp-rss

## 认证

### 登录获取Token

```
POST /api/v1/wx/auth/login
Content-Type: application/x-www-form-urlencoded

username=admin&password=admin@123
```

响应:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "access_token": "eyJ...",
    "token_type": "bearer",
    "expires_in": 259200
  }
}
```

### 使用Token

在后续请求中添加Header:
```
Authorization: Bearer <access_token>
```

## 公众号管理

### 获取公众号列表

```
GET /api/v1/wx/mps
Authorization: Bearer <token>
```

响应包含每个公众号的:
- `id`: 公众号ID（用于RSS请求）
- `mp_name`: 公众号名称
- `mp_cover`: 头像URL
- `mp_intro`: 简介
- `status`: 状态（1=正常）

## RSS接口（无需认证）

### 获取RSS订阅列表

```
GET /rss
```

返回所有公众号的RSS汇总（XML格式）。

### 获取单个公众号文章

```
GET /rss/{feed_id}?limit=10
```

参数:
- `feed_id`: 公众号ID（如 `MP_WXS_3017314279`）
- `limit`: 文章数量（1-100，默认10）
- `offset`: 偏移量（默认0）

返回RSS XML，包含:
- `<channel><title>`: 公众号名称
- `<item>`: 每篇文章
  - `<title>`: 文章标题
  - `<link>`: 微信文章原始URL
  - `<description>`: 摘要
  - `<pubDate>`: 发布时间
  - `<guid>`: 文章唯一标识

### 获取全部公众号文章

```
GET /rss/all?limit=30
```

### 搜索文章

```
GET /feed/search/{keyword}/{feed_id}.xml
```

## 文章管理

### 获取文章列表

```
GET /api/v1/wx/articles
Authorization: Bearer <token>
```

## Docker管理命令

```bash
# 查看容器状态
docker ps --filter name=we-mp-rss

# 启动/停止/重启
docker start we-mp-rss
docker stop we-mp-rss
docker restart we-mp-rss

# 查看日志
docker logs we-mp-rss --tail 50

# 进入容器
docker exec -it we-mp-rss bash
```

## 常见问题

### RSS返回空或无数据
1. 检查容器是否运行: `docker ps`
2. 检查微信读书登录状态: 访问 http://localhost:8001 管理后台
3. 查看容器日志: `docker logs we-mp-rss --tail 50`
4. 如果登录过期，需在管理后台重新扫码登录微信读书

### API返回401
Token已过期，重新调用 `/auth/login` 获取新token。
