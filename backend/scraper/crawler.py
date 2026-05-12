import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
import time
import random
import logging
from fake_useragent import UserAgent

from models import BookSource, Book, Chapter
from __init__ import db

logger = logging.getLogger(__name__)

# ===== 反封禁核心模块 =====

class AntiBlockSession:
    """
    带反封禁措施的请求会话
    - 随机 User-Agent
    - 请求间隔 + 随机抖动
    - 自动重试 + 指数退避
    - 代理池支持
    - Referer / Cookie 伪造
    - 429/403 自动降速
    """

    def __init__(self, proxy_list=None):
        self.proxy_list = proxy_list or []
        self.proxy_index = 0
        self.proxy_fail_count = {}
        self.request_count = 0
        self.last_request_time = 0
        self.base_delay = 1.0          # 基础延迟秒数
        self.jitter_range = (0.5, 2.0) # 随机抖动范围
        self.max_retries = 3            # 最大重试次数
        self.backoff_factor = 2.0       # 退避倍数
        self.cooldown_until = 0         # 冷却截止时间

        try:
            self._ua = UserAgent(browsers=['chrome', 'edge', 'firefox'], fallback=None)
        except Exception:
            self._ua = None

        self._session = requests.Session()
        # 常见浏览器请求头
        self._base_headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        }
        self._session.headers.update(self._base_headers)

    def _get_random_ua(self):
        """获取随机 User-Agent"""
        if self._ua:
            try:
                return self._ua.random
            except Exception:
                pass
        # fallback 常用 UA 池
        ua_pool = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
        ]
        return random.choice(ua_pool)

    def _get_proxy(self):
        """获取下一个代理"""
        if not self.proxy_list:
            return None
        proxy = self.proxy_list[self.proxy_index % len(self.proxy_list)]
        self.proxy_index += 1
        return {'http': proxy, 'https': proxy}

    def _mark_proxy_fail(self, proxy_url):
        """标记代理失败"""
        self.proxy_fail_count[proxy_url] = self.proxy_fail_count.get(proxy_url, 0) + 1
        if self.proxy_fail_count[proxy_url] >= 3:
            # 连续失败3次，移除该代理
            if proxy_url in self.proxy_list:
                self.proxy_list.remove(proxy_url)
                logger.info(f"Removed failing proxy: {proxy_url}")

    def _wait(self, is_retry=False):
        """智能等待：基础延迟 + 随机抖动 + 冷却"""
        now = time.time()

        # 如果在冷却期，等待冷却结束
        if now < self.cooldown_until:
            wait_time = self.cooldown_until - now
            logger.info(f"Cooldown: waiting {wait_time:.1f}s")
            time.sleep(wait_time)

        # 基础延迟 + 随机抖动
        elapsed = now - self.last_request_time
        jitter = random.uniform(*self.jitter_range)
        delay = self.base_delay + jitter

        if is_retry:
            delay *= 2  # 重试时加倍延迟

        if elapsed < delay:
            wait = delay - elapsed
            time.sleep(wait)

        self.last_request_time = time.time()

    def get(self, url, referer=None, timeout=15, **kwargs):
        """
        带反封禁的 GET 请求
        - 每次请求切换 UA
        - 自动添加 Referer
        - 智能延迟
        - 自动重试 + 退避
        - 代理轮换
        - 429/403 自动降速
        """
        last_exception = None

        for attempt in range(self.max_retries):
            self._wait(is_retry=(attempt > 0))
            self.request_count += 1

            # 每次请求都切换 UA
            self._session.headers['User-Agent'] = self._get_random_ua()

            # 设置 Referer（模拟从搜索引擎或站内跳转）
            if referer:
                self._session.headers['Referer'] = referer
            else:
                parsed = urlparse(url)
                self._session.headers['Referer'] = f'{parsed.scheme}://{parsed.netloc}/'

            # 随机添加 Cookie 模拟已访问
            if random.random() > 0.5:
                self._session.headers['Cookie'] = f'_visited=1; _t={random.randint(10000,99999)}'

            # 代理
            proxies = self._get_proxy()

            try:
                resp = self._session.get(url, timeout=timeout, proxies=proxies, **kwargs)

                # 检查是否被封
                if resp.status_code == 429:
                    # Too Many Requests - 退避
                    retry_after = int(resp.headers.get('Retry-After', '30'))
                    logger.warning(f"429 Too Many Requests, backing off {retry_after}s (attempt {attempt+1})")
                    self.cooldown_until = time.time() + retry_after
                    continue

                if resp.status_code == 403:
                    # Forbidden - 可能 IP 被封
                    logger.warning(f"403 Forbidden (attempt {attempt+1}), rotating identity")
                    # 切代理
                    if proxies and self.proxy_list:
                        failed = list(proxies.values())[0]
                        self._mark_proxy_fail(failed)
                    # 加大延迟
                    self.cooldown_until = time.time() + random.uniform(10, 30)
                    continue

                if resp.status_code >= 500:
                    logger.warning(f"Server error {resp.status_code} (attempt {attempt+1})")
                    time.sleep(random.uniform(2, 5))
                    continue

                # 成功 - 记录代理可用
                if proxies and self.proxy_list:
                    current = list(proxies.values())[0]
                    self.proxy_fail_count.pop(current, None)

                # 成功后随机化下次延迟
                self.base_delay = random.uniform(0.8, 1.5)
                return resp

            except requests.exceptions.ConnectionError as e:
                logger.warning(f"Connection error (attempt {attempt+1}): {e}")
                last_exception = e
                if proxies and self.proxy_list:
                    failed = list(proxies.values())[0]
                    self._mark_proxy_fail(failed)
                time.sleep(random.uniform(3, 8))

            except requests.exceptions.Timeout as e:
                logger.warning(f"Timeout (attempt {attempt+1})")
                last_exception = e
                time.sleep(random.uniform(2, 5))

            except Exception as e:
                logger.warning(f"Unexpected error (attempt {attempt+1}): {e}")
                last_exception = e
                time.sleep(random.uniform(2, 5))

        # 所有重试失败
        if last_exception:
            raise last_exception
        raise requests.exceptions.RequestException(f"Failed after {self.max_retries} retries: {url}")


