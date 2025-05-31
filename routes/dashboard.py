import pandas as pd
import numpy as np
from flask import Blueprint, render_template, jsonify
import os
from datetime import datetime, timedelta
import json

dashboard_bp = Blueprint('dashboard', __name__)

# 设备配置信息
DEVICE_CONFIGS = {
    '空调': {'base_power': 1000, 'max_power': 2000, 'min_power': 800, 'usage_hours': [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22]},
    '冰箱': {'base_power': 100, 'max_power': 150, 'min_power': 80, 'usage_hours': list(range(24))},
    '洗衣机': {'base_power': 500, 'max_power': 800, 'min_power': 400, 'usage_hours': [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]},
    '电视': {'base_power': 200, 'max_power': 300, 'min_power': 150, 'usage_hours': [18, 19, 20, 21, 22]},
    '电脑': {'base_power': 150, 'max_power': 250, 'min_power': 100, 'usage_hours': [9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21]},
    '热水器': {'base_power': 2000, 'max_power': 3000, 'min_power': 1500, 'usage_hours': [6, 7, 8, 19, 20, 21, 22]},
    '微波炉': {'base_power': 1000, 'max_power': 1500, 'min_power': 800, 'usage_hours': [7, 8, 9, 12, 13, 18, 19]},
    '电饭煲': {'base_power': 800, 'max_power': 1200, 'min_power': 600, 'usage_hours': [7, 8, 11, 12, 18, 19]},
    '照明': {'base_power': 100, 'max_power': 150, 'min_power': 50, 'usage_hours': [18, 19, 20, 21, 22, 23, 0, 1, 2, 3, 4, 5, 6, 7]},
    '路由器': {'base_power': 10, 'max_power': 15, 'min_power': 8, 'usage_hours': list(range(24))}
}

# 异常检测配置
ANOMALY_CONFIG = {
    'power_threshold': 3000,  # 功率阈值（瓦）
    'change_rate_threshold': 5.0,  # 变化率阈值（倍）
    'notification_cooldown': 300  # 通知冷却时间（秒）
}

# 存储最近的异常记录
recent_anomalies = []
# 记录上次通知时间
last_notification_time = {}

def is_device_active(hour, device_config):
    """检查设备在指定时间是否应该工作"""
    for start, end in device_config['usage_hours']:
        if start <= hour < end:
            # 添加随机性，使设备状态更自然
            if np.random.random() < 0.95:  # 95%的概率在预设时间内工作
                return True
    return False

def generate_device_power(hour, device_config):
    """生成设备在指定时间的功率"""
    if not is_device_active(hour, device_config):
        return 0
    
    # 基础功率加上随机波动
    base = device_config['base_power']
    
    # 根据时间段调整功率
    if hour in range(7, 9) or hour in range(18, 22):  # 早晚高峰
        base *= 1.2
    elif hour in range(23, 24) or hour in range(0, 6):  # 深夜
        base *= 0.8
    
    # 添加随机波动
    variation = np.random.normal(0, (device_config['max_power'] - device_config['min_power']) * 0.1)
    power = base + variation
    
    # 确保功率在合理范围内
    return max(device_config['min_power'], min(device_config['max_power'], power))

def detect_anomalies(current_data, previous_data):
    """检测异常用电情况"""
    anomalies = []
    current_time = datetime.now()

    for device, config in DEVICE_CONFIGS.items():
        device_power_col = f"{device}_power"
        if device_power_col in current_data and device_power_col in previous_data:
            current_power = current_data[device_power_col]
            previous_power = previous_data[device_power_col]

            # 检查功率是否超过阈值
            if current_power > ANOMALY_CONFIG['power_threshold']:
                # 检查通知冷却时间
                if device not in last_notification_time or \
                   (current_time - last_notification_time[device]).total_seconds() > ANOMALY_CONFIG['notification_cooldown']:
                    anomalies.append({
                        'device': device,
                        'type': 'high_power',
                        'message': f"{device}功率异常：{current_power:.1f}W，超过阈值{ANOMALY_CONFIG['power_threshold']}W"
                    })
                    last_notification_time[device] = current_time

            # 检查功率变化率
            if previous_power > 0:
                change_rate = current_power / previous_power
                if change_rate > ANOMALY_CONFIG['change_rate_threshold']:
                    if device not in last_notification_time or \
                       (current_time - last_notification_time[device]).total_seconds() > ANOMALY_CONFIG['notification_cooldown']:
                        anomalies.append({
                            'device': device,
                            'type': 'sudden_change',
                            'message': f"{device}功率突变：从{previous_power:.1f}W增加到{current_power:.1f}W，变化率{change_rate:.1f}倍"
                        })
                        last_notification_time[device] = current_time

    return anomalies

