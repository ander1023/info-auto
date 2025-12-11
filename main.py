import tools.host
import tools.masscan
import tools.nali
import tools.cip
import tools.whatweb
import tools.exceltools


def host() -> int:
    """
    处理子域名解析流程

    Returns:
        int: 处理的记录数量，0表示没有需要处理的记录
    """
    # 读取未处理的子域名记录
    subdomain = tools.exceltools.read_excel_sheet_as_list("info-auto.xlsx", "子域名", "host处理状态!=处理")

    if not subdomain:
        print("没有需要处理的子域名记录")
        return 0

    print(f"开始处理 {len(subdomain)} 条子域名记录")

    # 执行host解析
    hostTemp = tools.host.run(subdomain)
    subdomainIps = hostTemp[0]
    noCdnIPs = hostTemp[1]

    # 更新子域名对应的IP地址
    tools.exceltools.update_excel_status_dict(
        file_path="info-auto.xlsx",
        sheet_name="子域名",
        target_list=subdomainIps,
        match_column="名称",
        status_column="对应ip",
    )

    # 去重追加非CDN IP到对应表格
    tools.exceltools.deduplicate_append_excel(
        file_path="info-auto.xlsx",
        sheet_name="非CDN-IP",
        target_list=noCdnIPs,
        match_column='名称'
    )

    # 更新子域名处理状态
    tools.exceltools.update_excel_status(
        file_path="info-auto.xlsx",
        sheet_name="子域名",
        target_list=subdomain,
        match_column="名称",
        status_column="host处理状态",
        status_value="处理"
    )

    print(f"子域名处理完成，共处理 {len(subdomain)} 条记录")
    return len(subdomain)


def nali() -> int:
    """
    处理IP地理位置和云服务商识别流程

    Returns:
        int: 处理的记录数量，0表示没有需要处理的记录
    """
    # 读取未处理的非CDN IP记录
    ips = tools.exceltools.read_excel_sheet_as_list("info-auto.xlsx", "非CDN-IP", "nali处理状态!=处理")

    if not ips:
        print("没有需要处理的IP记录")
        return 0

    print(f"开始处理 {len(ips)} 条IP记录")

    # 执行nali分析，识别云IP和非云IP
    cp, ncp = tools.nali.run(ips)  # 云IP, 非云IP

    # 更新云IP类型和处理状态
    tools.exceltools.update_excel_status(
        file_path="info-auto.xlsx",
        sheet_name="非CDN-IP",
        target_list=cp,
        match_column="名称",
        status_column="类型",
        status_value="云IP"
    )
    tools.exceltools.update_excel_status(
        file_path="info-auto.xlsx",
        sheet_name="非CDN-IP",
        target_list=cp,
        match_column="名称",
        status_column="nali处理状态",
        status_value="处理"
    )

    # 更新非云IP类型和处理状态
    tools.exceltools.update_excel_status(
        file_path="info-auto.xlsx",
        sheet_name="非CDN-IP",
        target_list=ncp,
        match_column="名称",
        status_column="类型",
        status_value="非云IP"
    )
    tools.exceltools.update_excel_status(
        file_path="info-auto.xlsx",
        sheet_name="非CDN-IP",
        target_list=ncp,
        match_column="名称",
        status_column="nali处理状态",
        status_value="处理"
    )

    # 读取所有云IP并去重追加到扩展段表格
    allcip = tools.exceltools.read_excel_sheet_as_list("info-auto.xlsx", "非CDN-IP", "类型=云IP")
    tools.exceltools.deduplicate_append_excel(
        file_path="info-auto.xlsx",
        sheet_name="云IP+非云IP扩段",
        target_list=allcip,
        match_column='名称'
    )

    # 处理非云IP的CIDR扩展
    allncip = tools.exceltools.read_excel_sheet_as_list("info-auto.xlsx", "非CDN-IP", "类型=非云IP")
    cip, _ = tools.cip.run(allncip)
    print(f"非云IP扩展结果: {cip}")

    # 去重追加扩展后的IP段
    tools.exceltools.deduplicate_append_excel(
        file_path="info-auto.xlsx",
        sheet_name="云IP+非云IP扩段",
        target_list=cip,  # 扩展后的IP段
        match_column='名称'
    )

    print(f"IP分析完成，共处理 {len(ips)} 条记录")
    return len(ips)


