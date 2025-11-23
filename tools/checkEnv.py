import shutil
import subprocess
import sys


def check_tool_installed(tool_name):
    """
    检查指定工具是否安装

    Args:
        tool_name (str): 工具名称

    Returns:
        bool: 如果工具已安装返回True，否则返回False
    """
    # 检查命令是否存在
    if shutil.which(tool_name) is None:
        print(f"❌ 调试信息: 未找到 {tool_name} 命令")
        return False

    try:
        # 尝试运行工具的帮助命令来验证是否正常工作
        if tool_name == "nali":
            result = subprocess.run([tool_name, "-h"],
                                    capture_output=True,
                                    text=True,
                                    timeout=10)
        elif tool_name == "masscan":
            result = subprocess.run([tool_name, "--help"],
                                    capture_output=True,
                                    text=True,
                                    timeout=10)
        else:
            result = subprocess.run([tool_name, "--version"],
                                    capture_output=True,
                                    text=True,
                                    timeout=10)

        if result.returncode == 0 or result.returncode == 1:  # 很多工具帮助命令返回1
            print(f"✅ 调试信息: {tool_name} 已安装并可正常使用")
            print(f"   命令路径: {shutil.which(tool_name)}")
            return True
        else:
            print(f"❌ 调试信息: {tool_name} 命令执行失败，返回码: {result.returncode}")
            return False

    except subprocess.TimeoutExpired:
        print(f"❌ 调试信息: {tool_name} 命令执行超时")
        return False
    except Exception as e:
        print(f"❌ 调试信息: 执行 {tool_name} 命令时发生错误: {str(e)}")
        return False


def check_all_tools():
    """
    检查所有需要的工具是否安装
    """
    tools = ["nali", "masscan"]
    results = {}

    print("开始检查工具安装情况...")
    print("-" * 50)

    for tool in tools:
        print(f"检查 {tool}...")
        results[tool] = check_tool_installed(tool)
        print()  # 空行

    print("-" * 50)
    print("检查结果汇总:")
    for tool, installed in results.items():
        status = "✅ 已安装" if installed else "❌ 未安装"
        print(f"  {tool}: {status}")

    return all(results.values())


def get_tool_version(tool_name):
    """
    获取工具的版本信息（额外功能）
    """
    try:
        if tool_name == "nali":
            result = subprocess.run([tool_name, "-v"],
                                    capture_output=True,
                                    text=True,
                                    timeout=5)
        elif tool_name == "masscan":
            result = subprocess.run([tool_name, "--version"],
                                    capture_output=True,
                                    text=True,
                                    timeout=5)

        if result.returncode == 0:
            return result.stdout.strip()
    except:
        pass
    return "无法获取版本信息"


if __name__ == "__main__":
    # 检查所有工具
    all_installed = check_all_tools()

    print(f"\n最终结果: {'所有工具都已安装 ✅' if all_installed else '有工具未安装 ❌'}")

    # 显示版本信息（如果已安装）
    print("\n版本信息:")
    for tool in ["nali", "masscan"]:
        if check_tool_installed(tool):
            version = get_tool_version(tool)
            print(f"  {tool}: {version}")