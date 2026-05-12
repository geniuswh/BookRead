from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import or_
import time

from __init__ import db
from models import BookSource, Book, Chapter, ReadingProgress, BookGroup
from scraper.crawler import crawl_book_source, crawl_chapter_content, set_proxies, set_crawl_speed, anti_block, search_other_sources, search_books

books_bp = Blueprint('books', __name__)


# ===== 爬虫配置 API =====

@books_bp.route('/config/proxies', methods=['POST'])
@jwt_required()
def update_proxies():
    """设置代理池，格式: {"proxies": ["http://ip:port", "socks5://ip:port"]}"""
    data = request.get_json()
    proxies = data.get('proxies', [])
    set_proxies(proxies)
    return jsonify(msg=f'代理池已更新，共 {len(proxies)} 个代理')


@books_bp.route('/config/speed', methods=['POST'])
@jwt_required()
def update_speed():
    """设置爬取速度，格式: {"speed": "normal|slow|fast|stealth"}"""
    data = request.get_json()
    speed = data.get('speed', 'normal')
    if speed not in ('fast', 'normal', 'slow', 'stealth'):
        return jsonify(msg='速度只能是 fast/normal/slow/stealth'), 400
    set_crawl_speed(speed)
    return jsonify(msg=f'爬取速度已设为: {speed}')


@books_bp.route('/config/status', methods=['GET'])
@jwt_required()
def get_crawl_status():
    """获取爬虫状态"""
    return jsonify({
        'request_count': anti_block.request_count,
        'proxy_count': len(anti_block.proxy_list),
        'base_delay': anti_block.base_delay,
        'max_retries': anti_block.max_retries,
        'is_cooling_down': time.time() < anti_block.cooldown_until
    })


@books_bp.route('/sources', methods=['POST'])
@jwt_required()
def add_source():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    name = data.get('name', '').strip()
    url = data.get('url', '').strip()
    source_type = data.get('type', 'custom')

    if not name or not url:
        return jsonify(msg='名称和URL不能为空'), 400

    source = BookSource(user_id=user_id, name=name, url=url, source_type=source_type)
    db.session.add(source)
    db.session.commit()

    return jsonify(msg='书源添加成功', source={'id': source.id, 'name': source.name, 'url': source.url}), 201


@books_bp.route('/sources', methods=['GET'])
@jwt_required()
def get_sources():
    user_id = int(get_jwt_identity())
    sources = BookSource.query.filter_by(user_id=user_id).order_by(BookSource.created_at.desc()).all()

    result = []
    for s in sources:
        book_count = Book.query.filter_by(source_id=s.id).count()
        result.append({
            'id': s.id, 'name': s.name, 'url': s.url,
            'type': s.source_type, 'book_count': book_count,
            'last_crawled': s.last_crawled.isoformat() if s.last_crawled else None
        })

    return jsonify(result)


@books_bp.route('/sources/<int:source_id>', methods=['DELETE'])
@jwt_required()
def delete_source(source_id):
    user_id = int(get_jwt_identity())
    source = BookSource.query.filter_by(id=source_id, user_id=user_id).first()
    if not source:
        return jsonify(msg='书源不存在'), 404

    Book.query.filter_by(source_id=source_id).delete()
    db.session.delete(source)
    db.session.commit()
    return jsonify(msg='删除成功')


@books_bp.route('/sources/<int:source_id>', methods=['PUT'])
@jwt_required()
def update_source(source_id):
    user_id = int(get_jwt_identity())
    source = BookSource.query.filter_by(id=source_id, user_id=user_id).first()
    if not source:
        return jsonify(msg='书源不存在'), 404

    data = request.get_json()
    if 'name' in data:
        name = data['name'].strip()
        if not name:
            return jsonify(msg='名称不能为空'), 400
        source.name = name
    if 'url' in data:
        url = data['url'].strip()
        if not url:
            return jsonify(msg='URL不能为空'), 400
        source.url = url
    if 'type' in data:
        source.source_type = data['type']

    db.session.commit()
    return jsonify(msg='书源更新成功', source={
        'id': source.id, 'name': source.name,
        'url': source.url, 'type': source.source_type
    })


