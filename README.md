# BookRead - 个人网上书城

一个基于 Flask + React 的个人在线阅读平台，支持书源管理、小说爬取、在线阅读、搜书换源等功能。

## 功能特性

- **书源管理** — 添加、编辑、删除书源，一键爬取书籍和章节
- **在线阅读** — 沉浸式阅读体验，自定义字体/字号/行距/主题等
- **阅读进度** — 自动保存阅读进度，下次打开继续阅读
- **搜书** — 输入书名/作者搜索，优先从已添加书源搜索，再从百度搜索补充，一键加入书架
- **搜索换源** — 对已有书籍搜索其他站点同名书，支持一键换源
- **书架分组** — 自定义分组管理书架书籍
- **反封禁爬虫** — 随机 UA、智能延迟、自动重试、代理池支持

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Flask, SQLAlchemy, Flask-JWT-Extended, BeautifulSoup4 |
| 前端 | React 18, Ant Design 5, Vite, React Router 6 |
| 数据库 | SQLite |
| 爬虫 | requests, BeautifulSoup4, lxml, fake-useragent |

## 项目结构

```
BookRead/
├── backend/
│   ├── __init__.py          # Flask 应用工厂
│   ├── models.py            # 数据模型
│   ├── start.py             # 启动入口
│   ├── requirements.txt     # Python 依赖
│   ├── routes/
│   │   ├── auth.py          # 认证 API
│   │   ├── books.py         # 书籍/书源/搜书 API
│   │   └── reader.py        # 阅读 API
│   └── scraper/
│       └── crawler.py       # 爬虫核心（爬取/搜书/换源）
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── api.js           # API 请求封装
│       ├── App.jsx           # 路由配置
│       ├── components/
│       │   └── Layout.jsx    # 全局布局
│       └── pages/
│           ├── Home.jsx      # 书架首页
│           ├── Search.jsx    # 搜书
│           ├── BookDetail.jsx# 书籍详情/章节目录
│           ├── Reader.jsx    # 阅读器
│           ├── Sources.jsx   # 书源管理
│           ├── Login.jsx     # 登录
│           ├── Register.jsx  # 注册
│           └── Profile.jsx   # 个人设置
└── start.bat                # 一键启动脚本
```

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+

### 安装

```bash
# 克隆项目
git clone https://github.com/geniuswh/BookRead.git
cd BookRead

# 安装后端依赖
cd backend
pip install -r requirements.txt

# 安装前端依赖
cd ../frontend
npm install
```

### 启动

**方式一：一键启动（Windows）**

双击 `start.bat` 或在项目根目录执行：

```bash
start.bat
```

**方式二：分别启动**

```bash
# 后端（默认端口 5000）
cd backend
python start.py

# 前端（默认端口 5173）
cd frontend
npm run dev
```

打开浏览器访问 http://localhost:5173

## API 概览

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/register` | 用户注册 |
| POST | `/api/auth/login` | 用户登录 |
| GET | `/api/books/list` | 获取书架列表 |
| GET | `/api/books/search?keyword=` | 搜书 |
| POST | `/api/books/search/add` | 搜索结果加入书架 |
| GET | `/api/books/sources` | 获取书源列表 |
| POST | `/api/books/sources` | 添加书源 |
| PUT | `/api/books/sources/:id` | 编辑书源 |
| POST | `/api/books/sources/:id/crawl` | 爬取书源 |
| GET | `/api/books/:id/search-sources` | 搜索换源 |
| POST | `/api/books/:id/switch-source` | 切换书源 |
| GET | `/api/books/groups` | 获取分组 |
| GET | `/api/reader/chapter/:id` | 获取章节内容 |
| POST | `/api/reader/progress/:bookId` | 保存阅读进度 |

## 许可证

MIT
