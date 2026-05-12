from __init__ import db
from datetime import datetime


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    avatar = db.Column(db.String(500), default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    preferences = db.relationship('ReaderPreference', backref='user', uselist=False, lazy=True)
    book_sources = db.relationship('BookSource', backref='user', lazy=True)
    reading_progress = db.relationship('ReadingProgress', backref='user', lazy=True)
    book_groups = db.relationship('BookGroup', backref='user', lazy=True)


class BookSource(db.Model):
    __tablename__ = 'book_sources'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    url = db.Column(db.String(1000), nullable=False)
    source_type = db.Column(db.String(50), default='custom')
    last_crawled = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    books = db.relationship('Book', backref='source', lazy=True)


class BookGroup(db.Model):
    __tablename__ = 'book_groups'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    books = db.relationship('Book', backref='group', lazy=True)


class Book(db.Model):
    __tablename__ = 'books'

    id = db.Column(db.Integer, primary_key=True)
    source_id = db.Column(db.Integer, db.ForeignKey('book_sources.id'), nullable=False)
    title = db.Column(db.String(300), nullable=False)
    author = db.Column(db.String(200), default='未知')
    cover_url = db.Column(db.String(1000), default='')
    description = db.Column(db.Text, default='')
    book_url = db.Column(db.String(1000), nullable=False)
    category = db.Column(db.String(100), default='未分类')
    word_count = db.Column(db.String(50), default='')
    status = db.Column(db.String(50), default='连载中')
    group_id = db.Column(db.Integer, db.ForeignKey('book_groups.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    chapters = db.relationship('Chapter', backref='book', lazy=True, order_by='Chapter.chapter_index')
    reading_progress = db.relationship('ReadingProgress', backref='book', lazy=True)


class Chapter(db.Model):
    __tablename__ = 'chapters'

    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False)
    chapter_index = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(500), nullable=False)
    url = db.Column(db.String(1000), nullable=False)
    content = db.Column(db.Text, default='')


class ReadingProgress(db.Model):
    __tablename__ = 'reading_progress'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False)
    current_chapter_id = db.Column(db.Integer, db.ForeignKey('chapters.id'), nullable=True)
    current_chapter_index = db.Column(db.Integer, default=0)
    scroll_position = db.Column(db.Float, default=0.0)
    last_read_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('user_id', 'book_id'),)


class ReaderPreference(db.Model):
    __tablename__ = 'reader_preferences'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    font_family = db.Column(db.String(100), default='Noto Serif SC')
    font_size = db.Column(db.Integer, default=18)
    line_height = db.Column(db.Float, default=1.8)
    letter_spacing = db.Column(db.Float, default=0.5)
    paragraph_spacing = db.Column(db.Float, default=16.0)
    page_width = db.Column(db.Integer, default=800)
    theme = db.Column(db.String(50), default='light')
    bg_color = db.Column(db.String(20), default='#ffffff')
    text_color = db.Column(db.String(20), default='#333333')