def initialize_data():
    """初始化能源数据文件"""
    if not os.path.exists('data/energy_data.csv'):
        # 创建时间序列（最近24小时，每5分钟一个数据点）
        end_time = datetime.now()
        start_time = end_time - timedelta(days=1)
        time_list = [start_time + timedelta(minutes=i * 5) for i in range(24 * 12)]

        # 创建数据字典
        data = {
            'timestamp': [t.strftime('%Y-%m-%d %H:%M:%S') for t in time_list]
        }

        # 为每个设备生成功率数据
        for device, config in DEVICE_CONFIGS.items():
            powers = []
            for t in time_list:
                hour = t.hour
                power = generate_device_power(hour, config)
                
                # 添加随机波动
                if power > 0:
                    # 添加±10%的随机波动
                    variation = np.random.normal(0, power * 0.1)
                    power = max(0, power + variation)
                
                powers.append(power)
            
            data[f"{device}_power"] = powers
            # 计算能耗（功率 * 时间，转换为kWh）
            data[f"{device}_energy"] = [p * 5/60/1000 for p in powers]

        # 计算总功率和总能耗
        power_columns = [col for col in data.keys() if col.endswith('_power')]
        data['total_power'] = [sum(data[col][i] for col in power_columns) for i in range(len(time_list))]
        data['total_energy'] = [sum(data[col][i] for col in data.keys() if col.endswith('_energy')) for i in range(len(time_list))]

        # 创建DataFrame并保存
        df = pd.DataFrame(data)
        
        # 确保数据目录存在
        os.makedirs('data', exist_ok=True)
        
        # 保存数据
        df.to_csv('data/energy_data.csv', index=False)
        print("能源数据文件已初始化")

def read_energy_data():
    """读取能源数据"""
    try:
        if not os.path.exists('data/energy_data.csv'):
            initialize_data()
        return pd.read_csv('data/energy_data.csv')
    except Exception as e:
        print(f"读取能源数据时出错: {str(e)}")
        initialize_data()  # 如果读取失败，重新初始化
        return pd.read_csv('data/energy_data.csv')

def update_energy_data(new_data):
    """更新能源数据"""
    try:
        if os.path.exists('data/energy_data.csv'):
            existing_data = read_energy_data()
            updated_data = pd.concat([existing_data, new_data], ignore_index=True)
            updated_data.to_csv('data/energy_data.csv', index=False)
        else:
            new_data.to_csv('data/energy_data.csv', index=False)
    except Exception as e:
        print(f"更新能源数据时出错: {str(e)}")

def generate_new_data_point():
    """生成新的数据点"""
    current_time = datetime.now()
    data = {'timestamp': current_time.strftime('%Y-%m-%d %H:%M:%S')}
    
    # 为每个设备生成当前功率
    for device, config in DEVICE_CONFIGS.items():
        power = generate_device_power(current_time.hour, config)
        data[f"{device}_power"] = power
        data[f"{device}_energy"] = power * 5/60/1000  # 转换为kWh

    # 计算总功率和总能耗
    power_columns = [col for col in data.keys() if col.endswith('_power')]
    data['total_power'] = sum(data[col] for col in power_columns)
    data['total_energy'] = sum(data[col] for col in data.keys() if col.endswith('_energy'))

    return data

@dashboard_bp.route('/dashboard')
def dashboard():
    """仪表板页面"""
    try:
        df = read_energy_data()
        recent_df = df.tail(24 * 12)  # 最近24小时的数据

        # 准备数据以传递到前端
        timestamps = recent_df['timestamp'].tolist()
        total_power = recent_df['total_power'].tolist()

        return render_template('dashboard.html', timestamps=timestamps, total_power=total_power)
    except Exception as e:
        print(f"加载仪表板时出错: {str(e)}")
        return render_template('dashboard.html', error="加载数据时出错，请稍后重试")

