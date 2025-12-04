import asyncio
import subprocess
import os
import shutil
from typing import List
from datetime import datetime
import config

def run(targets: List[str]) -> List[str]:
    """保持向后兼容的同步接口
    执行masscan扫描并返回格式为IP:PORT的开放端口列表

    Args:
        targets: 目标IP地址列表

    Returns:
        格式为IP:PORT的开放端口列表
    """
    return asyncio.run(async_scan(targets))


async def async_scan(targets: List[str]) -> List[str]:
    """异步执行masscan扫描

    Args:
        targets: 目标IP地址列表

    Returns:
        格式为IP:PORT的开放端口列表
    """
    # 确保日志目录存在
    os.makedirs('log', exist_ok=True)

    # 检查masscan是否可用
    if not shutil.which("masscan"):
        error_msg = "错误: 系统中未找到masscan命令，请先安装masscan"
        print(error_msg)
        _append_log(f"错误: {error_msg}")
        return []

    # 构建目标字符串
    targets_str = ','.join(targets)

    # 构建命令 - 确保参数格式正确
    cmd = [
        'masscan',
         '-p1-65535',
        #'-p1-200',
        targets_str,
        '--rate',config.Config.masscan_rate,
        '--wait', '0'
    ]

    # 执行命令并捕获输出
    try:
        # 记录执行的命令
        cmd_str = ' '.join(cmd)
        _append_log(f"执行命令: {cmd_str}")

        # 同步执行命令
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: subprocess.run(cmd, capture_output=True, text=True, check=False)
        )

        # 追加保存原始日志
        _append_log(f"扫描目标: {targets_str}")
        _append_log("命令输出:")
        _append_log(result.stdout)

        if result.stderr:
            _append_log("错误输出:")
            _append_log(result.stderr)

        # 检查返回码
        if result.returncode != 0:
            _append_log(f"命令执行失败，返回码: {result.returncode}")
            if "unknown command-line parameter" in result.stderr:
                _append_log("提示: 可能是masscan版本不兼容或参数错误")

        # 解析输出，提取开放端口
        open_ports = parse_masscan_output(result.stdout)

        _append_log(f"发现的开放端口: {open_ports}")
        _append_log("=" * 60)

        return open_ports

    except FileNotFoundError:
        error_msg = "错误: 未找到masscan命令，请确保已安装masscan"
        print(error_msg)
        _append_log(f"错误: {error_msg}")
        return []
    except Exception as e:
        error_msg = f"命令执行异常: {str(e)}"
        print(error_msg)
        _append_log(f"错误: {error_msg}")
        return []


def _append_log(content: str):
    """追加日志到文件"""
    with open('log/masscan.log', 'a', encoding='utf-8') as f:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        f.write(f"[{timestamp}] {content}\n")


def parse_masscan_output(output: str) -> List[str]:
    """解析masscan输出，提取开放端口信息

    Args:
        output: masscan命令输出

    Returns:
        格式为IP:PORT的开放端口列表
    """
    open_ports = []

    for line in output.split('\n'):
        line = line.strip()
        if line.startswith('Discovered open port'):
            # 解析格式: "Discovered open port 22/tcp on 192.168.100.1"
            parts = line.split()
            if len(parts) >= 6:
                port_protocol = parts[3]  # 22/tcp
                ip = parts[5]  # 192.168.100.1

                # 提取端口号
                port = port_protocol.split('/')[0]

                # 构建IP:PORT格式
                open_ports.append(f"{ip}:{port}")

    return open_ports


def debug_masscan_help():
    """调试函数：获取masscan帮助信息"""
    try:
        result = subprocess.run(['masscan', '--help'], capture_output=True, text=True)
        print("masscan帮助信息:")
        print(result.stdout[:500])  # 只显示前500字符
        if result.stderr:
            print("错误信息:", result.stderr)
    except Exception as e:
        print(f"获取帮助信息失败: {e}")


# 测试代码
if __name__ == "__main__":
    # 调试masscan命令
    print("检查masscan命令...")
    debug_masscan_help()

    # 测试用例 - 使用更简单的参数
    print("\n开始扫描测试...")
    test_targets = ["192.168.100.131", "192.168.100.1"]
    results = run(test_targets)
    print("发现的开放端口:")
    for result in results:
        print(result)