# 全局反封禁会话
anti_block = AntiBlockSession()


def set_proxies(proxy_list):
    """设置代理池"""
    anti_block.proxy_list = proxy_list
    anti_block.proxy_index = 0
    anti_block.proxy_fail_count = {}
    logger.info(f"Proxy pool updated: {len(proxy_list)} proxies")


def set_crawl_speed(speed='normal'):
    """
    设置爬取速度
    - 'fast': 快速（适合不封IP的站点）
    - 'normal': 正常
    - 'slow': 慢速（适合严格封禁的站点）
    - 'stealth': 隐蔽（极慢，最大反封禁）
    """
    speed_configs = {
        'fast':    {'base_delay': 0.3, 'jitter': (0.1, 0.5), 'retries': 2},
        'normal':  {'base_delay': 1.0, 'jitter': (0.5, 2.0), 'retries': 3},
        'slow':    {'base_delay': 2.5, 'jitter': (1.0, 4.0), 'retries': 4},
        'stealth': {'base_delay': 5.0, 'jitter': (2.0, 8.0), 'retries': 5},
    }
    config = speed_configs.get(speed, speed_configs['normal'])
    anti_block.base_delay = config['base_delay']
    anti_block.jitter_range = config['jitter']
    anti_block.max_retries = config['retries']
    logger.info(f"Crawl speed set to: {speed}")


# ===== 站点适配器 =====

class BaseSiteAdapter:
    """基类"""
    def detect(self, url):
        raise NotImplementedError

    def parse(self, source):
        """返回 {'books': [{'title','author','cover_url','description','book_url','category','chapters':[{'index','title','url'}]}]}"""
        raise NotImplementedError


