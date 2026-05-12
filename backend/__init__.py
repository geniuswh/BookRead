import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_jwt_extended import JWTManager

db = SQLAlchemy()
jwt = JWTManager()


def create_app():
    app = Flask(__name__)

    base_dir = os.path.abspath(os.path.dirname(__file__))
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(base_dir, 'bookread.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'bookread-secret-key-change-in-prod')
    app.config['JSON_AS_ASCII'] = False

    # 生产环境安全检查
    if app.config['JWT_SECRET_KEY'] == 'bookread-secret-key-change-in-prod':
        logging.warning('⚠️ JWT_SECRET_KEY 使用默认值，请在生产环境中设置环境变量！')

    # CORS：支持环境变量配置，默认允许本地开发
    cors_origins = os.environ.get('CORS_ORIGINS', 'http://localhost:5173').split(',')
    CORS(app, supports_credentials=True, origins=[o.strip() for o in cors_origins])
    db.init_app(app)
    jwt.init_app(app)

    from routes.auth import auth_bp
    from routes.books import books_bp
    from routes.reader import reader_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(books_bp, url_prefix='/api/books')
    app.register_blueprint(reader_bp, url_prefix='/api/reader')

    with app.app_context():
        import models
        db.create_all()

    return app
