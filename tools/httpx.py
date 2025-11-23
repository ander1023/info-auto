import asyncio
import json
import subprocess
import os
import tempfile
from typing import List, Dict, Optional
from pathlib import Path


class HttpxScanner:
    def __init__(self):
        self.log_dir = Path("log")
        self.log_file = self.log_dir / "httpx.log"
        self.temp_dir = self.log_dir / "temp"
        self._ensure_log_dir()

    def _ensure_log_dir(self):
        """确保日志目录和临时目录存在"""
        self.log_dir.mkdir(exist_ok=True)
        self.temp_dir.mkdir(exist_ok=True)

    def _log_command_output(self, output: str):
        """将命令输出记录到日志文件"""
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(output + "\n")

    async def scan_urls_from_file(self, urls: List[str]) -> List[Dict]:
        """
        通过临时文件扫描URL列表

        Args:
            urls: URL列表

        Returns:
            包含扫描结果的字典列表
        """
        # 在log/temp目录下创建临时文件
        temp_file = self.temp_dir / "httpx_temp.txt"

        # 写入URL列表到临时文件
        with open(temp_file, 'w', encoding='utf-8') as f:
            for url in urls:
                f.write(url + '\n')

        try:
            return await self._scan_with_file_input(str(temp_file))
        finally:
            # 清理临时文件
            if temp_file.exists():
                temp_file.unlink()

    async def _scan_with_file_input(self, url_file: str) -> List[Dict]:
        """
        使用文件输入模式执行httpx扫描

        Args:
            url_file: 包含URL列表的文件路径

        Returns:
            包含扫描结果的字典列表
        """
        # 构建httpx命令 - 使用你手动测试成功的命令格式
        cmd = [
            "httpxx",  # 使用你系统中正确的命令名称
            "-l", url_file,  # 使用文件输入
            "-sc",  # 状态码
            "-title",  # 页面标题
            "-server",  # 服务器信息
            "-td",  # 技术检测
            "-fr",  # 跟随重定向
            "-nc",  # 不显示颜色
            "-silent"  # 静默模式，减少额外输出
        ]

        # 记录原始命令
        self._log_command_output(f"Executing command: {' '.join(cmd)}")

        # 统计URL数量
        with open(url_file, 'r', encoding='utf-8') as f:
            url_count = sum(1 for line in f)
        self._log_command_output(f"Input file: {url_file} with {url_count} URLs")

        try:
            # 执行命令 - 使用shell=True来正确处理带引号的参数
            process = await asyncio.create_subprocess_shell(
                ' '.join(cmd),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                shell=True
            )

            stdout, stderr = await process.communicate()

            # 记录原始输出
            output = stdout.decode('utf-8', errors='ignore').strip()
            error_output = stderr.decode('utf-8', errors='ignore').strip()

            if output:
                self._log_command_output(f"Output:\n{output}")
            if error_output:
                self._log_command_output(f"Error output:\n{error_output}")

            # 检查返回码
            if process.returncode != 0:
                self._log_command_output(f"Command failed with return code: {process.returncode}")

            # 解析输出
            if output:
                return self._parse_httpx_output(output)
            else:
                self._log_command_output("No output received from httpx")
                return []

        except Exception as e:
            error_msg = f"Command execution failed: {str(e)}"
            self._log_command_output(error_msg)
            return []

    def _parse_httpx_output(self, output: str) -> List[Dict]:
        """
        解析httpx命令输出

        Args:
            output: httpx命令输出

        Returns:
            解析后的结果列表
        """
        results = []
        lines = output.strip().split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 初始化结果字典
            result = {
                "url": "",
                "title": "",
                "status": 0,
                "technological": []
            }

            # 解析标准格式: https://www.python.org [200] [Welcome to Python.org] [] [EthicalAds,Google Hosted Libraries,HSTS,Modernizr,Varnish,jQuery UI:1.12.1,jQuery:1.8.2]
            parts = line.split(' ')

            # 第一个部分通常是URL
            if parts:
                result["url"] = parts[0]

            # 解析其他部分
            for part in parts[1:]:
                if part.startswith('[') and part.endswith(']'):
                    content = part[1:-1]

                    # 状态码 (数字)
                    if content.isdigit():
                        result["status"] = int(content)

                    # 标题 (第一个非数字且不包含逗号和斜杠的内容)
                    elif (len(content) > 2 and not ',' in content and not '/' in content
                          and not result["title"]):  # 只设置第一个符合条件的作为标题
                        result["title"] = content

                    # 技术栈 (包含逗号的内容)
                    elif ',' in content:
                        tech_list = [tech.strip() for tech in content.split(',')]
                        result["technological"] = tech_list

                    # 服务器信息 (包含斜杠的内容)
                    elif '/' in content:
                        if not result.get("server"):
                            result["server"] = content

                    # 其他内容都添加到技术栈
                    else:
                        result["technological"].append(content)

            results.append(result)

        return results


# 创建全局扫描器实例
_scanner = HttpxScanner()


async def xxx(urls: List[str]) -> List[Dict]:
    """
    异步扫描URL列表

    Args:
        urls: URL列表

    Returns:
        扫描结果列表
    """
    return await _scanner.scan_urls_from_file(urls)


def run(urls: List[str]) -> List[Dict]:
    """
    保持向后兼容的同步接口

    Args:
        urls: URL列表，例如 ["www.baidu.com", "www.google.com", "github.com"]

    Returns:
        扫描结果列表，每个元素包含 url, title, status, technological
    """
    # 创建临时文件路径
    temp_file = _scanner.temp_dir / "httpx.txt"

    # 确保临时目录存在
    _scanner._ensure_log_dir()

    # 将URL列表写入临时文件
    with open(temp_file, 'w', encoding='utf-8') as f:
        for url in urls:
            f.write(url + '\n')

    try:
        # 执行扫描
        results = asyncio.run(_scanner._scan_with_file_input(str(temp_file)))
        return results
    finally:
        # 扫描完成后自动删除临时文件
        if temp_file.exists():
            temp_file.unlink()


# 新增功能：直接从文件读取URL列表
def run_from_file(file_path: str) -> List[Dict]:
    """
    从文件读取URL列表并扫描

    Args:
        file_path: 包含URL列表的文件路径，每行一个URL

    Returns:
        扫描结果列表
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip()]

    return run(urls)


# 使用示例
if __name__ == "__main__":
    # 测试直接传递URL列表
    test_urls = ["192.168.100.131:81"]
    print("开始扫描URL列表...")
    results = run(test_urls)

    print(f"直接扫描完成，共处理 {len(results)} 个URL")
    for result in results:
        print(f"URL: {result['url']}")
        print(f"状态码: {result['status']}")
        print(f"标题: {result['title']}")
        print(f"技术栈: {result['technological']}")
        print("-" * 50)

    print(f"\n日志文件: {_scanner.log_file}")
    print(f"临时文件目录: {_scanner.temp_dir}")