class BiqugeAdapter(BaseSiteAdapter):
    """笔趣阁系列站点适配器"""
    PATTERNS = ['biquge', 'bqgui', 'biqubo', 'xbiquge', 'biquwx', 'biquge5200', '52bqg']

    def detect(self, url):
        hostname = urlparse(url).hostname or ''
        return any(p in hostname.lower() for p in self.PATTERNS)

    def parse(self, source):
        resp = anti_block.get(source.url)
        resp.encoding = self._detect_encoding(resp)
        soup = BeautifulSoup(resp.text, 'lxml')

        books = []
        book_info = self._parse_book_detail(soup, source.url)
        if book_info:
            books.append(book_info)
        else:
            book_links = self._find_book_links(soup, source.url)
            for link in book_links[:50]:
                try:
                    r = anti_block.get(link, referer=source.url)
                    r.encoding = self._detect_encoding(r)
                    s = BeautifulSoup(r.text, 'lxml')
                    info = self._parse_book_detail(s, link)
                    if info:
                        books.append(info)
                except Exception:
                    continue

        return {'books': books}

    def _parse_book_detail(self, soup, url):
        title_tag = soup.select_one('#info h1, .book-info h1, h1.title')
        if not title_tag:
            return None

        title = title_tag.get_text(strip=True)

        author = '未知'
        author_tag = soup.select_one('#info p:first-of-type, .book-info .author, a.name')
        if author_tag:
            author_text = author_tag.get_text(strip=True)
            author = re.sub(r'作\s*者[：:]', '', author_text).strip() or '未知'

        cover_url = ''
        cover_tag = soup.select_one('#fmimg img, .book-info img, .cover img')
        if cover_tag:
            cover_url = cover_tag.get('src', '')
            if cover_url:
                cover_url = urljoin(url, cover_url)

        description = ''
        desc_tag = soup.select_one('#intro, .book-info .intro, .description')
        if desc_tag:
            description = desc_tag.get_text(strip=True)[:500]

        category = '未分类'
        cat_tag = soup.select_one('.con_top a:nth-of-type(2), .breadcrumb a:nth-of-type(2)')
        if cat_tag:
            category = cat_tag.get_text(strip=True)

        chapters = []
        chapter_list = soup.select('#list dl dd a, .chapter-list a, .listmain dl dd a')
        for idx, a in enumerate(chapter_list):
            href = a.get('href', '')
            if not href or href == '#':
                continue
            chapters.append({
                'index': idx,
                'title': a.get_text(strip=True),
                'url': urljoin(url, href)
            })

        if not chapters:
            return None

        return {
            'title': title, 'author': author, 'cover_url': cover_url,
            'description': description, 'book_url': url,
            'category': category, 'chapters': chapters
        }

    def _find_book_links(self, soup, base_url):
        links = []
        for a in soup.select('a[href]'):
            href = a.get('href', '')
            full_url = urljoin(base_url, href)
            if re.match(r'.*/\d+_\d+/?$', full_url) or re.match(r'.*/\d+/?$', full_url):
                if full_url not in links:
                    links.append(full_url)
        return links

    def _detect_encoding(self, resp):
        content_type = resp.headers.get('Content-Type', '')
        if 'charset' in content_type:
            match = re.search(r'charset=([\w-]+)', content_type)
            if match:
                return match.group(1)
        return 'utf-8'


class TianyaAdapter(BaseSiteAdapter):
    """天涯论坛帖子适配"""
    def detect(self, url):
        return 'tianya.cn' in (urlparse(url).hostname or '')

    def parse(self, source):
        resp = anti_block.get(source.url)
        resp.encoding = 'utf-8'
        soup = BeautifulSoup(resp.text, 'lxml')

        title_tag = soup.select_one('h1, .s_title')
        title = title_tag.get_text(strip=True) if title_tag else '天涯帖子'
        author = '未知'
        author_tag = soup.select_one('.author a, .s_author a')
        if author_tag:
            author = author_tag.get_text(strip=True)

        posts = soup.select('.bbs-content, .post-content')
        if not posts:
            return {'books': []}

        content_parts = []
        for p in posts:
            text = p.get_text(strip=True)
            if text:
                content_parts.append(text)

        full_content = '\n\n'.join(content_parts)
        chapters = []
        chunk_size = 5000
        for i in range(0, len(full_content), chunk_size):
            chapters.append({
                'index': len(chapters),
                'title': f'第{len(chapters)+1}部分',
                'url': f'{source.url}#part{len(chapters)}'
            })

        return {'books': [{
            'title': title, 'author': author, 'cover_url': '',
            'description': full_content[:200], 'book_url': source.url,
            'category': '天涯帖子', 'chapters': chapters
        }]}


