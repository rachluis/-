from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session
import json
import os

login_bp = Blueprint('login', __name__)

# 用户数据文件路径
USERS_FILE = 'data/users.json'

def load_users():
    """加载用户数据"""
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_users(users):
    """保存用户数据"""
    os.makedirs('data', exist_ok=True)
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=4)

@login_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        # 验证密码长度
        if len(password) < 6 or len(password) > 18:
            return jsonify({
                'success': False,
                'message': '密码长度必须在6-18位之间'
            })
        
        users = load_users()
        
        # 如果是首次登录，创建用户
        if username not in users:
            users[username] = {
                'password': password,
                'login_attempts': 0,
                'last_attempt': None
            }
            save_users(users)
            session['username'] = username
            return jsonify({'success': True})
        
        # 验证密码
        if users[username]['password'] == password:
            users[username]['login_attempts'] = 0
            users[username]['last_attempt'] = None
            save_users(users)
            session['username'] = username
            return jsonify({'success': True})
        
        # 登录失败
        users[username]['login_attempts'] = users[username].get('login_attempts', 0) + 1
        save_users(users)
        
        return jsonify({
            'success': False,
            'message': '用户名或密码错误'
        })

@login_bp.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login.login'))