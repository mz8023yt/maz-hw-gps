import os
import argparse
import numpy as np
import csv
from geopy.distance import geodesic
import matplotlib.pyplot as plt
import pynmea2
import re

# 检查是否是有效的 NMEA 格式行
def is_valid_nmea(line):
    # 去除可能的乱码字符，确保是有效的 NMEA 报文
    line = line.strip()  # 去除空白字符
    line = re.sub(r'[^\x00-\x7F]+', '', line)  # 去除非ASCII字符
    # 以 $ 开头并且包含正确格式的消息
    return bool(re.match(r'^\$[A-Z]{5},', line))

# 解析 GNGLL 格式数据
def parse_gngll(line):
    try:
        msg = pynmea2.parse(line)
        if msg.status == 'A':  # 只有有效定位才处理
            lat = msg.latitude
            lon = msg.longitude
            return lat, lon
    except pynmea2.nmea.ChecksumError:
        pass  # 跳过校验错误的消息
    return None, None

# 解析 GPGGA 格式数据
def parse_gpgga(line):
    try:
        msg = pynmea2.parse(line)
        lat = msg.latitude
        lon = msg.longitude
        return lat, lon
    except pynmea2.nmea.ChecksumError:
        pass  # 跳过校验错误的消息
    return None, None

# 解析 GPRMC 格式数据
def parse_gprmc(line):
    try:
        msg = pynmea2.parse(line)
        if msg.status == 'A':  # 只有有效定位才处理
            lat = msg.latitude
            lon = msg.longitude
            return lat, lon
    except pynmea2.nmea.ChecksumError:
        pass  # 跳过校验错误的消息
    return None, None

# 解析 GNRMC 格式数据
def parse_gnrmc(line):
    try:
        msg = pynmea2.parse(line)
        if msg.status == 'A':  # 只有有效定位才处理
            lat = msg.latitude
            lon = msg.longitude
            return lat, lon
    except pynmea2.nmea.ChecksumError:
        pass  # 跳过校验错误的消息
    return None, None

# 加载并解析 GPS 数据文件
def load_gps_data(filename):
    latitudes = []
    longitudes = []
    
    # 解析相对路径
    file_path = os.path.abspath(filename)
    
    if not os.path.exists(file_path):
        print(f"错误：文件 {file_path} 不存在!")
        return [], []
    
    # 打开文件时忽略无法解码的字符
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
        for line in file:
            # 如果行是乱码，跳过
            if not is_valid_nmea(line):
                continue
            
            # 解析不同格式的报文
            if line.startswith('$GNGLL'):
                lat, lon = parse_gngll(line)
            elif line.startswith('$GPGGA'):
                lat, lon = parse_gpgga(line)
            elif line.startswith('$GPRMC'):
                lat, lon = parse_gprmc(line)
            elif line.startswith('$GNRMC'):  # 支持 GNRMC
                lat, lon = parse_gnrmc(line)
            else:
                continue  # 跳过其他格式消息
            
            if lat is not None and lon is not None:
                latitudes.append(lat)
                longitudes.append(lon)
    
    return latitudes, longitudes

# 计算 RMS 均方根误差
def calculate_rms(latitudes, longitudes):
    if not latitudes or not longitudes:
        print("错误：没有有效的 GPS 数据，无法计算 RMS!")
        return np.nan

    # 计算经纬度的平均值
    mean_lat = np.mean(latitudes)
    mean_lon = np.mean(longitudes)
    
    # 计算每个点与平均位置的距离
    errors = []
    for lat, lon in zip(latitudes, longitudes):
        errors.append(geodesic((mean_lat, mean_lon), (lat, lon)).meters)
    
    # 计算 RMS
    rms = np.sqrt(np.mean(np.square(errors)))
    return rms

# 计算百分位误差
def calculate_percentiles(errors, percentiles=[68, 95]):
    if not errors:
        print("错误：没有有效的误差数据，无法计算百分位!")
        return []
    return np.percentile(errors, percentiles)

# 保存经纬度到新文件
def save_coordinates(latitudes, longitudes, filename):
    with open(filename, 'w', newline='') as file:
        writer = csv.writer(file)
        for lat, lon in zip(latitudes, longitudes):
            writer.writerow([lat, lon])

# 绘制误差分布图
def plot_errors(errors, filename):
    if errors:
        plt.hist(errors, bins=50, edgecolor='black')
        plt.title(filename)
        plt.xlabel('Error (meters)')
        plt.ylabel('Frequency')
        plt.show()
    else:
        print("错误：没有足够的误差数据进行绘图!")

# 主程序
def main():
    # 使用 argparse 解析命令行参数
    parser = argparse.ArgumentParser(description="解析 GPS 文件并计算定位精度")
    parser.add_argument('file', type=str, help="输入的 GPS 数据文件路径")
    args = parser.parse_args()

    # 载入GPS数据文件
    latitudes, longitudes = load_gps_data(args.file)
    if not latitudes or not longitudes:
        print("错误：没有解析到有效的 GPS 数据。")
        return
    
    # 计算 RMS
    rms = calculate_rms(latitudes, longitudes)
    if not np.isnan(rms):
        print(f'RMS: {rms:.2f} meters')
    else:
        print("RMS 计算失败。")
    
    # 计算 68% 和 95% 百分位误差
    errors = [geodesic((np.mean(latitudes), np.mean(longitudes)), (lat, lon)).meters
              for lat, lon in zip(latitudes, longitudes)]
    percentiles = calculate_percentiles(errors)
    
    # 使用 np.any() 来检查 percentiles 是否为空
    if percentiles.size > 0:
        print(f'68% percentile error: {percentiles[0]:.2f} meters')
        print(f'95% percentile error: {percentiles[1]:.2f} meters')
    else:
        print("无法计算百分位误差。")

    # 提取输入文件名（不包含路径和扩展名）
    base_filename = os.path.splitext(os.path.basename(args.file))[0]
    output_filename = f'{base_filename}.csv'

    # 保存经纬度数据
    save_coordinates(latitudes, longitudes, output_filename)

    # 绘制误差分布
    plot_errors(errors, base_filename)

if __name__ == "__main__":
    main()
