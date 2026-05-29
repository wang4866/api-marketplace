# Web2MD API — 网页转Markdown

一键将任意网页URL转换为干净的Markdown格式。自动去除广告、导航栏、侧边栏，只保留正文内容。

🌐 **在线体验**: https://wang4866.github.io/api-marketplace/  
📘 **API文档**: https://wang4866.github.io/api-marketplace/docs.html  
💻 **技术栈**: FastAPI + BeautifulSoup + markdownify + httpx

---

## 快速开始

```bash
# 克隆项目
git clone https://github.com/wang4866/api-marketplace.git
cd api-marketplace

# 安装依赖
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 启动服务
cd app
uvicorn main:app --host 0.0.0.0 --port 8000

# 测试
curl -X POST http://localhost:8000/convert \
  -H "Content-Type: application/json" \
  -d '{"url": "https://zh.wikipedia.org/wiki/Markdown"}'
```

## API 接口

### POST /convert
把网页URL转为干净Markdown。

**请求参数:**
```json
{
  "url": "https://example.com/article",     // 必填：要转换的网页URL
  "include_images": false                    // 选填：是否保留图片链接
}
```

**返回结果:**
```json
{
  "success": true,
  "title": "文章标题",
  "content": "# Markdown正文...",
  "url": "https://example.com/article",
  "word_count": 1200,
  "char_count": 8000
}
```

### GET /health
健康检查，返回 `{"status": "healthy"}`

### GET /docs
Swagger UI 交互式文档

## 使用示例

### Python
```python
import httpx

resp = httpx.post("http://localhost:8000/convert", json={
    "url": "https://zh.wikipedia.org/wiki/Python"
})
data = resp.json()
print(data["title"])
print(data["content"])
```

### JavaScript
```javascript
const resp = await fetch("http://localhost:8000/convert", {
  method: "POST",
  headers: {"Content-Type": "application/json"},
  body: JSON.stringify({url: "https://zh.wikipedia.org/wiki/Python"})
});
const data = await resp.json();
```

## 部署

### Render (推荐)
项目根目录包含 `render.yaml`，push到GitHub后Render会自动部署。

### Railway
1. 导入GitHub仓库
2. 设置启动命令: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### VPS
```
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 项目结构
```
api-marketplace/
├── app/
│   ├── main.py          # FastAPI应用入口
│   ├── web_to_md.py     # 网页转Markdown核心逻辑
│   └── __init__.py
├── site/
│   ├── index.html       # 中文静态首页
│   ├── docs.html        # 中文API文档
│   └── vercel.json      # Vercel配置
├── requirements.txt
├── render.yaml          # Render部署配置
├── deploy.sh            # 部署脚本
└── README.md
```

## 限流
每个IP每小时100次请求，无需注册即可使用。

## 开源协议
MIT
