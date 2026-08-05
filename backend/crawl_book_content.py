# -*- coding: utf-8 -*-
"""
菠萝猫《华娱之娱乐圈外人》完整正文爬取脚本
登录后遍历所有章节，爬取正文并写入数据库缓存。
用法: python crawl_book_content.py [book_id]
"""
import sys
import os
import time
import random

sys.stdout.reconfigure(encoding='utf-8')
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from __init__ import create_app, db
from models import Book, Chapter
from scraper.crawler import boluomao_login, boluomao_logout, crawl_chapter_content

BOOK_ID = int(sys.argv[1]) if len(sys.argv) > 1 else 4
USERNAME = 'geniuswh@163.com'
PASSWORD = 'geniuswh'


def ensure_login():
    """确保已登录，失败时重试"""
    for attempt in range(3):
        ok, msg = boluomao_login(USERNAME, PASSWORD)
        if ok:
            return True
        print(f'  重新登录尝试 {attempt+1} 失败: {msg}')
        time.sleep(3)
    return False


def main():
    app = create_app()
    with app.app_context():
        book = Book.query.get(BOOK_ID)
        if not book:
            print('书籍不存在:', BOOK_ID)
            return

        print(f'书籍: {book.title} (id={book.id})')

        if not ensure_login():
            print('登录失败，退出')
            return

        chapters = Chapter.query.filter_by(book_id=book.id).order_by(Chapter.chapter_index).all()
        total = len(chapters)
        print(f'共 {total} 章，开始爬取正文...')

        success = 0
        cached = 0
        failed = 0
        consecutive_fail = 0
        t0 = time.time()

        for i, ch in enumerate(chapters, 1):
            if ch.content:
                cached += 1
                continue

            content = None
            # 每章重试最多2次
            for attempt in range(2):
                try:
                    content = crawl_chapter_content(ch.url, referer=book.book_url)
                    if content and content != '无法获取章节内容':
                        break
                    content = None
                    time.sleep(random.uniform(1, 2))
                except Exception as e:
                    content = None
                    time.sleep(random.uniform(1, 2))
                    if attempt == 0 and e.__class__.__name__ in ('ConnectionError', 'ReadTimeout', 'ChunkedEncodingError'):
                        # 连接问题可能是风控，重新登录
                        print(f'  第{i}章连接异常，重新登录...')
                        ensure_login()

            if content:
                ch.content = content
                db.session.commit()
                success += 1
                consecutive_fail = 0
            else:
                failed += 1
                consecutive_fail += 1
                db.session.rollback()
                if failed <= 10:
                    print(f'  第{i}章({ch.title[:25]}) 爬取失败')
                if consecutive_fail >= 8:
                    print(f'  连续失败 {consecutive_fail} 章，重新登录并等待...')
                    boluomao_logout()
                    ensure_login()
                    consecutive_fail = 0
                    time.sleep(5)

            if i % 25 == 0:
                elapsed = time.time() - t0
                print(f'  进度: {i}/{total} 成功={success} 失败={failed} 已有缓存={cached} 用时={elapsed:.0f}s')

            # 控制请求间隔，避免风控
            time.sleep(random.uniform(1.5, 3.0))

        print(f'\n完成: 新增{success}章, 已有缓存{cached}章, 失败{failed}章, 总耗时{time.time()-t0:.0f}s')


if __name__ == '__main__':
    main()
