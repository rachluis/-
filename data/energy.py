import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta

# 定义设备列表及其功率范围和使用概率
devices = [
    {'name': '空调', 'min_power': 1000, 'max_power': 2000, 'on_time': 0.3},
    {'name': '冰箱', 'min_power': 100, 'max_power': 200, 'on_time': 0.7},
    {'name': '电视', 'min_power': 50, 'max_power': 150, 'on_time': 0.4},
    {'name': '洗衣机', 'min_power': 500, 'max_power': 1000, 'on_time': 0.1},
    {'name': '电热水器', 'min_power': 1500, 'max_power': 2000, 'on_time': 0.2},
    {'name': '电饭煲', 'min_power': 700, 'max_power': 1000, 'on_time': 0.15},
    {'name': '微波炉', 'min_power': 800, 'max_power': 1200, 'on_time': 0.1},
    {'name': '电脑', 'min_power': 100, 'max_power': 200, 'on_time': 0.5},
    {'name': '手机充电器', 'min_power': 10, 'max_power': 20, 'on_time': 0.8},
    {'name': '灯', 'min_power': 20, 'max_power': 100, 'on_time': 0.6}
]

# 设置数据生成的时间范围（过去一个月）
end_time = datetime.now()
start_time = end_time - timedelta(days=30)

# 创建时间序列，每5分钟一个时间点
time_list = []
current_time = start_time

while current_time <= end_time:
    time_list.append(current_time)
    current_time += timedelta(minutes=5)

# 创建数据框
data = {'timestamp': [t.strftime('%Y-%m-%d %H:%M:%S') for t in time_list]}

# 为每个设备生成模拟数据
for device in devices:
    device_on = [random.random() < device['on_time'] for _ in time_list]
    device_power = [
        round(random.uniform(device['min_power'], device['max_power']), 2) if on else 0
        for on in device_on
    ]
    device_energy = [
        round(power * 5 / 60 / 1000, 4)  # 5分钟的能耗（kWh）
        for power in device_power
    ]

    data[f"{device['name']}_power"] = device_power
    data[f"{device['name']}_energy"] = device_energy

# 计算总功率和总能耗
data['total_power'] = [
    round(sum(row), 2) for row in zip(*[data[f"{d['name']}_power"] for d in devices])
]
data['total_energy'] = [
    round(sum(row), 4) for row in zip(*[data[f"{d['name']}_energy"] for d in devices])
]

# 创建DataFrame并保存为CSV
df = pd.DataFrame(data)
df.to_csv('data/energy_data.csv', index=False)

print(f"已生成包含 {len(time_list)} 条记录的 energy_data.csv 文件")