@books_bp.route('/sources/<int:source_id>/crawl', methods=['POST'])
@jwt_required()
def crawl_source(source_id):
    user_id = int(get_jwt_identity())
    source = BookSource.query.filter_by(id=source_id, user_id=user_id).first()
    if not source:
        return jsonify(msg='书源不存在'), 404

    try:
        data = request.get_json(silent=True) or {}
        speed = data.get('speed', 'normal')
        result = crawl_book_source(source, speed=speed)
        source.last_crawled = db.func.now()
        db.session.commit()
        return jsonify(msg=f'成功爬取 {result["book_count"]} 本书，{result["chapter_count"]} 个章节', data=result)
    except Exception as e:
        return jsonify(msg=f'爬取失败: {str(e)}'), 500


@books_bp.route('/list', methods=['GET'])
@jwt_required()
def get_books():
    user_id = int(get_jwt_identity())
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    keyword = request.args.get('keyword', '').strip()
    source_id = request.args.get('source_id', type=int)
    category = request.args.get('category', '').strip()
    group_id = request.args.get('group_id', type=int)

    query = Book.query.join(BookSource).filter(BookSource.user_id == user_id)

    if keyword:
        query = query.filter(or_(Book.title.contains(keyword), Book.author.contains(keyword)))
    if source_id:
        query = query.filter(Book.source_id == source_id)
    if category:
        query = query.filter(Book.category == category)
    if group_id:
        query = query.filter(Book.group_id == group_id)

    pagination = query.order_by(Book.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)

    books = []
    for b in pagination.items:
        chapter_count = Chapter.query.filter_by(book_id=b.id).count()
        progress = ReadingProgress.query.filter_by(user_id=user_id, book_id=b.id).first()
        src = BookSource.query.get(b.source_id)
        books.append({
            'id': b.id, 'title': b.title, 'author': b.author,
            'cover_url': b.cover_url, 'description': b.description,
            'category': b.category, 'word_count': b.word_count,
            'status': b.status, 'chapter_count': chapter_count,
            'source_id': b.source_id,
            'source_name': src.name if src else '未知',
            'group_id': b.group_id,
            'progress': {
                'chapter_index': progress.current_chapter_index if progress else 0,
                'scroll_position': progress.scroll_position if progress else 0
            } if progress else None
        })

    return jsonify({
        'books': books,
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages
    })


@books_bp.route('/<int:book_id>', methods=['GET'])
@jwt_required()
def get_book(book_id):
    user_id = int(get_jwt_identity())
    book = Book.query.join(BookSource).filter(Book.id == book_id, BookSource.user_id == user_id).first()
    if not book:
        return jsonify(msg='书籍不存在'), 404

    chapters = Chapter.query.filter_by(book_id=book_id).order_by(Chapter.chapter_index).all()
    src = BookSource.query.get(book.source_id)

    return jsonify({
        'id': book.id, 'title': book.title, 'author': book.author,
        'cover_url': book.cover_url, 'description': book.description,
        'category': book.category, 'word_count': book.word_count,
        'status': book.status, 'source_id': book.source_id,
        'source_name': src.name if src else '未知',
        'book_url': book.book_url,
        'group_id': book.group_id,
        'chapters': [{'id': c.id, 'index': c.chapter_index, 'title': c.title} for c in chapters]
    })


@books_bp.route('/<int:book_id>', methods=['DELETE'])
@jwt_required()
def delete_book(book_id):
    user_id = int(get_jwt_identity())
    book = Book.query.join(BookSource).filter(Book.id == book_id, BookSource.user_id == user_id).first()
    if not book:
        return jsonify(msg='书籍不存在'), 404

    Chapter.query.filter_by(book_id=book_id).delete()
    ReadingProgress.query.filter_by(book_id=book_id).delete()
    db.session.delete(book)
    db.session.commit()
    return jsonify(msg='删除成功')


@books_bp.route('/categories', methods=['GET'])
@jwt_required()
def get_categories():
    user_id = int(get_jwt_identity())
    sources = BookSource.query.filter_by(user_id=user_id).with_entities(BookSource.id).all()
    source_ids = [s.id for s in sources]

    categories = db.session.query(Book.category).filter(
        Book.source_id.in_(source_ids)
    ).distinct().all()

    return jsonify([c[0] for c in categories])


# ===== 搜索换源 API =====

