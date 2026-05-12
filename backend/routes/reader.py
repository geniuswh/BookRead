from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime

from __init__ import db
from models import ReaderPreference, Chapter, Book, ReadingProgress, BookSource
from scraper.crawler import crawl_chapter_content

reader_bp = Blueprint('reader', __name__)


@reader_bp.route('/preferences', methods=['GET'])
@jwt_required()
def get_preferences():
    user_id = int(get_jwt_identity())
    pref = ReaderPreference.query.filter_by(user_id=user_id).first()
    if not pref:
        pref = ReaderPreference(user_id=user_id)
        db.session.add(pref)
        db.session.commit()

    return jsonify({
        'font_family': pref.font_family,
        'font_size': pref.font_size,
        'line_height': pref.line_height,
        'letter_spacing': pref.letter_spacing,
        'paragraph_spacing': pref.paragraph_spacing,
        'page_width': pref.page_width,
        'theme': pref.theme,
        'bg_color': pref.bg_color,
        'text_color': pref.text_color
    })


@reader_bp.route('/preferences', methods=['PUT'])
@jwt_required()
def update_preferences():
    user_id = int(get_jwt_identity())
    pref = ReaderPreference.query.filter_by(user_id=user_id).first()
    if not pref:
        pref = ReaderPreference(user_id=user_id)
        db.session.add(pref)

    data = request.get_json()
    fields = ['font_family', 'font_size', 'line_height', 'letter_spacing',
              'paragraph_spacing', 'page_width', 'theme', 'bg_color', 'text_color']

    for field in fields:
        if field in data:
            setattr(pref, field, data[field])

    db.session.commit()
    return jsonify(msg='偏好更新成功')


@reader_bp.route('/chapter/<int:chapter_id>', methods=['GET'])
@jwt_required()
def get_chapter(chapter_id):
    user_id = int(get_jwt_identity())
    chapter = Chapter.query.get(chapter_id)
    if not chapter:
        return jsonify(msg='章节不存在'), 404

    book = Book.query.join(BookSource).filter(
        Book.id == chapter.book_id, BookSource.user_id == user_id
    ).first()
    if not book:
        return jsonify(msg='无权访问'), 403

    if not chapter.content:
        try:
            referer = book.book_url
            content = crawl_chapter_content(chapter.url, referer=referer)
            chapter.content = content
            db.session.commit()
        except Exception:
            pass

    total_chapters = Chapter.query.filter_by(book_id=book.id).count()
    prev_chapter = Chapter.query.filter_by(
        book_id=book.id, chapter_index=chapter.chapter_index - 1
    ).first()
    next_chapter = Chapter.query.filter_by(
        book_id=book.id, chapter_index=chapter.chapter_index + 1
    ).first()

    return jsonify({
        'id': chapter.id,
        'title': chapter.title,
        'content': chapter.content or '章节内容加载失败，请重新爬取',
        'chapter_index': chapter.chapter_index,
        'total_chapters': total_chapters,
        'prev_chapter_id': prev_chapter.id if prev_chapter else None,
        'next_chapter_id': next_chapter.id if next_chapter else None,
        'book_title': book.title
    })


@reader_bp.route('/progress/<int:book_id>', methods=['GET'])
@jwt_required()
def get_progress(book_id):
    user_id = int(get_jwt_identity())
    progress = ReadingProgress.query.filter_by(user_id=user_id, book_id=book_id).first()
    if not progress:
        return jsonify(chapter_index=0, scroll_position=0)

    return jsonify(
        chapter_index=progress.current_chapter_index,
        scroll_position=progress.scroll_position,
        chapter_id=progress.current_chapter_id
    )


@reader_bp.route('/progress/<int:book_id>', methods=['POST'])
@jwt_required()
def save_progress(book_id):
    user_id = int(get_jwt_identity())
    data = request.get_json()

    progress = ReadingProgress.query.filter_by(user_id=user_id, book_id=book_id).first()
    if not progress:
        progress = ReadingProgress(user_id=user_id, book_id=book_id)
        db.session.add(progress)

    if 'chapter_index' in data:
        progress.current_chapter_index = data['chapter_index']
    if 'chapter_id' in data:
        progress.current_chapter_id = data['chapter_id']
    if 'scroll_position' in data:
        progress.scroll_position = data['scroll_position']

    progress.last_read_at = datetime.utcnow()
    db.session.commit()
    return jsonify(msg='进度已保存')