class GenericNovelAdapter(BaseSiteAdapter):
    """通用小说站点适配器"""
    def detect(self, url):
        return True

    def parse(self, source):
        resp = anti_block.get(source.url)
        resp.encoding = self._detect_encoding(resp)
        soup = BeautifulSoup(resp.text, 'lxml')

        chapter_links = []
        for selector in [
            'dl dd a', '.chapter-list a', '.listmain a', '#list a',
            '.book-chapter a', '.volume-wrap a', '.catalog a',
            'ul.chapter_list a', '.booklist a'
        ]:
            chapter_links = soup.select(selector)
            if len(chapter_links) >= 3:
                break

        if len(chapter_links) < 3:
            return {'books': []}

        title = '未知书名'
        for sel in ['h1', '.book-name', '.bookname', '#bookinfo h1']:
            t = soup.select_one(sel)
            if t:
                title = t.get_text(strip=True)
                break

        author = '未知'
        for sel in ['.author', '.book-author', '.writer']:
            a = soup.select_one(sel)
            if a:
                text = re.sub(r'作\s*者[：:]', '', a.get_text(strip=True)).strip()
                if text:
                    author = text
                    break

        description = ''
        for sel in ['.intro', '#intro', '.book-intro', '.description']:
            d = soup.select_one(sel)
            if d:
                description = d.get_text(strip=True)[:500]
                break

        chapters = []
        seen = set()
        for idx, a in enumerate(chapter_links):
            href = a.get('href', '')
            title_text = a.get_text(strip=True)
            if not href or href == '#' or not title_text:
                continue
            full_url = urljoin(source.url, href)
            if full_url in seen:
                continue
            seen.add(full_url)
            chapters.append({'index': len(chapters), 'title': title_text, 'url': full_url})

        if not chapters:
            return {'books': []}

        return {'books': [{
            'title': title, 'author': author, 'cover_url': '',
            'description': description, 'book_url': source.url,
            'category': '未分类', 'chapters': chapters
        }]}

    def _detect_encoding(self, resp):
        content_type = resp.headers.get('Content-Type', '')
        if 'charset' in content_type:
            match = re.search(r'charset=([\w-]+)', content_type)
            if match:
                return match.group(1)
        try:
            resp.text.encode('utf-8')
            return 'utf-8'
        except Exception:
            return 'gbk'


ADAPTERS = [BiqugeAdapter(), TianyaAdapter(), GenericNovelAdapter()]


def crawl_book_source(source, speed='normal'):
    """爬取一个书源，返回统计信息"""
    set_crawl_speed(speed)

    adapter = None
    for a in ADAPTERS:
        if a.detect(source.url):
            adapter = a
            break

    if not adapter:
        raise ValueError(f'不支持的站点: {source.url}')

    result = adapter.parse(source)
    book_count = 0
    chapter_count = 0

    for book_data in result.get('books', []):
        existing = Book.query.filter_by(source_id=source.id, book_url=book_data['book_url']).first()
        if existing:
            continue

        book = Book(
            source_id=source.id,
            title=book_data['title'],
            author=book_data.get('author', '未知'),
            cover_url=book_data.get('cover_url', ''),
            description=book_data.get('description', ''),
            book_url=book_data['book_url'],
            category=book_data.get('category', '未分类'),
            word_count=book_data.get('word_count', ''),
            status=book_data.get('status', '连载中')
        )
        db.session.add(book)
        db.session.flush()

        for ch_data in book_data.get('chapters', []):
            chapter = Chapter(
                book_id=book.id,
                chapter_index=ch_data['index'],
                title=ch_data['title'],
                url=ch_data['url']
            )
            db.session.add(chapter)
            chapter_count += 1

        book_count += 1

    db.session.commit()
    return {'book_count': book_count, 'chapter_count': chapter_count}


def crawl_chapter_content(url, referer=None):
    """爬取单章内容"""
    resp = anti_block.get(url, referer=referer)

    # 检测编码
    content_type = resp.headers.get('Content-Type', '')
    if 'charset' in content_type:
        match = re.search(r'charset=([\w-]+)', content_type)
        if match:
            resp.encoding = match.group(1)
    else:
        try:
            resp.text.encode('utf-8')
            resp.encoding = 'utf-8'
        except Exception:
            resp.encoding = 'gbk'

    soup = BeautifulSoup(resp.text, 'lxml')

    for tag in soup(['script', 'style', 'ins', 'iframe']):
        tag.decompose()

    content_selectors = [
        '#content', '.content', '#BookText', '.chapter-content',
        '.read-content', '#htmlContent', '.text-content',
        '.bookreadercontent', '#chaptercontent', '.reader-content',
        'article .content', '.novel-content', '#nr1'
    ]

    content_div = None
    for sel in content_selectors:
        content_div = soup.select_one(sel)
        if content_div:
            break

    if content_div:
        text = content_div.get_text(separator='\n', strip=True)
        lines = text.split('\n')
        cleaned = []
        ad_patterns = [
            r'请记住本书首发域名', r'手机版阅读网址', r'最新网址',
            r'天才一秒记住', r'本章未完.*点击下一页',
            r'一秒记住.*免费阅读', r'本章阅读结束'
        ]
        for line in lines:
            if any(re.search(p, line) for p in ad_patterns):
                continue
            cleaned.append(line)
        return '\n'.join(cleaned)

    all_texts = soup.find_all(string=True)
    if all_texts:
        largest = max(all_texts, key=lambda t: len(t.strip()))
        return largest.strip()

    return '无法获取章节内容'