def masscan() -> int:
    """
    执行端口扫描流程

    Returns:
        int: 处理的记录数量，0表示没有需要处理的记录
    """
    # 读取未处理的IP段记录，限制每次处理10条
    ips = tools.exceltools.read_excel_sheet_as_list(
        "info-auto.xlsx",
        "云IP+非云IP扩段",
        "masscan处理状态!=处理",
        limit=10
    )

    if not ips:
        print("没有需要扫描的IP段记录")
        return 0

    print(f"开始端口扫描 {len(ips)} 条IP段记录")

    # 执行masscan端口扫描
    ipport = tools.masscan.run(ips)
    print(f"端口扫描发现 {len(ipport)} 个开放端口")


    # 统计每个IP的端口数量
    ip_count = {}
    for item in ipport:
        ip = item.split(':')[0]
        ip_count[ip] = ip_count.get(ip, 0) + 1

    # 保留同IP端口数量小于60个的item
    filtered_ipport = [item for item in ipport if ip_count[item.split(':')[0]] < 60]

    print(f"过滤后剩余 {len(filtered_ipport)} 个开放端口")

    # 去重追加发现的IP端口到对应表格
    tools.exceltools.deduplicate_append_excel(
        file_path="info-auto.xlsx",
        sheet_name="IP端口",
        target_list=filtered_ipport,
        match_column='名称'
    )

    # 更新masscan处理状态
    tools.exceltools.update_excel_status(
        file_path="info-auto.xlsx",
        sheet_name="云IP+非云IP扩段",
        target_list=ips,
        match_column="名称",
        status_column="masscan处理状态",
        status_value="处理"
    )

    print(f"端口扫描完成，共处理 {len(ips)} 条IP段记录")
    return len(ips)


def whatweb() -> int:
    """
    处理HTTP服务发现流程

    Returns:
        int: 处理的记录数量，0表示没有需要处理的记录
    """
    # 读取所有可解析的子域名（有对应IP的）
    canHostSubdomain = tools.exceltools.read_excel_sheet_as_list("info-auto.xlsx", "子域名", "non_blank_对应ip")
    canHostIP = tools.exceltools.read_excel_sheet_as_list(
        "info-auto.xlsx",
        "子域名",
        target_column="对应ip",
        filter_condition="non_blank_对应ip"
    )

    if not canHostSubdomain:
        print("没有可解析的子域名记录")

    print(f"发现 {len(canHostSubdomain)} 个可解析的子域名")

    # 去重追加可解析子域名到HTTP汇总表格
    tools.exceltools.deduplicate_append_excel(
        file_path="info-auto.xlsx",
        sheet_name="http汇总",
        target_list=canHostSubdomain,
        match_column='名称'
    )

    # 创建IP到子域名的映射关系
    ip_to_subdomain = dict(zip(canHostIP, canHostSubdomain))

    # 读取所有IP端口记录
    ipport = tools.exceltools.read_excel_sheet_as_list("info-auto.xlsx", "IP端口")

    # 将IP和端口转换为子域名和端口的笛卡尔积组合
    ipToSubdomainPort = []
    for item in ipport:
        ip, port = item.split(':', 1)
        subdomain = ip_to_subdomain.get(ip, ip)
        # 如果是范围端口或逗号分隔的端口
        if '-' in port or ',' in port:
            # 处理端口范围或列表
            if '-' in port:
                start, end = map(int, port.split('-'))
                for p in range(start, end + 1):
                    ipToSubdomainPort.append(f"{subdomain}:{p}")
            elif ',' in port:
                for p in port.split(','):
                    ipToSubdomainPort.append(f"{subdomain}:{p}")
        else:
            # 单个端口
            ipToSubdomainPort.append(f"{subdomain}:{port}")

    print(f"生成 {len(ipToSubdomainPort)} 条子域名端口记录")

    # 去重追加子域名端口到HTTP汇总表格
    tools.exceltools.deduplicate_append_excel(
        file_path="info-auto.xlsx",
        sheet_name="http汇总",
        target_list=ipToSubdomainPort,
        match_column='名称'
    )
    # 读取未处理的HTTP记录进行httpx解析
    urls = tools.exceltools.read_excel_sheet_as_list("info-auto.xlsx", "http汇总",
                                                     filter_condition="httpx处理状态!=处理")

    if not urls:
        print("没有需要HTTP探测的记录")
        return 0

    print(f"开始HTTP探测 {len(urls)} 条记录")
    # 这里可以添加httpx处理逻辑
    # tools.httpx.run(urls)
    results = tools.whatweb.run(urls)
    resultUrl = [url for item in results for url in item.keys()]
    tools.exceltools.deduplicate_append_excel(
        file_path="info-auto.xlsx",
        sheet_name="http解析",
        target_list=resultUrl,
        match_column='名称'
    )
    tools.exceltools.update_excel_status_dict(
        file_path="info-auto.xlsx",
        sheet_name="http解析",
        target_list=results,
        match_column="名称",
        status_column="类型",
    )
    tools.exceltools.update_excel_status(
        file_path="info-auto.xlsx",
        sheet_name="http汇总",
        target_list=urls,
        match_column="名称",
        status_column="httpx处理状态",
        status_value="处理"
    )
    return len(urls)


def main():
    """
    主函数：按顺序执行信息收集流程

    执行流程:
    1. 子域名解析 (host)
    2. IP地理位置和云服务商识别 (nali)
    3. 端口扫描 (masscan)
    4. HTTP服务发现 (httpx)

    循环执行直到所有流程处理完成
    """
    print("开始信息收集自动化流程...")

    iteration = 1
    while True:
        print(f"\n=== 第 {iteration} 轮处理 ===")

        processed_count = 0
        processed_count += host()
        processed_count += nali()
        processed_count += masscan()
        processed_count += whatweb()

        if processed_count == 0:
            print("\n所有处理流程已完成，退出循环")
            break

        iteration += 1

    print("信息收集自动化流程执行完毕")


if __name__ == "__main__":
    main()