@books_bp.route('/<int:book_id>/search-sources', methods=['GET'])
@jwt_required()
def search_book_sources(book_id):
    """搜索其他站点上同名书籍，供换源使用"""
    user_id = int(get_jwt_identity())
    book = Book.query.join(BookSource).filter(Book.id == book_id, BookSource.user_id == user_id).first()
    if not book:
        return jsonify(msg='书籍不存在'), 404

    try:
        results = search_other_sources(book.title, book.author)
        return jsonify(results)
    except Exception as e:
        return jsonify(msg=f'搜索失败: {str(e)}', results=[]), 500


@books_bp.route('/<int:book_id>/switch-source', methods=['POST'])
@jwt_required()
def switch_book_source(book_id):
    """换源：根据搜索结果URL重新爬取该书"""
    user_id = int(get_jwt_identity())
    book = Book.query.join(BookSource).filter(Book.id == book_id, BookSource.user_id == user_id).first()
    if not book:
        return jsonify(msg='书籍不存在'), 404

    data = request.get_json()
    new_url = data.get('url', '').strip()
    source_name = data.get('source_name', '').strip()

    if not new_url:
        return jsonify(msg='URL不能为空'), 400

    try:
        from scraper.crawler import crawl_single_book
        result = crawl_single_book(new_url, book.title)
        if not result or not result.get('chapters'):
            return jsonify(msg='未能从该源获取到章节'), 400

        # 更新书源或创建新书源
        if source_name:
            existing_source = BookSource.query.filter_by(user_id=user_id, name=source_name).first()
            if existing_source:
                book.source_id = existing_source.id
            else:
                new_source = BookSource(user_id=user_id, name=source_name, url=new_url)
                db.session.add(new_source)
                db.session.flush()
                book.source_id = new_source.id

        book.book_url = new_url
        if result.get('cover_url'):
            book.cover_url = result['cover_url']
        if result.get('description'):
            book.description = result['description']
        if result.get('category'):
            book.category = result['category']

        # 删除旧章节，写入新章节
        Chapter.query.filter_by(book_id=book_id).delete()
        for ch_data in result.get('chapters', []):
            chapter = Chapter(
                book_id=book_id,
                chapter_index=ch_data['index'],
                title=ch_data['title'],
                url=ch_data['url']
            )
            db.session.add(chapter)

        # 重置阅读进度
        progress = ReadingProgress.query.filter_by(user_id=user_id, book_id=book_id).first()
        if progress:
            progress.current_chapter_index = 0
            progress.current_chapter_id = None
            progress.scroll_position = 0.0

        db.session.commit()
        return jsonify(msg=f'换源成功，共 {len(result.get("chapters", []))} 章')
    except Exception as e:
        db.session.rollback()
        return jsonify(msg=f'换源失败: {str(e)}'), 500


# ===== 搜书 API =====

@books_bp.route('/search', methods=['GET'])
@jwt_required()
def search_books_api():
    """搜书：优先从已有书源搜索，搜不到再从百度搜索"""
    user_id = int(get_jwt_identity())
    keyword = request.args.get('keyword', '').strip()
    if not keyword:
        return jsonify(msg='请输入搜索关键字'), 400

    # 获取用户已添加的书源URL列表
    sources = BookSource.query.filter_by(user_id=user_id).all()
    source_urls = [s.url for s in sources]

    try:
        results = search_books(keyword, source_urls)
        return jsonify(results)
    except Exception as e:
        return jsonify(msg=f'搜索失败: {str(e)}', results=[]), 500