# ===== 搜索换源 =====

# 判断是否为小说阅读站点的特征关键词（辅助判断）
_NOVEL_SITE_KEYWORDS = [
    'biquge', 'bqgui', 'biqubo', 'xbiquge', 'biquwx', 'biquge5200',
    '52bqg', 'bxwx', 'paoshu8', 'ttshu', 'wanben', 'qb5', 'quanshu',
    'biqugu', 'xbiqugu', 'dingdi', 'shuqu', 'boquge', 'qushu',
    'biqugetv', 'biqufan', 'biqiuge', 'ffxs', 'xinbqg', 'biqugex',
    'ibiquge', 'biqugee', 'du1quan', 'twkan', 'biqugse', 'biquw',
    'zanghai', 'vivila', 'aixiax', 'xiaoshuo', 'novel', 'biqugla',
    'ranwen', 'easysoso', 'xxsy', 'faloo', 'shuba', 'shuqi',
    'biqugn', 'biqugegg', 'yixiangxws', 'xsw', 'zwdu', 'znlzd',
    'mishi', 'gdbzkz', 'xsbiquge', 'lkshu', 'shuquge',
    'uushu', 'aishu', 'dshu', 'tianxiabook', 'xiaoqiaxs',
    'bqgxsw', '69shu', '8novel',
]

# 明确排除的域名（正版/大平台/内容站/非小说站）
_EXCLUDED_DOMAINS = [
    'baidu.com', 'zhihu.com', 'weibo.com', 'douban.com', 'sohu.com',
    '163.com', 'toutiao.com', 'weixin', 'bilibili', 'taobao.com',
    'jd.com', 'douyin.com', 'xiaohongshu', 'wikipedia', 'tieba.baidu',
    'qidian.com', 'chuangshi.qq.com', 'read.qq.com', 'vip.reader.qq.com',
    'ubook.reader.qq.com', 'hongxiu.com', 'readnovel.com', 'xs8.cn',
    'm.qidian.com', 'book.qq.com', 'read.douban.com',
]


def search_other_sources(title, author=''):
    """
    通过百度搜索发现其他站点上的同名书籍。
    核心逻辑：用书名从百度获取结果，提取小说站链接，精确匹配书名。
    """
    results = []
    seen_urls = set()

    # 构造多组搜索关键词，覆盖不同搜索习惯
    search_keywords = [
        f'{title} 笔趣阁 最新章节',
        f'{title} 最新章节 目录',
        f'{title} 在线阅读 全文',
    ]
    if author and author != '未知':
        search_keywords.append(f'{title} {author} 最新章节')

    for keyword in search_keywords:
        try:
            _do_baidu_search(keyword, title, results, seen_urls)
        except Exception as e:
            logger.warning(f"Baidu search failed for '{keyword}': {e}")

    return results[:30]


def _do_baidu_search(keyword, exact_title, results, seen_urls):
    """执行一次百度搜索，提取小说站链接，精确匹配书名"""
    resp = anti_block.get(
        'https://www.baidu.com/s',
        params={'wd': keyword},
        timeout=15
    )
    resp.encoding = 'utf-8'
    soup = BeautifulSoup(resp.text, 'lxml')

    containers = soup.select('.result, .c-container')
    for container in containers:
        # 优先从 mu 属性拿真实URL（百度结果卡片里藏着目标站真实链接）
        mu_url = container.get('mu', '')
        h3 = container.select_one('h3 a, .t a')
        link_title = h3.get_text(strip=True) if h3 else ''

        urls_to_check = []
        if mu_url and mu_url.startswith('http'):
            urls_to_check.append(mu_url)

        # h3链接作为备选（需要解析百度跳转）
        if h3:
            href = h3.get('href', '')
            if href and href.startswith('http'):
                urls_to_check.append(href)

        for raw_url in urls_to_check:
            # 如果是百度跳转链接，解析出真实URL
            real_url = raw_url
            if 'baidu.com/link' in raw_url:
                real_url = _resolve_baidu_link(raw_url) or raw_url

            # 检查：1) 是小说站 2) 书名精确匹配 3) 未重复
            if not _is_novel_site(real_url):
                continue
            if real_url in seen_urls:
                continue
            if not _title_exact_match(exact_title, link_title):
                continue

            seen_urls.add(real_url)
            domain = urlparse(real_url).hostname or ''
            # 去重：同一主域名只保留一个结果
            root_domain = _get_root_domain(domain)
            if any(_get_root_domain(urlparse(r['url']).hostname or '') == root_domain for r in results):
                continue
            source_name = _extract_source_name(domain)
            results.append({
                'title': exact_title,
                'url': real_url,
                'source_name': source_name,
            })


