#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import asyncio
import sys
import datetime
from typing import List, Tuple, Dict


def is_cloud_ip(ip_result):
    """判断是否为云IP"""
    cloud_keywords = [
        "腾讯云", "阿里云", "Amazon", "AWS", "Azure", "Google Cloud",
        "华为云", "百度云", "ucloud", "青云", "Cloud", "云"
    ]

    for keyword in cloud_keywords:
        if keyword.lower() in ip_result.lower():
            return True
    return False


def log_nali_message(ip, result, error=None):
    """记录nali命令执行的原始日志"""
    log_dir = "./log"
    log_file = os.path.join(log_dir, "nali.log")

    # 确保日志目录存在
    os.makedirs(log_dir, exist_ok=True)

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(log_file, 'a', encoding='utf-8') as lf:
        if error:
            lf.write(f"nali-[{timestamp}] IP: {ip}, 错误: {error}\n")
        else:
            lf.write(f"nali-[{timestamp}] IP: {ip}, 结果: {result}\n")


async def query_ip_info(ip_clean: str, semaphore: asyncio.Semaphore) -> Tuple[str, str, bool]:
    """
    异步查询单个IP信息

    参数:
    ip_clean: 清理后的IP地址
    semaphore: 信号量用于限制并发数

    返回:
    tuple: (ip_clean, result, is_success)
    """
    async with semaphore:
        try:
            # 使用 asyncio.create_subprocess_exec 创建子进程
            process = await asyncio.create_subprocess_exec(
                'nali', ip_clean,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # 等待进程完成并获取输出
            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                ip_result = stdout.decode('utf-8').strip()
                log_nali_message(ip_clean, ip_result)
                return ip_clean, ip_result, True
            else:
                error_msg = stderr.decode('utf-8').strip()
                log_nali_message(ip_clean, None, f"nali-命令执行失败: {error_msg}")
                return ip_clean, None, False

        except FileNotFoundError:
            error_msg = "未找到 'nali' 命令，请确保已安装 nali"
            log_nali_message(ip_clean, None, error_msg)
            raise FileNotFoundError(error_msg)
        except Exception as e:
            error_msg = f"nali-未知错误: {e}"
            log_nali_message(ip_clean, None, error_msg)
            return ip_clean, None, False


async def classify_ips(ip_list: List[str], max_concurrent: int = 10) -> Tuple[List[str], List[str]]:
    """
    异步分类IP列表为云IP和非云IP

    参数:
    ip_list: IP地址列表
    max_concurrent: 最大并发数，默认10

    返回:
    tuple: (cloud_ips, non_cloud_ips) - 云IP列表和非云IP列表
    """
    cloud_ips = []
    non_cloud_ips = []

    print("开始异步处理IP地址分类...")
    print(f"nali-最大并发数: {max_concurrent}")

    # 使用信号量限制并发数
    semaphore = asyncio.Semaphore(max_concurrent)

    # 准备任务列表
    tasks = []
    valid_ips = []

    # 预处理IP列表，提取有效IP
    for i, ip_line in enumerate(ip_list, 1):
        ip_line = ip_line.strip()

        # 跳过空行
        if not ip_line:
            continue

        # 提取IP地址
        ip_match = re.search(r'(\d+\.\d+\.\d+\.\d+)', ip_line)
        if not ip_match:
            print(f"nali-第{i}行: 未找到有效IP地址 - {ip_line}")
            continue

        ip_clean = ip_match.group(1)
        valid_ips.append((i, ip_clean))

    print(f"nali-有效IP数量: {len(valid_ips)}")

    # 创建所有查询任务
    for line_num, ip_clean in valid_ips:
        task = query_ip_info(ip_clean, semaphore)
        tasks.append((line_num, ip_clean, task))

    # 等待所有任务完成
    completed = 0
    total = len(tasks)

    for line_num, ip_clean, task in tasks:
        try:
            ip_clean, result, is_success = await task

            if is_success and result:
                if is_cloud_ip(result):
                    cloud_ips.append(ip_clean)
                    print(f"nali-第{line_num}行: {ip_clean} -> 云IP")
                else:
                    non_cloud_ips.append(ip_clean)
                    print(f"nali-第{line_num}行: {ip_clean} -> 非云IP")
            else:
                # 查询失败，默认归为非云IP
                non_cloud_ips.append(ip_clean)
                print(f"nali-第{line_num}行: {ip_clean} -> 查询失败，归为非云IP")

        except Exception as e:
            # 处理异常情况
            non_cloud_ips.append(ip_clean)
            print(f"nali-第{line_num}行: {ip_clean} -> 处理错误，归为非云IP: {e}")

        completed += 1
        if completed % 10 == 0 or completed == total:
            print(f"nali-进度: {completed}/{total} ({completed / total * 100:.1f}%)")

    print(f"nali-处理完成! 云IP: {len(cloud_ips)}个, 非云IP: {len(non_cloud_ips)}个")
    return cloud_ips, non_cloud_ips


async def classify_ips_from_file(file_path: str, max_concurrent: int = 10) -> Tuple[List[str], List[str]]:
    """
    从文件读取IP并异步分类

    参数:
    file_path: 包含IP地址的文件路径
    max_concurrent: 最大并发数

    返回:
    tuple: (cloud_ips, non_cloud_ips) - 云IP列表和非云IP列表
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"nali-文件 '{file_path}' 不存在!")

    with open(file_path, 'r', encoding='utf-8') as f:
        ip_list = f.readlines()

    return await classify_ips(ip_list, max_concurrent)


def save_results(cloud_ips, non_cloud_ips, cloud_file="yip.txt", non_cloud_file="zip.txt"):
    """
    保存分类结果到文件

    参数:
    cloud_ips: 云IP列表
    non_cloud_ips: 非云IP列表
    cloud_file: 云IP输出文件名
    non_cloud_file: 非云IP输出文件名
    """
    # 保存云IP
    with open(cloud_file, 'w', encoding='utf-8') as cf:
        for ip in cloud_ips:
            cf.write(f"nali-{ip}\n")

    # 保存非云IP
    with open(non_cloud_file, 'w', encoding='utf-8') as ncf:
        for ip in non_cloud_ips:
            ncf.write(f"nali-{ip}\n")

    print(f"nali-云IP已保存至: {cloud_file}")
    print(f"nali-非云IP已保存至: {non_cloud_file}")


# 同步调用接口
def run(ip_list: List[str], max_concurrent: int = 10) -> Tuple[List[str], List[str]]:
    """
    保持向后兼容的同步接口

    参数:
    ip_list: IP地址列表
    max_concurrent: 最大并发数，默认10

    返回:
    tuple: (cloud_ips, non_cloud_ips) - 云IP列表和非云IP列表
    """
    return asyncio.run(classify_ips(ip_list, max_concurrent))


# 同步文件处理接口
def run_from_file(file_path: str, max_concurrent: int = 10) -> Tuple[List[str], List[str]]:
    """
    从文件读取IP并同步分类（保持向后兼容）

    参数:
    file_path: 包含IP地址的文件路径
    max_concurrent: 最大并发数

    返回:
    tuple: (cloud_ips, non_cloud_ips) - 云IP列表和非云IP列表
    """
    return asyncio.run(classify_ips_from_file(file_path, max_concurrent))


async def main():
    """异步主函数"""
    # 获取输入文件
    input_file = input("请输入要读取的文件路径: ").strip()

    # 获取并发数
    try:
        max_concurrent = int(input("请输入最大并发数 (默认10): ").strip() or "10")
    except ValueError:
        max_concurrent = 10

    try:
        # 使用异步函数分类IP
        start_time = datetime.datetime.now()
        cloud_ips, non_cloud_ips = await classify_ips_from_file(input_file, max_concurrent)
        end_time = datetime.datetime.now()

        # 保存结果
        save_results(cloud_ips, non_cloud_ips)

        # 显示统计信息
        duration = end_time - start_time
        print("\n" + "=" * 50)
        print(f"nali-异步处理完成!")
        print(f"nali-处理耗时: {duration}")
        print(f"nali-云IP数量: {len(cloud_ips)}")
        print(f"nali-非云IP数量: {len(non_cloud_ips)}")
        print(f"nali-总计: {len(cloud_ips) + len(non_cloud_ips)}")

        # 显示预览
        if cloud_ips:
            print(f"nali-\n云IP列表预览 (前10个):")
            for ip in cloud_ips[:10]:
                print(f"nali-  {ip}")

        if non_cloud_ips:
            print(f"nali-\n非云IP列表预览 (前10个):")
            for ip in non_cloud_ips[:10]:
                print(f"nali-  {ip}")

    except FileNotFoundError as e:
        print(f"nali-错误: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"nali-处理过程中发生错误: {e}")
        sys.exit(1)


# 使用示例
async def example_usage():
    """异步使用示例"""
    # 示例1: 直接使用IP列表
    example_ips = [
        "8.8.8.8",
        "114.114.114.114",
        "1.1.1.1",
        "202.96.128.86"
    ]

    print("示例1: 直接使用IP列表")
    cloud, non_cloud = await classify_ips(example_ips, max_concurrent=5)
    print(f"nali-云IP: {cloud}")
    print(f"nali-非云IP: {non_cloud}")
    print()


if __name__ == "__main__":
    # 运行异步主函数
    asyncio.run(main())

    # 或者运行示例
    # asyncio.run(example_usage())

    # 同步调用示例（保持向后兼容）
    # example_ips = ["8.8.8.8", "114.114.114.114"]
    # cloud_ips, non_cloud_ips = run(example_ips)
    # print(f"nali-云IP: {cloud_ips}")
    # print(f"nali-非云IP: {non_cloud_ips}")