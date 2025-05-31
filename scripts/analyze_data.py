import pandas as pd
import sqlite3
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import numpy as np
from sklearn.cluster import KMeans


class EnergyAnalyzer:
    def __init__(self, db_file='energy.db'):
        self.db_file = db_file
        self.conn = sqlite3.connect(db_file)
        self.device_id_map = self._get_device_id_map()
        self.device_name_map = {v: k for k, v in self.device_id_map.items()}

    def _get_device_id_map(self):
        # 获取设备ID到名称的映射
        query = "SELECT id, name FROM devices"
        df = pd.read_sql(query, self.conn)
        return dict(zip(df['id'], df['name']))

    def get_energy_usage(self, start_date=None, end_date=None):
        """获取指定时间段的用电数据"""
        query = "SELECT device_id, timestamp, power, energy FROM energy_records"
        params = []

        if start_date or end_date:
            where_clause = []
            if start_date:
                where_clause.append("timestamp >= ?")
                params.append(start_date)
            if end_date:
                where_clause.append("timestamp <= ?")
                params.append(end_date)

            query += " WHERE " + " AND ".join(where_clause)

        df = pd.read_sql(query, self.conn, params=params)
        df['device_name'] = df['device_id'].map(self.device_name_map)

        return df

    def get_daily_usage(self, device=None):
        """获取每日用电量"""
        query = """
            SELECT 
                device_id, 
                date(timestamp) as date,
                SUM(power) as total_power,
                SUM(energy) as total_energy
            FROM energy_records
            GROUP BY device_id, date
        """

        if device:
            device_id = next((k for k, v in self.device_id_map.items() if v == device), None)
            if not device_id:
                return pd.DataFrame()
            query += " WHERE device_id = ?"
            df = pd.read_sql(query, self.conn, params=[device_id])
            df['device_name'] = device
        else:
            df = pd.read_sql(query, self.conn)
            df['device_name'] = df['device_id'].map(self.device_name_map)

        return df

    def analyze_high_consumption_devices(self):
        """分析高耗能设备"""
        daily_usage = self.get_daily_usage()

        # 计算每个设备的平均功率和总电量
        device_stats = daily_usage.groupby('device_name').agg(
            avg_power=('total_power', 'mean'),
            total_energy=('total_energy', 'sum')
        ).reset_index()

        # 高耗能设备阈值（平均功率超过300W）
        high_consumption = device_stats[device_stats['avg_power'] > 300]

        # 存储高耗能设备
        self._store_high_consumption_devices(high_consumption)

        return high_consumption

    def detect_anomalous_usage(self):
        """检测异常用电模式"""
        # 获取所有用电记录
        records = self.get_energy_usage()

        # 对每个设备进行异常检测
        anomalies = []

        for device_id, group in records.groupby('device_id'):
            device_name = self.device_id_map[device_id]

            # 移除异常值（这里使用IQR方法）
            q1 = group['power'].quantile(0.25)
            q3 = group['power'].quantile(0.75)
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr

            # 标记异常值
            group['is_anomaly'] = (group['power'] < lower_bound) | (group['power'] > upper_bound)

            # 提取异常记录
            device_anomalies = group[group['is_anomaly']].copy()
            device_anomalies['device_name'] = device_name

            anomalies.append(device_anomalies)

        # 合并所有设备的异常记录
        anomalies_df = pd.concat(anomalies)

        return anomalies_df

    def generate_energy_recommendations(self):
        """生成节能建议"""
        recommendations = []

        # 获取高耗能设备
        high_consumption = self.analyze_high_consumption_devices()
        for _, row in high_consumption.iterrows():
            recommendations.append(
                f"{row['device_name']} 平均功率为 {row['avg_power']:.1f}W，属于高耗能设备，建议减少使用时长或更换能效更高的设备。")

        # 获取异常用电记录
        anomalies = self.detect_anomalous_usage()
        for device_name, group in anomalies.groupby('device_name'):
            # 只关注功率过高的异常
            high_anomalies = group[group['power'] > group['power'].mean() + 2 * group['power'].std()]
            if not high_anomalies.empty:
                avg_anomaly_power = high_anomalies['power'].mean()
                recommendations.append(
                    f"{device_name} 存在异常高功率使用情况（平均{avg_anomaly_power:.1f}W），建议检查设备是否正常运行。")

        # 生成一般性建议
        if not recommendations:
            recommendations.append("您的用电模式良好，目前没有节能建议。")
        else:
            recommendations.append("建议定期检查设备运行状态，确保设备正常运行。")
            recommendations.append("考虑在非高峰时段使用大功率设备，可以降低用电成本。")

        return recommendations

    def _store_high_consumption_devices(self, high_consumption):
        """存储高耗能设备信息"""
        cursor = self.conn.cursor()

        # 清除现有记录
        cursor.execute("DELETE FROM high_consumption_devices")

        # 插入新记录
        for _, row in high_consumption.iterrows():
            cursor.execute('''
                INSERT INTO high_consumption_devices (device, avg_power)
                VALUES (?, ?)
            ''', (row['device_name'], row['avg_power']))

        self.conn.commit()

    def plot_energy_usage(self, device=None, start_date=None, end_date=None):
        """绘制用电使用图表"""
        # 获取指定时间段的数据
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)

        records = self.get_energy_usage(
            start_date.strftime('%Y-%m-%d %H:%M:%S') if start_date else None,
            end_date.strftime('%Y-%m-%d %H:%M:%S') if end_date else None
        )

        if device:
            records = records[records['device_name'] == device]

        # 绘制功率随时间变化的图表
        plt.figure(figsize=(12, 6))
        plt.plot(records['timestamp'], records['power'], marker='.', linestyle='-')
        plt.title(f"{'设备' if device else '总体'}功率变化")
        plt.xlabel("时间")
        plt.ylabel("功率 (W)")
        plt.grid(True)
        plt.tight_layout()
        plt.xticks(rotation=45)
        plt.show()

    def cluster_usage_patterns(self, n_clusters=3):
        """聚类用电模式"""
        # 获取每日用电数据
        daily_usage = self.get_daily_usage()

        # 转换为设备-日期矩阵
        pivot = daily_usage.pivot(index='date', columns='device_name', values='total_power').fillna(0)

        # 使用K-Means聚类
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        cluster_labels = kmeans.fit_predict(pivot)

        # 添加聚类标签
        pivot['cluster'] = cluster_labels

        return pivot


# 主执行函数
if __name__ == "__main__":
    analyzer = EnergyAnalyzer()

    # 生成节能建议
    recommendations = analyzer.generate_energy_recommendations()
    print("节能建议:")
    for rec in recommendations:
        print(f"- {rec}")

    # 可视化用电模式
    print("\n绘图示例:")
    print("- 绘制空调功率变化图")
    analyzer.plot_energy_usage(device="空调")

    print("- 绘制所有设备功率变化图(最近7天)")
    start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    analyzer.plot_energy_usage(start_date=start_date)

    print("- 聚类用电模式(3个簇)")
    clusters = analyzer.cluster_usage_patterns(n_clusters=3)
    print("\n设备用电模式聚类结果:")
    print(clusters['cluster'].value_counts())