import os
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

    CORS(app, supports_credentials=True, origins=['http://localhost:5173'])
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
