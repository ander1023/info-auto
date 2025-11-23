import time
from collections import defaultdict


def ip_to_int(ip):
    """IP转整数"""
    # 清理IP地址，移除可能的前缀
    clean_ip = ip.replace('cip-', '')
    octets = list(map(int, clean_ip.split('.')))
    return (octets[0] << 24) | (octets[1] << 16) | (octets[2] << 8) | octets[3]


def int_to_ip(num):
    """整数转IP"""
    return f"{(num >> 24) & 0xFF}.{(num >> 16) & 0xFF}.{(num >> 8) & 0xFF}.{num & 0xFF}"


def is_excluded(ip_str):
    """排除1和255结尾的IP"""
    last_octet = int(ip_str.split('.')[-1])
    return last_octet in (1, 255)


def group_by_gap(ips_int, max_gap=8):
    """按相邻IP差距≤8分组，超过则为独立IP"""
    if not ips_int:
        return [], []

    groups = []
    singles = []
    current_group = [ips_int[0]]

    for i in range(1, len(ips_int)):
        ip = ips_int[i]
        gap = ip - current_group[-1]
        if gap <= max_gap:
            current_group.append(ip)
        else:
            if len(current_group) == 1:
                singles.append(current_group[0])
            else:
                groups.append(current_group)
            current_group = [ip]

    # 处理最后一组
    if len(current_group) == 1:
        singles.append(current_group[0])
    else:
        groups.append(current_group)

    return groups, singles


def expand_group_properly(group, forward=3, backward=3):
    """扩段逻辑：向前/后各扩3个，补中间空缺"""
    min_ip = min(group)
    max_ip = max(group)
    original_set = set(group)

    # 向前扩3个
    forward_ips = []
    current = min_ip - 1
    while len(forward_ips) < forward:
        ip_str = int_to_ip(current)
        if not is_excluded(ip_str) and current not in original_set:
            forward_ips.append(current)
        current -= 1
    forward_ips.reverse()

    # 向后扩3个
    backward_ips = []
    current = max_ip + 1
    while len(backward_ips) < backward:
        ip_str = int_to_ip(current)
        if not is_excluded(ip_str) and current not in original_set:
            backward_ips.append(current)
        current += 1

    # 补中间空缺
    middle_ips = []
    for ip in range(min_ip + 1, max_ip):
        if ip not in original_set and not is_excluded(int_to_ip(ip)):
            middle_ips.append(ip)

    # 合并结果
    all_ips_int = forward_ips + group + middle_ips + backward_ips

    # 生成CIDR信息
    min_all = min(all_ips_int)
    max_all = max(all_ips_int)
    prefix_len = 32 - (max_all - min_all).bit_length()

    # 确保prefix_len在合理范围内
    prefix_len = max(24, min(32, prefix_len))

    cidr = f"{int_to_ip(min_all)}/{prefix_len}"

    return {
        "cidr": cidr,
        "ips_int": all_ips_int,
        "start_ip": int_to_ip(min_all),
        "end_ip": int_to_ip(max_all),
        "original_count": len(group),
        "expanded_count": len(all_ips_int)
    }


def cidr_to_ips(cidr):
    """将CIDR网段转换为该网段内的所有IP地址"""
    if '/' not in cidr:
        return [cidr]

    network, prefix_len = cidr.split('/')
    prefix_len = int(prefix_len)

    # 清理网络地址
    clean_network = network.replace('cip-', '')

    # 将网络地址转换为整数
    network_int = ip_to_int(clean_network)

    # 计算掩码和主机数量
    mask = (0xFFFFFFFF << (32 - prefix_len)) & 0xFFFFFFFF
    host_bits = 32 - prefix_len
    num_hosts = 2 ** host_bits

    # 计算网络地址和广播地址
    network_addr = network_int & mask
    broadcast_addr = network_addr + num_hosts - 1

    # 生成所有IP地址（排除网络地址和广播地址）
    ips = []
    for ip_int in range(network_addr + 1, broadcast_addr):  # 跳过网络地址和广播地址
        ip_str = int_to_ip(ip_int)
        if not is_excluded(ip_str):
            ips.append(ip_str)

    return ips