def _resolve_baidu_link(baidu_url):
    """解析百度跳转链接，获取真实目标URL"""
    try:
        resp = requests.get(baidu_url, timeout=5, allow_redirects=True,
                           headers={'User-Agent': anti_block._get_random_ua()})
        final_url = resp.url
        if 'baidu.com' in final_url:
            return None
        return final_url
    except Exception:
        return None


def _get_root_domain(hostname):
    """提取主域名，如 www.xbiquge.la -> xbiquge.la, m.easysoso.cn -> easysoso.cn"""
    if not hostname:
        return ''
    parts = hostname.replace('www.', '').replace('m.', '').replace('wap.', '').split('.')
    if len(parts) >= 2:
        return '.'.join(parts[-2:])
    return hostname


def _extract_source_name(hostname):
    """从域名中提取书源名称，更智能地处理子域名"""
    if not hostname:
        return '未知'
    # 移除常见前缀
    h = hostname.replace('www.', '').replace('m.', '').replace('wap.', '').replace('a.', '')
    parts = h.split('.')
    # 取主域名部分（如 xxsy.net -> xxsy, yixiangxws.com -> yixiangxws）
    if len(parts) >= 2:
        main_part = parts[0]
        # 如果主域名太短（如 a, b），尝试使用完整子域名
        if len(main_part) <= 2 and len(parts) >= 3:
            main_part = parts[-3] if len(parts[-3]) > len(main_part) else main_part
        return main_part
    return hostname


def _is_novel_site(url):
    """判断URL是否来自小说阅读站（免费小说站为主，排除正版平台和非小说站）"""
    hostname = (urlparse(url).hostname or '').lower()
    path = urlparse(url).path.lower()

    # 排除正版平台和非小说站
    if any(e in hostname for e in _EXCLUDED_DOMAINS):
        return False

    # 域名包含小说站关键词
    if any(kw in hostname for kw in _NOVEL_SITE_KEYWORDS):
        return True

    # URL路径特征判断（很多小站域名无特征，但路径有模式）
    # 匹配如 /book/123/、/xs-123/、/0_123/、/html/12/12345/、/dushi/123.html 等
    novel_path_patterns = [
        r'^/\d+_\d+',              # /0_123/
        r'^/book/\d+',             # /book/123/
        r'^/xs-\d+',              # /xs-123/
        r'^/novel/\d+',            # /novel/123/
        r'^/html/\d+/\d+',        # /html/12/12345/
        r'^/(dushi|xuanhuan|qihuan|lishi|kehuan|wuxia|xianxia|youxi|lingyi|junshi|city|game|scifi|romance)/\d+',
    ]
    if any(re.match(p, path) for p in novel_path_patterns):
        return True

    return False


def _title_exact_match(original_title, candidate_text):
    """
    精确匹配：百度搜索结果标题中是否包含完整的书名。
    策略：候选文本中必须包含完整的书名字符串。
    """
    if not original_title or not candidate_text:
        return False

    # 去掉HTML标签残留
    clean = re.sub(r'<[^>]+>', '', candidate_text)

    # 核心判断：候选文本中是否包含完整的书名
    if original_title in clean:
        return True

    return False


