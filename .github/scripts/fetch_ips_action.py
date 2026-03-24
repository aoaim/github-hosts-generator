#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   GitHub Action 脚本
#   从云端（境外）获取 GitHub 域名 IP 列表
#   输出: raw_ips.json
#
import json
import re
import importlib.util
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

PROJECT_ROOT = Path(__file__).resolve().parents[2]

import httpx
import dns.resolver
from tenacity import retry, stop_after_attempt, wait_fixed


def load_github_urls() -> list[str]:
    domains_path = PROJECT_ROOT / "domains.py"
    spec = importlib.util.spec_from_file_location("domains", domains_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load domains module from: {domains_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    urls = getattr(module, "GITHUB_URLS", None)
    if not isinstance(urls, list):
        raise RuntimeError("GITHUB_URLS is missing or invalid in domains.py")
    return urls


GITHUB_URLS = load_github_urls()

DNS_TIMEOUT_SEC = 2.0
DNS_LIFETIME_SEC = 2.0
DNS_WORKERS = 12
DOMAIN_WORKERS = 8


# 国际权威 DNS 服务器
INTERNATIONAL_DNS = [
    # 国际
    "8.8.8.8",          # Google
    "1.1.1.1",          # Cloudflare
    "9.9.9.9",          # Quad9
    "208.67.222.222",   # OpenDNS
    # DNS.SB (德国/全球多节点)
    "185.222.222.222",  # DNS.SB primary
    "45.11.45.11",      # DNS.SB secondary
    # Level 3 Parent DNS (美国)
    "4.2.2.1",
    # 台湾
    "101.101.101.101",  # TWNIC Quad101
    # 香港
    "202.14.67.4",      # PCCW
    "203.80.64.66",     # HKBN
    # 新加坡
    "165.21.83.88",     # SingTel
    "203.116.1.78",     # StarHub
    # 日本
    "203.112.2.4",      # Line/OCN
    "210.196.3.183",    # IIJ
]


def query_dns(domain, dns_server):
    resolver = dns.resolver.Resolver()
    resolver.nameservers = [dns_server]
    resolver.timeout = DNS_TIMEOUT_SEC
    resolver.lifetime = DNS_LIFETIME_SEC
    answers = resolver.resolve(domain, 'A')
    return [rdata.address for rdata in answers]


def get_ip_list_from_dns(domain, dns_servers=None):
    """从指定 DNS 服务器并发查询域名 IP"""
    if dns_servers is None:
        dns_servers = INTERNATIONAL_DNS

    ips = set()
    max_workers = min(DNS_WORKERS, len(dns_servers))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(query_dns, domain, dns_server): dns_server for dns_server in dns_servers}
        for future in as_completed(futures):
            dns_server = futures[future]
            try:
                ips.update(future.result())
            except Exception as e:
                print(f"  DNS {dns_server} query failed for {domain}: {e}")

    return list(ips)


@retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
def get_ip_list_from_ipaddress_com(session, domain):
    """从 ipaddress.com 抓取 IP 列表"""
    url = f'https://sites.ipaddress.com/{domain}'
    headers = {
        'User-Agent': 'curl/7.81.0'
    }
    
    try:
        rs = session.get(url, headers=headers)
        rs.raise_for_status()
        # 匹配页面中的 IP 地址
        pattern = r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b"
        ip_list = re.findall(pattern, rs.text)
        # 过滤无效 IP
        valid_ips = [ip for ip in ip_list if ip not in ["1.0.1.1", "1.2.1.1", "127.0.0.1"]]
        return valid_ips
    except Exception as ex:
        print(f"  ipaddress.com query failed for {domain}: {ex}")
        return []


def process_domain(domain):
    print(f"\nProcessing: {domain}")
    all_ips = set()

    with httpx.Client(timeout=10.0, follow_redirects=True) as session:
        # 1. 从 ipaddress.com 获取
        ip_list_web = get_ip_list_from_ipaddress_com(session, domain)
    all_ips.update(ip_list_web)
    print(f"  ipaddress.com IPs: {len(ip_list_web)}")

    # 2. 从国际 DNS 获取（并发）
    ip_list_dns = get_ip_list_from_dns(domain)
    all_ips.update(ip_list_dns)
    print(f"  DNS IPs: {len(ip_list_dns)}")

    ip_list = sorted(all_ips)
    print(f"  Total unique IPs: {len(ip_list)}")
    return domain, ip_list


def main():
    print("=" * 60)
    print("Fetching GitHub IPs from cloud (GitHub Action)")
    print("=" * 60)
    
    results = {}

    with ThreadPoolExecutor(max_workers=DOMAIN_WORKERS) as executor:
        future_map = {executor.submit(process_domain, domain): domain for domain in GITHUB_URLS}
        for future in as_completed(future_map):
            domain = future_map[future]
            try:
                domain_name, ip_list = future.result()
                results[domain_name] = ip_list
            except Exception as e:
                print(f"Failed processing {domain}: {e}")
                results[domain] = []
    
    # 写入 raw_ips.json
    output = {
        "update_time": __import__('datetime').datetime.utcnow().isoformat() + "Z",
        "source": "github-action",
        "data": results
    }
    
    with open('raw_ips.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print("\n" + "=" * 60)
    print(f"✓ Saved to raw_ips.json")
    print(f"  Total domains: {len(results)}")
    print(f"  Total IP entries: {sum(len(ips) for ips in results.values())}")
    print("=" * 60)


if __name__ == "__main__":
    main()
