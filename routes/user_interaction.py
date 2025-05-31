from flask import Blueprint, render_template, jsonify, request
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import json
import os

user_interaction_bp = Blueprint('user_interaction', __name__)

# 通知存储文件
NOTIFICATIONS_FILE = 'data/notifications.json'
# 报告存储文件
REPORTS_FILE = 'data/reports.json'

def load_notifications():
    """加载通知数据"""
    if os.path.exists(NOTIFICATIONS_FILE):
        with open(NOTIFICATIONS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_notifications(notifications):
    """保存通知数据"""
    os.makedirs('data', exist_ok=True)
    with open(NOTIFICATIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(notifications, f, ensure_ascii=False, indent=4)

def load_reports():
    """加载报告数据"""
    if os.path.exists(REPORTS_FILE):
        with open(REPORTS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_reports(reports):
    """保存报告数据"""
    os.makedirs('data', exist_ok=True)
    with open(REPORTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(reports, f, ensure_ascii=False, indent=4)

def add_notification(title, message, notification_type='info'):
    """添加新通知"""
    notifications = load_notifications()
    notification = {
        'id': len(notifications) + 1,
        'title': title,
        'message': message,
        'type': notification_type,
        'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'unread': True
    }
    notifications.insert(0, notification)
    save_notifications(notifications)
    return notification

def generate_report(report_type):
    """生成报告"""
    reports = load_reports()
    
    if report_type == 'daily':
        # 生成每日用电报告
        df = pd.read_csv('data/energy_data.csv')
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        today = datetime.now().date()
        today_data = df[df['timestamp'].dt.date == today]
        
        total_energy = today_data['total_energy'].sum()
        avg_power = today_data['total_power'].mean()
        max_power = today_data['total_power'].max()
        
        report = {
            'id': len(reports) + 1,
            'title': '每日用电报告',
            'content': f'今日总用电量：{total_energy:.2f} kWh\n'
                      f'平均功率：{avg_power:.2f} W\n'
                      f'最大功率：{max_power:.2f} W',
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'type': 'daily'
        }
    elif report_type == 'weekly':
        # 生成每周用电报告
        df = pd.read_csv('data/energy_data.csv')
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=7)
        week_data = df[(df['timestamp'].dt.date >= start_date) & 
                      (df['timestamp'].dt.date <= end_date)]
        
        total_energy = week_data['total_energy'].sum()
        avg_daily_energy = total_energy / 7
        
        report = {
            'id': len(reports) + 1,
            'title': '每周用电报告',
            'content': f'本周总用电量：{total_energy:.2f} kWh\n'
                      f'日均用电量：{avg_daily_energy:.2f} kWh',
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'type': 'weekly'
        }
    
    reports.insert(0, report)
    save_reports(reports)
    return report

@user_interaction_bp.route('/user-interaction')
def user_interaction():
    """用户交互页面"""
    return render_template('user_interaction.html')

@user_interaction_bp.route('/api/search', methods=['POST'])
def search():
    """处理搜索请求"""
    try:
        data = request.get_json()
        query = data.get('query', '').lower()
        
        results = []
        
        # 根据查询内容返回相应的结果
        if '今日用电' in query:
            df = pd.read_csv('data/energy_data.csv')
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            today = datetime.now().date()
            today_data = df[df['timestamp'].dt.date == today]
            
            total_energy = today_data['total_energy'].sum()
            avg_power = today_data['total_power'].mean()
            
            results.append(f'今日总用电量：{total_energy:.2f} kWh')
            results.append(f'平均功率：{avg_power:.2f} W')
            
        elif '节能建议' in query:
            # 从模式分析模块获取建议
            df = pd.read_csv('data/energy_data.csv')
            device_power_cols = [col for col in df.columns if '_power' in col and col != 'total_power']
            device_avg_power = df[device_power_cols].mean()
            
            for device, avg_power in device_avg_power.items():
                device_name = device.replace('_power', '')
                if avg_power > 300:
                    results.append(f'{device_name}平均功率较高（{avg_power:.1f}W），建议检查使用情况')
        
        elif '设备使用' in query:
            df = pd.read_csv('data/energy_data.csv')
            device_power_cols = [col for col in df.columns if '_power' in col and col != 'total_power']
            device_usage_time = df[device_power_cols].apply(lambda x: (x > 0).sum() * 5 / 60)  # 转换为小时
            
            for device, hours in device_usage_time.items():
                device_name = device.replace('_power', '')
                results.append(f'{device_name}今日使用时长：{hours:.1f}小时')
        
        elif '用电趋势' in query:
            df = pd.read_csv('data/energy_data.csv')
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['hour'] = df['timestamp'].dt.hour
            hourly_avg = df.groupby('hour')['total_power'].mean()
            
            peak_hour = hourly_avg.idxmax()
            peak_power = hourly_avg.max()
            
            results.append(f'用电高峰时段：{peak_hour}时')
            results.append(f'高峰时段平均功率：{peak_power:.1f}W')
        
        elif '异常记录' in query:
            anomalies = load_notifications()
            anomaly_notifications = [n for n in anomalies if n['type'] == 'warning']
            
            for notification in anomaly_notifications[:5]:  # 只显示最近5条
                results.append(f"{notification['time']} - {notification['message']}")
        
        elif '用电报告' in query:
            report = generate_report('daily')
            results.append(f'已生成每日用电报告：{report["content"]}')
        
        return jsonify({
            'success': True,
            'results': results
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'处理查询时出错：{str(e)}'
        })

@user_interaction_bp.route('/api/notifications')
def get_notifications():
    """获取通知列表"""
    try:
        notifications = load_notifications()
        return jsonify(notifications)
    except Exception as e:
        return jsonify([])

@user_interaction_bp.route('/api/reports')
def get_reports():
    """获取报告列表"""
    try:
        reports = load_reports()
        return jsonify(reports)
    except Exception as e:
        return jsonify([])

@user_interaction_bp.route('/api/chart-data')
def get_chart_data():
    """获取图表数据"""
    try:
        df = pd.read_csv('data/energy_data.csv')
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # 获取最近24小时的数据
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=24)
        recent_data = df[(df['timestamp'] >= start_time) & (df['timestamp'] <= end_time)]
        
        # 功率趋势数据
        power_trend = {
            'labels': recent_data['timestamp'].dt.strftime('%H:%M').tolist(),
            'data': recent_data['total_power'].tolist()
        }
        
        # 设备使用时长数据
        device_power_cols = [col for col in df.columns if '_power' in col and col != 'total_power']
        device_usage = df[device_power_cols].apply(lambda x: (x > 0).sum() * 5 / 60)  # 转换为小时
        
        device_usage_data = {
            'labels': [col.replace('_power', '') for col in device_usage.index],
            'data': device_usage.tolist()
        }
        
        return jsonify({
            'powerTrend': power_trend,
            'deviceUsage': device_usage_data
        })
    except Exception as e:
        return jsonify({
            'powerTrend': {'labels': [], 'data': []},
            'deviceUsage': {'labels': [], 'data': []}
        }) 