@dashboard_bp.route('/api/real-time-data')
def real_time_data():
    """获取实时数据"""
    try:
        # 读取现有数据
        df = read_energy_data()
        previous_data = df.iloc[-1].to_dict() if not df.empty else None

        # 生成新数据点
        new_data = generate_new_data_point()
        
        # 检测异常
        if previous_data:
            anomalies = detect_anomalies(new_data, previous_data)
            if anomalies:
                # 将异常记录添加到列表
                recent_anomalies.extend(anomalies)
                # 只保留最近100条记录
                if len(recent_anomalies) > 100:
                    recent_anomalies.pop(0)

        # 更新数据文件
        new_df = pd.DataFrame([new_data])
        update_energy_data(new_df)

        # 准备返回数据
        response_data = {
            'time': new_data['timestamp'],
            'power': float(new_data['total_power']),
            'anomalies': anomalies if 'anomalies' in locals() else []
        }

        return jsonify(response_data)
    except Exception as e:
        print(f"获取实时数据时出错: {str(e)}")
        return jsonify({
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'power': 0,
            'anomalies': []
        })

@dashboard_bp.route('/api/anomaly-records')
def get_anomaly_records():
    """获取异常记录"""
    return jsonify(recent_anomalies)

@dashboard_bp.route('/api/top-devices')
def top_devices():
    """获取设备用电排行"""
    try:
        df = read_energy_data()

        # 计算每个设备的平均功率
        device_power_cols = [col for col in df.columns if '_power' in col and col != 'total_power']
        device_avg_power = df[device_power_cols].mean()

        # 获取平均功率最高的5个设备
        top5_devices = device_avg_power.nlargest(5)

        return jsonify({
            'labels': [col.replace('_power', '') for col in top5_devices.index],
            'data': [float(power) for power in top5_devices.tolist()]
        })
    except Exception as e:
        print(f"获取设备排行时出错: {str(e)}")
        return jsonify({
            'labels': [],
            'data': []
        })

@dashboard_bp.route('/api/device-status')
def device_status():
    """获取设备状态"""
    try:
        df = read_energy_data()
        if df.empty:
            return jsonify([])

        # 获取最新时间点的数据
        latest_row = df.iloc[-1]

        device_status = []
        for col in df.columns:
            if '_power' in col and col != 'total_power':
                device_name = col.replace('_power', '')
                power = float(latest_row[col])
                status = 'on' if power > 0 else 'off'
                device_status.append({
                    'name': device_name,
                    'status': status,
                    'power': power
                })

        return jsonify(device_status)
    except Exception as e:
        print(f"获取设备状态时出错: {str(e)}")
        return jsonify([])

@dashboard_bp.route('/api/energy-recommendations')
def energy_recommendations():
    """获取节能建议"""
    try:
        df = read_energy_data()
        recommendations = []

        # 计算每个设备的平均功率和使用时间
        device_power_cols = [col for col in df.columns if '_power' in col and col != 'total_power']
        device_avg_power = df[device_power_cols].mean()
        device_usage_time = df[device_power_cols].apply(lambda x: (x > 0).sum() * 5 / 60)  # 转换为小时

        # 分析每个设备
        for device, avg_power in device_avg_power.items():
            device_name = device.replace('_power', '')
            usage_hours = device_usage_time[device]
            
            # 检查高耗能设备
            if avg_power > 300:
                recommendations.append(
                    f"{device_name} 平均功率为 {avg_power:.1f}W，使用时间 {usage_hours:.1f}小时/天，"
                    f"建议减少使用时长或更换能效更高的设备。"
                )
            
            # 检查长时间运行的设备
            if usage_hours > 12 and device_name not in ['冰箱', '路由器']:
                recommendations.append(
                    f"{device_name} 每天运行时间超过12小时，建议检查是否忘记关闭。"
                )

        # 检查总用电量
        total_energy = df['total_energy'].sum()
        if total_energy > 20:  # 假设每天超过20度电为高耗能
            recommendations.append(
                f"今日总用电量 {total_energy:.1f}度，超过正常水平，建议检查是否有设备异常运行。"
            )

        if not recommendations:
            recommendations.append("您的用电模式良好，目前没有节能建议。")

        return jsonify(recommendations)
    except Exception as e:
        print(f"获取节能建议时出错: {str(e)}")
        return jsonify(["暂时无法获取节能建议，请稍后重试。"])

@dashboard_bp.route('/api/historical-data')
def historical_data():
    """获取历史数据"""
    try:
        df = read_energy_data()

        # 获取最近的100条记录
        recent_df = df.tail(100)

        records = []
        for _, row in recent_df.iterrows():
            record = {
                'date': row['timestamp'].split()[0],
                'time': row['timestamp'].split()[1],
                'power': float(row['total_power']),
                'energy': float(row['total_energy'])
            }
            records.append(record)

        return jsonify(records)
    except Exception as e:
        print(f"获取历史数据时出错: {str(e)}")
        return jsonify([])