def crawl_single_book(url, expected_title=''):
    """爬取单个URL的书籍信息（用于换源）"""
    # 尝试各种适配器
    for adapter in ADAPTERS:
        if adapter.detect(url):
            class FakeSource:
                def __init__(self, url):
                    self.url = url
            result = adapter.parse(FakeSource(url))
            books = result.get('books', [])
            if books:
                # 优先匹配标题
                for b in books:
                    if expected_title and (expected_title in b['title'] or b['title'] in expected_title):
                        return b
                # 没匹配到就返回第一个
                return books[0]

    # 通用爬取
    try:
        resp = anti_block.get(url)
        resp.encoding = _detect_encoding(resp)
        soup = BeautifulSoup(resp.text, 'lxml')

        # 找章节列表
        chapter_links = []
        for selector in ['dl dd a', '.chapter-list a', '.listmain a', '#list a',
                         '.book-chapter a', '.volume-wrap a', '.catalog a',
                         'ul.chapter_list a', '.booklist a']:
            chapter_links = soup.select(selector)
            if len(chapter_links) >= 3:
                break

        if len(chapter_links) < 3:
            return None

        title = expected_title or '未知'
        for sel in ['h1', '.book-name', '.bookname', '#bookinfo h1']:
            t = soup.select_one(sel)
            if t:
                title = t.get_text(strip=True)
                break

        author = '未知'
        for sel in ['.author', '.book-author', '.writer']:
            a = soup.select_one(sel)
            if a:
                text = re.sub(r'作\s*者[：:]', '', a.get_text(strip=True)).strip()
                if text:
                    author = text
                    break

        description = ''
        for sel in ['.intro', '#intro', '.book-intro', '.description']:
            d = soup.select_one(sel)
            if d:
                description = d.get_text(strip=True)[:500]
                break

        chapters = []
        seen = set()
        for a in chapter_links:
            href = a.get('href', '')
            title_text = a.get_text(strip=True)
            if not href or href == '#' or not title_text:
                continue
            full_url = urljoin(url, href)
            if full_url in seen:
                continue
            seen.add(full_url)
            chapters.append({'index': len(chapters), 'title': title_text, 'url': full_url})

        return {
            'title': title, 'author': author, 'cover_url': '',
            'description': description, 'book_url': url,
            'category': '未分类', 'chapters': chapters
        }
    except Exception as e:
        logger.error(f"crawl_single_book failed: {e}")
        return None


# ===== 搜书功能 =====

def search_books(keyword, source_urls=None):
    """
    搜书功能：优先从已有书源站点中搜索，同时从百度搜索补充结果。
    keyword: 搜索关键字（书名、作者名、或书名+作者名）
    source_urls: 用户已添加的书源URL列表
    返回: [{'title', 'author', 'url', 'source_name', 'description', 'cover_url', 'from_source'}]
    """
    results = []
    seen_urls = set()

    # 第一步：从已添加的书源站点中搜索
    if source_urls:
        source_results = _search_from_sources(keyword, source_urls)
        for r in source_results:
            url_key = r['url']
            if url_key not in seen_urls:
                seen_urls.add(url_key)
                r['from_source'] = True
                results.append(r)

    # 第二步：始终从百度搜索补充（书源结果可能不完整）
    baidu_results = _search_from_baidu(keyword)
    for r in baidu_results:
        url_key = r['url']
        if url_key not in seen_urls:
            seen_urls.add(url_key)
            r['from_source'] = False
            results.append(r)

    return results[:30]


def _search_from_sources(keyword, source_urls):
    """从用户已添加的书源站点中搜索书籍"""
    results = []
    # 将关键字拆分为词，用于匹配
    keywords = keyword.strip().split()
    
    for url in source_urls:
        try:
            resp = anti_block.get(url, timeout=10)
            resp.encoding = _detect_encoding(resp)
            soup = BeautifulSoup(resp.text, 'lxml')

            # 在页面中搜索所有链接，匹配书名或作者
            book_links = []
            for a_tag in soup.select('a[href]'):
                text = a_tag.get_text(strip=True)
                href = a_tag.get('href', '')
                if not text or not href or href == '#':
                    continue
                # 所有关键词都要在文本中出现（支持 书名+作者名 的场景）
                if all(kw in text for kw in keywords):
                    full_url = urljoin(url, href)
                    # 排除外链
                    parsed = urlparse(full_url)
                    base_parsed = urlparse(url)
                    if parsed.hostname != base_parsed.hostname:
                        continue
                    # 排除章节页面（.html 结尾通常是章节页，不是书籍目录页）
                    path = parsed.path.lower()
                    if path.endswith('.html') or path.endswith('.htm'):
                        continue
                    book_links.append({
                        'text': text,
                        'url': full_url
                    })

            # 去重
            seen = set()
            for link in book_links[:10]:
                if link['url'] in seen:
                    continue
                seen.add(link['url'])

                # 尝试爬取书籍详情
                try:
                    book_info = crawl_single_book(link['url'], link['text'])
                    if book_info and book_info.get('chapters'):
                        parsed = urlparse(url)
                        domain = parsed.hostname or ''
                        source_name = _extract_source_name(domain)
                        results.append({
                            'title': book_info.get('title', link['text']),
                            'author': book_info.get('author', '未知'),
                            'url': link['url'],
                            'source_name': source_name,
                            'description': book_info.get('description', '')[:200],
                            'cover_url': book_info.get('cover_url', ''),
                        })
                except Exception:
                    # 爬取详情失败，仍然保留基本搜索结果
                    parsed = urlparse(url)
                    domain = parsed.hostname or ''
                    source_name = _extract_source_name(domain)
                    results.append({
                        'title': link['text'],
                        'author': '未知',
                        'url': link['url'],
                        'source_name': source_name,
                        'description': '',
                        'cover_url': '',
                    })

        except Exception as e:
            logger.warning(f"Search from source {url} failed: {e}")
            continue

    return results


