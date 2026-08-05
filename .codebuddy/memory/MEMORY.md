# BookRead 项目长期记忆

## 项目结构
- `backend/`: Flask 后端（SQLite + SQLAlchemy + JWT），入口 `start.py`
- `frontend/`: React + Vite 前端（antd v5），入口 `vite.config.js`
- `start.bat`: 一键启动脚本
- 已删除 `BookReadApp/` 和 `BookReadNew/`（React Native app 相关，用户不需要）

## 启动方式
- 后端: `cd backend && python start.py`（端口 5000）
- 前端: `cd frontend && node_modules\.bin\vite --host`（端口 5173）
- 注意: 必须用 `node_modules\.bin\vite` 而非 `npx vite`，因为全局安装的 vite 8 有兼容问题（返回 404），本地是 vite 5.4.21

## 数据库
- 文件: `backend/bookread.db`
- 用户: testuser(id=1, 主要使用账号，有书源和书籍), admin(id=2), geniuswh(id=3)
- 书籍存储: SQLite，章节内容懒加载（阅读时才爬取并缓存到 Chapter.content）

## 爬虫
- `backend/scraper/crawler.py` 包含多站点适配器：Biquge、Tianya、Boluomao、GenericNovel
- **菠萝猫 (boluomao) 适配器**（2026-08-05 添加）:
  - 书籍页 `/book/{id}.html` 可匿名访问
  - 章节列表分页: `?cp=N`，容器 `.direBox .direList .name a`
  - 章节正文 `obf-text` 加密，解密算法: base64 解码 → 每字节 XOR ((i % 127) + 1) → UTF-8（函数 `_boluomao_decode`）
  - 简介在 `.obf-html[data-obf-html]`（同样加密）
  - **限制**: 前100章可匿名爬取，第101章起需要登录；TXT下载也需登录
- **登录**: 已实现 `boluomao_login(username, password)` 自动登录（ddddocr 识别验证码），登录会话保存在 `_boluomao_session`，供章节爬取使用
- 菠萝猫账号: geniuswh@163.com / geniuswh（用户提供）
- 已入库: 《华娱之娱乐圈外人》796章全部正文已缓存（book id=4, 书源 id=5 "菠萝猫"），归属 testuser，全书约173万字
- 正文爬取脚本: `backend/crawl_book_content.py`（登录后逐章爬正文写库，防风控间隔1.5-3秒，失败自动重登录）
- 菠萝猫部分章节有 `?p=N` 分页，`_crawl_boluomao_chapter` 已支持自动翻页合并

## 其他
- 系统登录接口返回字段为 `token`（不是 access_token）
- 书籍列表接口返回结构为 `{books, page, pages, per_page, total}`
- testuser 密码已重置为 `testuser123`（2026-08-05）
- TXT导出功能（2026-08-05）：后端 `GET /api/books/:id/export` 返回全部章节合并TXT（未缓存章节实时爬取），前端在 Home 书架下拉菜单和 BookDetail 更多操作里加了"下载TXT"
