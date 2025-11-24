import asyncio
import subprocess
import sys
import os
import logging
from datetime import datetime


def setup_logging():
    """
    设置日志记录
    """
    # 创建log目录（如果不存在）
    log_dir = './log'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # 配置日志
    log_file = os.path.join(log_dir, 'whatweb.log')

    # 创建logger
    logger = logging.getLogger('whatweb_scanner')
    logger.setLevel(logging.INFO)

    # 避免重复添加handler
    if not logger.handlers:
        # 创建文件handler，使用追加模式
        file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
        file_handler.setLevel(logging.INFO)

        # 创建控制台handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # 创建formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # 添加handler到logger
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger


# 初始化日志
logger = setup_logging()


async def whatweb_scan(target):
    """
    异步执行 whatweb 扫描
    :param target: 目标URL或IP
    :return: 扫描结果字典
    """
    try:
        # 记录开始扫描
        logger.info(f"开始扫描目标: {target}")

        # 使用 asyncio.create_subprocess_exec 异步执行 whatweb 命令
        process = await asyncio.create_subprocess_exec(
            'whatweb',
            '--no-error',
            '--color=never',
            '--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36 Edg/139.0.0.0',
            target,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        # 等待进程完成并获取输出
        stdout, stderr = await process.communicate()

        # 解码输出，忽略编码错误
        stdout_text = stdout.decode('utf-8', errors='ignore')
        stderr_text = stderr.decode('utf-8', errors='ignore')

        # 记录扫描结果到日志
        logger.info(f"扫描完成: {target} - 返回码: {process.returncode}")
        logger.info(f"目标 {target} 的输出:\n{stdout_text}")
        if stderr_text:
            logger.warning(f"目标 {target} 的错误输出:\n{stderr_text}")

        # 返回结果
        return {
            'target': target,
            'stdout': stdout_text,
            'stderr': stderr_text,
            'returncode': process.returncode
        }

    except Exception as e:
        error_msg = f"扫描目标 {target} 时出错: {str(e)}"
        logger.error(error_msg)
        return {'target': target, 'error': str(e)}

async def get_ips_from_subdomains_async(subdomains):
    """
    异步扫描子域名列表
    :param subdomains: 子域名列表
    :return: 扫描结果列表
    """
    # 记录开始批量扫描
    logger.info(f"开始批量扫描，目标数量: {len(subdomains)}")
    logger.info(f"目标列表: {subdomains}")

    # 创建所有扫描任务
    tasks = [whatweb_scan(target) for target in subdomains]

    # 并发执行所有任务
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 处理结果
    final_results = []
    for result in results:
        if isinstance(result, Exception):
            error_msg = f"任务执行出错: {result}"
            logger.error(error_msg)
            print(f"任务执行出错: {result}")
            continue

        final_results.append(result)
        # print(f"\n扫描结果: {result['target']}")

        if 'error' in result:
            print(f"错误: {result['error']}")
        else:
            # print(f"返回码: {result['returncode']}")
            # print(f"输出:\n{result['stdout']}")
            if result['stderr']:
                print(f"错误输出:\n{result['stderr']}")

    # 记录批量扫描完成
    logger.info(f"批量扫描完成，成功处理: {len(final_results)} 个目标")

    return final_results


def parse_status_from_output(stdout):
    """
    从whatweb输出中解析状态码
    :param stdout: whatweb输出文本
    :return: 状态码数字字符串
    """
    import re
    match = re.search(r'\[(\d{3})\s+', stdout)
    return match.group(1) if match else "Unknown"


async def main(subdomains):
    """
    主函数
    :param subdomains: 目标URL列表
    :return: 格式为 [{url: status}] 的结果列表
    """
    # 记录程序开始
    logger.info("=" * 50)
    logger.info("WhatWeb 扫描程序启动")
    logger.info(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 执行异步扫描
    results = await get_ips_from_subdomains_async(subdomains)

    # 转换为要求的格式 [{url: status}]
    formatted_results = []
    for result in results:
        if 'error' in result:
            status = f"Error: {result['error']}"
        else:
            # 从stdout中解析状态码
            status = parse_status_from_output(result['stdout'])

        formatted_results.append({result['target']: status})

    # 记录程序结束
    logger.info(f"WhatWeb 扫描程序完成，共处理 {len(formatted_results)} 个目标")
    logger.info(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 50)

    return formatted_results


def run(targets):
    """
    运行whatweb扫描的主函数
    :param targets: 目标URL列表，例如 ['127.0.0.1:81', '127.0.0.1:82']
    :return: 格式为 [{url: status}] 的结果列表
    """
    return asyncio.run(main(targets))


# 使用示例
if __name__ == "__main__":
    # 定义要扫描的目标列表
    subdomains = ['127.0.0.1:81', '127.0.0.1:82']

    # 使用run函数执行扫描
    results = run(subdomains)

    # 打印格式化结果
    # print("\n格式化结果:")
    for item in results:
        for url, status in item.items():
            print(f"{url}  {status}")

    print(f"\n扫描完成，共处理 {len(results)} 个目标")
    # print(f"详细日志已保存到: ./log/whatweb.log")