@books_bp.route('/search/add', methods=['POST'])
@jwt_required()
def add_book_from_search():
    """从搜索结果添加书籍到书架：爬取该书并入库"""
    user_id = int(get_jwt_identity())
    data = request.get_json()
    url = data.get('url', '').strip()
    source_name = data.get('source_name', '').strip()
    title = data.get('title', '').strip()

    if not url:
        return jsonify(msg='URL不能为空'), 400

    try:
        from scraper.crawler import crawl_single_book
        result = crawl_single_book(url, title)
        if not result or not result.get('chapters'):
            return jsonify(msg='未能从该源获取到章节内容'), 400

        # 查找或创建书源
        source = None
        if source_name:
            source = BookSource.query.filter_by(user_id=user_id, name=source_name).first()
        if not source:
            source = BookSource(user_id=user_id, name=source_name or url, url=url)
            db.session.add(source)
            db.session.flush()

        # 检查是否已存在
        existing = Book.query.filter_by(source_id=source.id, book_url=result['book_url']).first()
        if existing:
            return jsonify(msg='该书已在书架中', book_id=existing.id), 200

        book = Book(
            source_id=source.id,
            title=result.get('title', title),
            author=result.get('author', '未知'),
            cover_url=result.get('cover_url', ''),
            description=result.get('description', ''),
            book_url=result['book_url'],
            category=result.get('category', '未分类'),
            word_count=result.get('word_count', ''),
            status=result.get('status', '连载中')
        )
        db.session.add(book)
        db.session.flush()

        for ch_data in result.get('chapters', []):
            chapter = Chapter(
                book_id=book.id,
                chapter_index=ch_data['index'],
                title=ch_data['title'],
                url=ch_data['url']
            )
            db.session.add(chapter)

        db.session.commit()
        return jsonify(msg='添加成功', book_id=book.id), 201
    except Exception as e:
        db.session.rollback()
        return jsonify(msg=f'添加失败: {str(e)}'), 500


# ===== 分组 API =====

@books_bp.route('/groups', methods=['GET'])
@jwt_required()
def get_groups():
    user_id = int(get_jwt_identity())
    groups = BookGroup.query.filter_by(user_id=user_id).order_by(BookGroup.sort_order, BookGroup.created_at).all()
    result = []
    for g in groups:
        book_count = Book.query.filter_by(group_id=g.id).count()
        result.append({
            'id': g.id, 'name': g.name,
            'sort_order': g.sort_order, 'book_count': book_count
        })
    return jsonify(result)


@books_bp.route('/groups', methods=['POST'])
@jwt_required()
def add_group():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    name = data.get('name', '').strip()
    if not name:
        return jsonify(msg='分组名称不能为空'), 400

    max_order = db.session.query(db.func.max(BookGroup.sort_order)).filter_by(user_id=user_id).scalar() or 0
    group = BookGroup(user_id=user_id, name=name, sort_order=max_order + 1)
    db.session.add(group)
    db.session.commit()
    return jsonify(msg='分组创建成功', group={'id': group.id, 'name': group.name, 'sort_order': group.sort_order}), 201


@books_bp.route('/groups/<int:group_id>', methods=['PUT'])
@jwt_required()
def update_group(group_id):
    user_id = int(get_jwt_identity())
    group = BookGroup.query.filter_by(id=group_id, user_id=user_id).first()
    if not group:
        return jsonify(msg='分组不存在'), 404

    data = request.get_json()
    if 'name' in data:
        name = data['name'].strip()
        if not name:
            return jsonify(msg='分组名称不能为空'), 400
        group.name = name
    if 'sort_order' in data:
        group.sort_order = data['sort_order']

    db.session.commit()
    return jsonify(msg='分组更新成功')


@books_bp.route('/groups/<int:group_id>', methods=['DELETE'])
@jwt_required()
def delete_group(group_id):
    user_id = int(get_jwt_identity())
    group = BookGroup.query.filter_by(id=group_id, user_id=user_id).first()
    if not group:
        return jsonify(msg='分组不存在'), 404

    # 将该分组下的书籍移至未分组
    Book.query.filter_by(group_id=group_id).update({'group_id': None})
    db.session.delete(group)
    db.session.commit()
    return jsonify(msg='分组删除成功，书籍已移至未分组')


@books_bp.route('/<int:book_id>/group', methods=['PUT'])
@jwt_required()
def set_book_group(book_id):
    """设置书籍所属分组"""
    user_id = int(get_jwt_identity())
    book = Book.query.join(BookSource).filter(Book.id == book_id, BookSource.user_id == user_id).first()
    if not book:
        return jsonify(msg='书籍不存在'), 404

    data = request.get_json()
    group_id = data.get('group_id')  # None = 未分组

    if group_id is not None:
        group = BookGroup.query.filter_by(id=group_id, user_id=user_id).first()
        if not group:
            return jsonify(msg='分组不存在'), 404

    book.group_id = group_id
    db.session.commit()
    return jsonify(msg='分组设置成功')
