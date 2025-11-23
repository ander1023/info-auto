import asyncio
import os
from typing import List, Dict, Tuple


async def run_host_command(subdomain: str) -> str:
    """异步执行host命令"""
    process = await asyncio.create_subprocess_exec(
        'host', subdomain,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    stdout, stderr = await process.communicate()
    return stdout.decode().strip()


async def get_ips_from_subdomains_async(subdomains: List[str]) -> Tuple[List[Dict[str, str]], List[str]]:
    """
    异步执行但保持顺序的版本
    输出格式: [[{域名1:ip1}, {域名2:ip2}], [无alias ip1, 无alias ip2]]
    """
    os.makedirs('./log', exist_ok=True)

    host_output = []
    domain_ip_dicts = []  # 存储 {域名: IP} 字典的列表
    no_alias_ips = []  # 存储无alias的IP列表

    # 使用信号量控制并发数量为1，实现顺序执行
    semaphore = asyncio.Semaphore(1)

    async def process_subdomain(subdomain):
        async with semaphore:  # 确保同一时间只有一个任务执行
            try:
                print(f"host-Processing {subdomain}...")
                output = await run_host_command(subdomain)

                if output:
                    # 同步写入文件
                    with open('./log/host.log', 'a', encoding='utf-8') as f:
                        f.write(f"{output}\n")

                    host_output.append(output)

                    # 检查整个输出中是否包含"alias"
                    has_alias = 'alias' in output.lower()

                    # 解析所有包含"has address"的行
                    lines = output.split('\n')
                    for line in lines:
                        # 查找包含"has address"的行
                        if 'has address' in line.lower():
                            parts = line.split()
                            if len(parts) >= 4:
                                potential_ip = parts[-1]
                                if (potential_ip.count('.') == 3 and
                                        all(part.isdigit() for part in potential_ip.split('.'))):

                                    # 提取域名（可能是原始子域名或解析出的域名）
                                    domain_name = parts[0]
                                    if domain_name.endswith(':'):
                                        domain_name = domain_name[:-1]

                                    # 创建 {域名: IP} 字典
                                    domain_ip_dict = {domain_name: potential_ip}
                                    domain_ip_dicts.append(domain_ip_dict)

                                    # 如果没有alias，添加到无alias IP列表
                                    if not has_alias:
                                        no_alias_ips.append(potential_ip)
                                        print(f"host-Found IP for {subdomain}: {potential_ip} (no alias)")
                                    else:
                                        print(f"host-Found IP for {domain_name}: {potential_ip} (with alias)")

            except Exception as e:
                print(f"host-Error processing {subdomain}: {e}")

    # 创建任务但按顺序执行
    tasks = [process_subdomain(sub) for sub in subdomains]
    await asyncio.gather(*tasks)

    # 去重处理
    unique_domain_ip_dicts = []
    seen = set()

    for item in domain_ip_dicts:
        # 将字典转换为可哈希的元组进行去重
        key = tuple(item.items())[0]
        if key not in seen:
            seen.add(key)
            unique_domain_ip_dicts.append(item)

    unique_no_alias_ips = sorted(set(no_alias_ips))

    # 可选：写入文件
    # with open('./log/ip.txt', 'w', encoding='utf-8') as f:
    #     for ip in unique_no_alias_ips:
    #         f.write(f"host-{ip}\n")

    return [unique_domain_ip_dicts, unique_no_alias_ips]


# 同步调用接口
def run(subdomains: List[str]) -> Tuple[List[Dict[str, str]], List[str]]:
    """保持向后兼容的同步接口"""
    return asyncio.run(get_ips_from_subdomains_async(subdomains))


# 测试示例
# if __name__ == "__main__":
#     test_subdomains = [
#         "www.bd7oxy.top",
#         "ander1023.bd7oxy.top",
#         "frp.bd7oxy.top"
#     ]
#
#     result = run(test_subdomains)
#     print("Final result:", result)
#     print("Domain-IP dicts:", result[0])
#     print("No-alias IPs:", result[1])