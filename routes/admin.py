from flask import Blueprint, request, jsonify
from models import User, DataImportLog, SystemLog
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import os
import csv
import pandas as pd

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/api/users', methods=['GET'])
def get_users():
    # 获取所有用户
    users = User.query.all()

    return jsonify([{
        'id': user.id,
        'username': user.username,
        'created_at': user.created_at.isoformat() if user.created_at else None,
        'last_login': user.last_login.isoformat() if user.last_login else None
    } for user in users])


@admin_bp.route('/api/user/<int:user_id>', methods=['GET'])
def get_user(user_id):
    # 获取指定用户
    user = User.query.get_or_404(user_id)

    return jsonify({
        'id': user.id,
        'username': user.username,
        'created_at': user.created_at.isoformat() if user.created_at else None,
        'last_login': user.last_login.isoformat() if user.last_login else None
    })


@admin_bp.route('/api/user', methods=['POST'])
def create_user():
    # 创建新用户
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({
            'success': False,
            'message': '用户名和密码不能为空'
        }), 400

    # 检查用户名是否已存在
    if User.query.filter_by(username=username).first():
        return jsonify({
            'success': False,
            'message': '用户名已存在'
        }), 400

    # 创建新用户
    new_user = User(
        username=username,
        password=generate_password_hash(password),
        created_at=datetime.now()
    )

    db.session.add(new_user)
    db.session.commit()

    # 记录系统日志
    system_log = SystemLog(
        timestamp=datetime.now(),
        message=f"用户 '{username}' 创建成功"
    )
    db.session.add(system_log)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': '用户创建成功'
    })


@admin_bp.route('/api/user/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    # 更新用户信息
    user = User.query.get_or_404(user_id)
    data = request.get_json()

    password = data.get('password')

    if password:
        user.password = generate_password_hash(password)

    user.last_login = datetime.now()
    db.session.commit()

    # 记录系统日志
    system_log = SystemLog(
        timestamp=datetime.now(),
        message=f"用户 '{user.username}' 更新成功"
    )
    db.session.add(system_log)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': '用户信息更新成功'
    })


@admin_bp.route('/api/user/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    # 删除用户
    user = User.query.get_or_404(user_id)

    # 不能删除当前登录用户
    if user.id == current_user.id:
        return jsonify({
            'success': False,
            'message': '不能删除当前登录用户'
        }), 400

    db.session.delete(user)
    db.session.commit()

    # 记录系统日志
    system_log = SystemLog(
        timestamp=datetime.now(),
        message=f"用户 '{user.username}' 已删除"
    )
    db.session.add(system_log)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': '用户已删除'
    })


@admin_bp.route('/api/data-import-logs', methods=['GET'])
def get_data_import_logs():
    # 获取数据导入日志
    logs = DataImportLog.query.order_by(DataImportLog.import_time.desc()).all()

    return jsonify([{
        'id': log.id,
        'operation': log.operation,
        'filename': log.filename,
        'import_time': log.import_time.isoformat(),
        'record_count': log.record_count,
        'success': log.success
    } for log in logs])


@admin_bp.route('/api/system-logs', methods=['GET'])
def get_system_logs():
    # 获取系统日志
    logs = SystemLog.query.order_by(SystemLog.timestamp.desc()).limit(20).all()

    return jsonify([{
        'timestamp': log.timestamp.isoformat(),
        'message': log.message
    } for log in logs])


@admin_bp.route('/api/import-data', methods=['POST'])
def import_data():
    # 导入新的用电数据
    file = request.files.get('file')
    file_type = request.form.get('type', 'csv')
    append = request.form.get('append', 'False') == 'True'

    if not file:
        return jsonify({
            'success': False,
            'message': '未选择文件'
        }), 400

    try:
        if file_type == 'csv':
            # 处理CSV文件
            data = pd.read_csv(file)
        elif file_type == 'excel':
            # 处理Excel文件
            data = pd.read_excel(file)
        else:
            return jsonify({
                'success': False,
                'message': '不支持的文件类型'
            }), 400

        # 验证数据格式
        required_columns = {'timestamp', 'device', 'power', 'energy'}
        if not required_columns.issubset(data.columns):
            return jsonify({
                'success': False,
                'message': '文件格式错误，缺少必要列'
            }), 400

        # 记录导入操作
        import_log = DataImportLog(
            operation='数据导入',
            filename=file.filename,
            import_time=datetime.now(),
            record_count=len(data),
            success=True
        )

        # 处理导入模式
        if not append:
            # 清空现有数据
            db.session.query(EnergyRecord).delete()
            db.session.commit()

        # 导入数据
        for _, row in data.iterrows():
            device = Device.query.filter_by(name=row['device']).first()
            if not device:
                device = Device(name=row['device'])
                db.session.add(device)

            record = EnergyRecord(
                timestamp=datetime.fromisoformat(row['timestamp']),
                device=device,
                power=row['power'],
                energy=row['energy']
            )
            db.session.add(record)

        db.session.commit()

        # 记录系统日志
        system_log = SystemLog(
            timestamp=datetime.now(),
            message=f"成功导入 {len(data)} 条数据"
        )
        db.session.add(system_log)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'成功导入 {len(data)} 条数据'
        })

    except Exception as e:
        # 记录失败的导入操作
        import_log = DataImportLog(
            operation='数据导入',
            filename=file.filename,
            import_time=datetime.now(),
            record_count=0,
            success=False,
            error=str(e)
        )
        db.session.add(import_log)
        db.session.commit()

        # 记录系统日志
        system_log = SystemLog(
            timestamp=datetime.now(),
            message=f"数据导入失败: {str(e)}"
        )
        db.session.add(system_log)
        db.session.commit()

        return jsonify({
            'success': False,
            'message': str(e)
        }), 500