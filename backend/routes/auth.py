from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity

from __init__ import db
from models import User, ReaderPreference

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '').strip()

    if not username or not email or not password:
        return jsonify(msg='用户名、邮箱和密码不能为空'), 400

    if len(username) < 3 or len(username) > 20:
        return jsonify(msg='用户名长度需在3-20之间'), 400

    if len(password) < 6:
        return jsonify(msg='密码长度不能少于6位'), 400

    if User.query.filter_by(username=username).first():
        return jsonify(msg='用户名已存在'), 409

    if User.query.filter_by(email=email).first():
        return jsonify(msg='邮箱已被注册'), 409

    user = User(
        username=username,
        email=email,
        password_hash=generate_password_hash(password)
    )
    db.session.add(user)
    db.session.flush()

    pref = ReaderPreference(user_id=user.id)
    db.session.add(pref)
    db.session.commit()

    token = create_access_token(identity=str(user.id))
    return jsonify(token=token, user={'id': user.id, 'username': user.username, 'email': user.email}), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    login_name = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if not login_name or not password:
        return jsonify(msg='请输入用户名和密码'), 400

    user = User.query.filter((User.username == login_name) | (User.email == login_name)).first()

    if not user or not check_password_hash(user.password_hash, password):
        return jsonify(msg='用户名或密码错误'), 401

    token = create_access_token(identity=str(user.id))
    return jsonify(token=token, user={'id': user.id, 'username': user.username, 'email': user.email})


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_me():
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    if not user:
        return jsonify(msg='用户不存在'), 404

    return jsonify(id=user.id, username=user.username, email=user.email, avatar=user.avatar)


@auth_bp.route('/me', methods=['PUT'])
@jwt_required()
def update_me():
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    data = request.get_json()

    if 'username' in data:
        new_name = data['username'].strip()
        existing = User.query.filter(User.username == new_name, User.id != user_id).first()
        if existing:
            return jsonify(msg='用户名已存在'), 409
        user.username = new_name

    if 'email' in data:
        new_email = data['email'].strip()
        existing = User.query.filter(User.email == new_email, User.id != user_id).first()
        if existing:
            return jsonify(msg='邮箱已被使用'), 409
        user.email = new_email

    if 'password' in data:
        user.password_hash = generate_password_hash(data['password'])

    db.session.commit()
    return jsonify(msg='更新成功', user={'id': user.id, 'username': user.username, 'email': user.email})