def run(input_ips):
    """
    总入口函数：输入IP列表，扩段后输出独立IP列表
    包含CIDR网段对应的所有IP

    Args:
        input_ips: 输入的IP地址列表

    Returns:
        tuple: (独立IP列表, CIDR网段列表)
    """
    # 清理输入IP，移除可能的前缀
    cleaned_ips = [ip.replace('cip-', '') for ip in input_ips]

    # 过滤无效IP
    valid_ips = [ip for ip in cleaned_ips if not is_excluded(ip)]
    if not valid_ips:
        return [], []

    print(f"有效IP数量: {len(valid_ips)}")

    # 转换并排序
    ips_int = [ip_to_int(ip) for ip in valid_ips]
    ips_int_sorted = sorted(ips_int)

    # 按/24网段分组处理
    subnet_groups = defaultdict(list)
    for ip_int in ips_int_sorted:
        ip_str = int_to_ip(ip_int)
        prefix = ".".join(ip_str.split('.')[:3])
        subnet_groups[prefix].append(ip_int)

    print(f"网段数量: {len(subnet_groups)}")

    # 处理每个网段
    all_cidr_ips = []  # 所有CIDR网段对应的IP
    all_single_ips = []  # 独立IP
    cidr_list = []  # CIDR网段列表

    for prefix, ips in subnet_groups.items():
        print(f"处理网段 {prefix}.x，包含 {len(ips)} 个IP")
        groups, singles = group_by_gap(ips, max_gap=8)
        print(f"  分组结果: {len(groups)}个连续组, {len(singles)}个独立IP")

        # 处理分组（扩段并生成CIDR）
        for group in groups:
            result = expand_group_properly(group)
            cidr_list.append(result["cidr"])

            # 将CIDR网段转换为所有IP并添加
            cidr_ips = cidr_to_ips(result["cidr"])
            all_cidr_ips.extend(cidr_ips)
            print(f"  生成CIDR: {result['cidr']} -> {len(cidr_ips)}个IP")

        # 收集独立IP
        single_ip_strs = [int_to_ip(ip) for ip in singles]
        all_single_ips.extend(single_ip_strs)
        if singles:
            print(f"  独立IP: {len(singles)}个")

    # 合并所有IP并去重
    all_ips = list(set(all_cidr_ips + all_single_ips))

    # 按IP地址排序
    all_ips_sorted = sorted(all_ips, key=lambda ip: ip_to_int(ip))
    cidr_list_sorted = sorted(cidr_list, key=lambda cidr: ip_to_int(cidr.split('/')[0]))

    print(f"\n最终结果: {len(all_ips_sorted)}个独立IP, {len(cidr_list_sorted)}个CIDR网段")

    return all_ips_sorted, cidr_list_sorted


def run_simple(input_ips):
    """
    简化版入口函数：只返回独立IP列表

    Args:
        input_ips: 输入的IP地址列表

    Returns:
        list: 扩段后的所有独立IP地址列表
    """
    final_ips, _ = run(input_ips)
    return final_ips


# 使用示例
if __name__ == "__main__":
    # 测试用例1：正常情况
    example_ips = [
        "192.168.1.10",
        "192.168.1.11",
        "192.168.1.12",
        "192.168.2.20",
        "192.168.2.25",
        "192.168.3.100"
    ]

    print("测试用例1 - 正常情况")
    print("输入IP列表:")
    for ip in example_ips:
        print(f"  {ip}")

    result_ips, result_cidrs = run(example_ips)

    print(f"\n生成的CIDR网段:")
    for cidr in result_cidrs:
        cidr_ips = cidr_to_ips(cidr)
        print(f"  {cidr}: {len(cidr_ips)}个IP")

    print(f"\n扩段后的独立IP列表 (前10个):")
    for ip in result_ips[:10]:
        print(f"  {ip}")

    # 测试用例2：边界情况 - 只有1个IP
    print("\n" + "=" * 50)
    print("测试用例2 - 只有1个IP")
    single_ip = ["192.168.1.10"]
    result_ips, result_cidrs = run(single_ip)
    print(f"输入: {single_ip}")
    print(f"输出: {len(result_ips)}个IP, {len(result_cidrs)}个CIDR")

    # 测试用例3：边界情况 - 空列表
    print("\n" + "=" * 50)
    print("测试用例3 - 空列表")
    empty_ips = []
    result_ips, result_cidrs = run(empty_ips)
    print(f"输入: 空列表")
    print(f"输出: {len(result_ips)}个IP, {len(result_cidrs)}个CIDR")

    # 测试用例4：排除IP的情况
    print("\n" + "=" * 50)
    print("测试用例4 - 包含排除IP")
    excluded_ips = ["192.168.1.1", "192.168.1.255", "192.168.1.10"]
    result_ips, result_cidrs = run(excluded_ips)
    print(f"输入: {excluded_ips}")
    print(f"输出: {len(result_ips)}个IP, {len(result_cidrs)}个CIDR")