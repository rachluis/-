import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta

# 定义设备列表
devices = [
    {'name': '空调', 'min_power': 1000, 'max_power': 2000, 'on_time': 0.3},
    {'name': '冰箱', 'min_power': 100, 'max_power': 200, 'on_time': 0.7},
    {'name': '电视', 'min_power': 50, 'max_power': 150, 'on_time': 0.2},
    {'name': '洗衣机', 'min_power': 500, 'max_power': 1000, 'on_time': 0.1},
    {'name': '电热水器', 'min_power': 1500, 'max_power': 2000, 'on_time': 0.05},
    {'name': '电饭煲', 'min_power': 700, 'max_power': 1000, 'on_time': 0.05},
    {'name': '微波炉', 'min_power': 800, 'max_power': 1200, 'on_time': 0.1},
    {'name': '电脑', 'min_power': 100, 'max_power': 200, 'on_time': 0.4},
    {'name': '手机充电器', 'min_power': 10, 'max_power': 20, 'on_time': 0.8},
    {'name': '灯', 'min_power': 20, 'max_power': 100, 'on_time': 0.6}
]


# 生成模拟数据
def generate_simulated_data(num_days=30, interval_minutes=5):
    start_time = datetime.now() - timedelta(days=num_days)
    end_time = datetime.now()
    time_delta = timedelta(minutes=interval_minutes)

    timestamps = []
    current_time = start_time

    while current_time <= end_time:
        timestamps.append(current_time)
        current_time += time_delta

    data = {'timestamp': timestamps}

    for device in devices:
        device_on = [random.random() < device['on_time'] for _ in timestamps]
        device_power = [
            random.uniform(device['min_power'], device['max_power']) if on else 0
            for on in device_on
        ]
        device_energy = [
            power * interval_minutes / 60 / 1000
            for power in device_power
        ]

        data[f"{device['name']}_power"] = device_power
        data[f"{device['name']}_energy"] = device_energy

    df = pd.DataFrame(data)
    df['total_power'] = df[[f"{d['name']}_power" for d in devices]].sum(axis=1)
    df['total_energy'] = df[[f"{d['name']}_energy" for d in devices]].sum(axis=1)

    return df


# 保存到CSV文件
def save_to_csv(df, filename='data/energy_data.csv'):
    df.to_csv(filename, index=False)
    print(f"模拟数据已保存到 {filename}")


if __name__ == "__main__":
    df = generate_simulated_data()
    save_to_csv(df)