import asyncio
import subprocess
import os
import shutil
from typing import List
from datetime import datetime
import config


def run(targets: List[str]) -> List[str]:
    """保持向后兼容的同步接口
    执行naabu扫描并返回格式为IP:PORT的开放端口列表

    Args:
        targets: 目标IP地址列表

    Returns:
        格式为IP:PORT的开放端口列表
    """
    return asyncio.run(async_scan(targets))


async def async_scan(targets: List[str]) -> List[str]:
    """异步执行naabu扫描

    Args:
        targets: 目标IP地址列表

    Returns:
        格式为IP:PORT的开放端口列表
    """
    # 确保日志目录存在
    os.makedirs('log', exist_ok=True)

    # 检查naabu是否可用
    if not shutil.which("naabu"):
        error_msg = "错误: 系统中未找到naabu命令，请先安装naabu"
        print(error_msg)
        _append_log(f"错误: {error_msg}")
        return []

    # 构建目标字符串
    targets_str = ','.join(targets)

    # 构建naabu命令
    cmd = [
        'naabu',
        '-p', '1-65535',  # 扫描所有端口
        '-host', targets_str,
        '-rate', '4000',
        '-retries', '3',
        '-silent'
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
                _append_log("提示: 可能是naabu版本不兼容或参数错误")

        # 解析输出，提取开放端口 - naabu输出格式为 ip:port
        open_ports = parse_naabu_output(result.stdout)

        _append_log(f"发现的开放端口: {len(open_ports)}个")
        _append_log("=" * 60)

        return open_ports

    except FileNotFoundError:
        error_msg = "错误: 未找到naabu命令，请确保已安装naabu"
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
    with open('log/naabu.log', 'a', encoding='utf-8') as f:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        f.write(f"[{timestamp}] {content}\n")


def parse_naabu_output(output: str) -> List[str]:
    """解析naabu输出，提取开放端口信息

    Args:
        output: naabu命令输出

    Returns:
        格式为IP:PORT的开放端口列表
    """
    open_ports = []

    for line in output.split('\n'):
        line = line.strip()

        # naabu默认输出格式为: ip:port
        # 例如: 192.168.1.1:80
        # 也可能是: 192.168.1.1:80 (http)

        # 过滤空行和注释行
        if not line or line.startswith('#'):
            continue

        # 提取IP:PORT部分（可能后面有协议信息）
        if ':' in line:
            # 分割IP和端口
            parts = line.split(':')
            if len(parts) >= 2:
                ip = parts[0]
                port_part = parts[1]

                # 端口部分可能包含空格或协议信息，如 "80 (http)"
                port = port_part.split()[0].strip()

                # 验证端口是否为数字
                if port.isdigit():
                    # 构建IP:PORT格式
                    open_ports.append(f"{ip}:{port}")
                else:
                    # 尝试从括号中提取端口
                    if '(' in port_part and ')' in port_part:
                        port = port_part.split('(')[0].strip()
                        if port.isdigit():
                            open_ports.append(f"{ip}:{port}")

    # 去重并排序
    unique_ports = sorted(set(open_ports))
    return unique_ports


def debug_naabu_help():
    """调试函数：获取naabu帮助信息"""
    try:
        result = subprocess.run(['naabu', '-h'], capture_output=True, text=True)
        print("naabu帮助信息:")
        print(result.stdout[:500])  # 只显示前500字符
        if result.stderr:
            print("错误信息:", result.stderr)
    except Exception as e:
        print(f"获取帮助信息失败: {e}")


def test_naabu_scan():
    """测试naabu扫描功能"""
    # 测试目标
    test_targets = ["scanme.nmap.org", "example.com"]

    print(f"开始naabu扫描测试，目标: {test_targets}")

    # 构建测试命令
    cmd = [
        'naabu',
        '-p', '80,443',  # 只扫描常用端口
        '-host', ','.join(test_targets),
        '-silent'
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        print(f"\n返回码: {result.returncode}")
        print(f"输出:\n{result.stdout}")

        if result.stderr:
            print(f"错误:\n{result.stderr}")

        # 解析输出
        open_ports = parse_naabu_output(result.stdout)
        print(f"\n解析到的开放端口: {open_ports}")

    except subprocess.TimeoutExpired:
        print("扫描超时")
    except Exception as e:
        print(f"扫描失败: {e}")


# 测试代码
if __name__ == "__main__":
    # 调试naabu命令
    print("=" * 60)
    print("检查naabu命令...")
    debug_naabu_help()

    # 测试扫描功能
    print("\n" + "=" * 60)
    print("测试naabu扫描功能...")
    test_naabu_scan()

    # 测试主函数
    print("\n" + "=" * 60)
    print("测试主扫描函数...")

    # 使用测试目标
    test_targets = ["scanme.nmap.org", "example.com"]
    print(f"扫描目标: {test_targets}")

    results = run(test_targets)
    print(f"\n发现的开放端口 ({len(results)}个):")
    for result in results:
        print(f"  {result}")

    # 测试本地网络（可选）
    print("\n" + "=" * 60)
    print("测试本地网络扫描...")
    local_targets = ["127.0.0.1"]
    local_results = run(local_targets)
    print(f"本地开放端口: {local_results}")