def calculate_efficiency_score(device_data):
    """计算设备能效评分"""
    if device_data.empty:
        return 0
    
    # 计算基础指标
    avg_power = device_data['power'].mean()
    max_power = device_data['power'].max()
    power_variance = device_data['power'].var()
    
    # 获取设备配置
    device_config = DEVICE_CONFIGS.get(device_data['device'].iloc[0], {})
    if not device_config:
        return 0
    
    # 计算能效得分（0-100分）
    base_score = 100
    
    # 功率使用效率（40分）
    power_efficiency = 40 * (1 - (avg_power - device_config['min_power']) / 
                           (device_config['max_power'] - device_config['min_power']))
    
    # 功率稳定性（30分）
    stability_score = 30 * (1 - min(power_variance / (device_config['max_power'] ** 2), 1))
    
    # 峰值控制（30分）
    peak_score = 30 * (1 - (max_power - device_config['base_power']) / 
                      (device_config['max_power'] - device_config['base_power']))
    
    total_score = power_efficiency + stability_score + peak_score
    return max(0, min(100, total_score))

def analyze_device_patterns(device_data):
    """分析设备使用模式"""
    if device_data.empty:
        return []
    
    patterns = []
    device_name = device_data['device'].iloc[0]
    
    # 计算每小时平均功率
    hourly_power = device_data.groupby(device_data['timestamp'].dt.hour)['power'].mean()
    
    # 识别峰值时段
    peak_hours = hourly_power[hourly_power > hourly_power.mean() + hourly_power.std()].index.tolist()
    if peak_hours:
        patterns.append(f"{device_name}在{peak_hours}时达到用电高峰")
    
    # 分析使用时长
    active_hours = len(hourly_power[hourly_power > 0])
    if active_hours > 12:
        patterns.append(f"{device_name}使用时间较长，建议适当控制使用时长")
    
    return patterns

def detect_anomalies(device_data):
    """检测异常用电"""
    if device_data.empty:
        return []
    
    anomalies = []
    device_name = device_data['device'].iloc[0]
    
    # 计算移动平均和标准差
    window_size = 5
    device_data['power_ma'] = device_data['power'].rolling(window=window_size).mean()
    device_data['power_std'] = device_data['power'].rolling(window=window_size).std()
    
    # 检测异常值（超过3个标准差）
    anomalies_mask = abs(device_data['power'] - device_data['power_ma']) > 3 * device_data['power_std']
    anomaly_times = device_data[anomalies_mask]['timestamp'].tolist()
    
    if anomaly_times:
        anomalies.append({
            'device': device_name,
            'times': anomaly_times,
            'message': f"{device_name}在{len(anomaly_times)}个时间点出现异常用电"
        })
    
    return anomalies

def generate_recommendations(device_data, efficiency_score, patterns, anomalies):
    """生成节能建议"""
    recommendations = []
    device_name = device_data['device'].iloc[0]
    
    # 基于能效评分的建议
    if efficiency_score < 60:
        recommendations.append(f"{device_name}能效评分较低（{efficiency_score:.1f}分），建议检查设备状态")
    
    # 基于使用模式的建议
    for pattern in patterns:
        if "用电高峰" in pattern:
            recommendations.append(f"建议错峰使用{device_name}")
        if "使用时间较长" in pattern:
            recommendations.append(f"建议减少{device_name}的使用时长")
    
    # 基于异常检测的建议
    for anomaly in anomalies:
        if anomaly['device'] == device_name:
            recommendations.append(f"检测到{device_name}异常用电，建议检查设备是否正常工作")
    
    return recommendations

@dashboard_bp.route('/api/device-analysis')
def device_analysis():
    """获取设备分析数据"""
    try:
        # 读取最近30天的数据
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        df = pd.read_csv('data/energy_data.csv')
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df[(df['timestamp'] >= start_date) & (df['timestamp'] <= end_date)]
        
        analysis_results = {}
        for device in DEVICE_CONFIGS.keys():
            device_data = df[df['device'] == device]
            
            # 计算能效评分
            efficiency_score = calculate_efficiency_score(device_data)
            
            # 分析使用模式
            patterns = analyze_device_patterns(device_data)
            
            # 检测异常
            anomalies = detect_anomalies(device_data)
            
            # 生成建议
            recommendations = generate_recommendations(
                device_data, efficiency_score, patterns, anomalies
            )
            
            analysis_results[device] = {
                'efficiency_score': efficiency_score,
                'patterns': patterns,
                'anomalies': anomalies,
                'recommendations': recommendations
            }
        
        return jsonify({
            'success': True,
            'data': analysis_results
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'分析数据时出错：{str(e)}'
        })