def _search_from_baidu(keyword):
    """从百度搜索书籍"""
    results = []
    seen_urls = set()

    # 拆分关键词，判断搜索类型
    words = keyword.strip().split()
    if len(words) >= 2:
        # 可能是"书名 作者名"或"作者名 书名"
        # 尝试用完整关键字 + 书名搜索
        search_keywords = [
            f'{words[0]} 笔趣阁 最新章节',
            f'{words[0]} {words[1]} 最新章节 目录',
            f'{keyword} 在线阅读 全文',
        ]
    else:
        # 单个关键词，可能是书名或作者名
        search_keywords = [
            f'{keyword} 笔趣阁 最新章节',
            f'{keyword} 小说 最新章节 目录',
            f'{keyword} 在线阅读 全文',
        ]

    for kw in search_keywords:
        try:
            _do_baidu_search_book(kw, keyword, results, seen_urls)
        except Exception as e:
            logger.warning(f"Baidu search failed for '{kw}': {e}")

    return results


def _do_baidu_search_book(keyword, search_term, results, seen_urls):
    """百度搜书：提取小说站链接，匹配搜索关键词"""
    resp = anti_block.get(
        'https://www.baidu.com/s',
        params={'wd': keyword},
        timeout=15
    )
    resp.encoding = 'utf-8'
    soup = BeautifulSoup(resp.text, 'lxml')

    containers = soup.select('.result, .c-container')
    for container in containers:
        mu_url = container.get('mu', '')
        h3 = container.select_one('h3 a, .t a')
        link_title = h3.get_text(strip=True) if h3 else ''

        urls_to_check = []
        if mu_url and mu_url.startswith('http'):
            urls_to_check.append(mu_url)

        if h3:
            href = h3.get('href', '')
            if href and href.startswith('http'):
                urls_to_check.append(href)

        for raw_url in urls_to_check:
            real_url = raw_url
            if 'baidu.com/link' in raw_url:
                real_url = _resolve_baidu_link(raw_url) or raw_url

            if not _is_novel_site(real_url):
                continue
            if real_url in seen_urls:
                continue
            # 搜书时使用更宽松的匹配：搜索词的任一部分在标题中即可
            # 支持书名+作者 或 纯作者名 搜索
            search_words = search_term.split()
            if not any(sw in link_title for sw in search_words if len(sw) >= 2):
                # 如果搜索单词都不在标题中，跳过
                short_words = [sw for sw in search_words if len(sw) >= 2]
                if short_words:
                    continue

            seen_urls.add(real_url)
            domain = urlparse(real_url).hostname or ''
            root_domain = _get_root_domain(domain)
            if any(_get_root_domain(urlparse(r['url']).hostname or '') == root_domain for r in results):
                continue
            source_name = _extract_source_name(domain)
            results.append({
                'title': link_title.replace('_', ' ').replace('-', ' '),
                'author': '未知',
                'url': real_url,
                'source_name': source_name,
                'description': '',
                'cover_url': '',
            })


def _detect_encoding(resp):
    """通用编码检测"""
    content_type = resp.headers.get('Content-Type', '')
    if 'charset' in content_type:
        match = re.search(r'charset=([\w-]+)', content_type)
        if match:
            return match.group(1)
    try:
        resp.text.encode('utf-8')
        return 'utf-8'
    except Exception:
        return 'gbk'
