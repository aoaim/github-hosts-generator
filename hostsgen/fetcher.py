#!/usr/bin/env python
# -*- coding:utf-8 -*-

from concurrent.futures import ThreadPoolExecutor, as_completed

import dns.resolver

from hostsgen.config import PROJECT_ROOT, RAW_IPS_FILE, TARGET_DOMAINS
from hostsgen.io import ensure_output_dir, utc_timestamp, write_json_file

DNS_TIMEOUT_SEC = 2.0
DNS_LIFETIME_SEC = 2.0
DNS_WORKERS = 12
DOMAIN_WORKERS = 8

INTERNATIONAL_DNS = (
    "8.8.8.8",          # Google
    "1.1.1.1",          # Cloudflare
    "9.9.9.9",          # Quad9
    "208.67.222.222",   # OpenDNS
    "185.222.222.222",  # DNS.SB
    "4.2.2.1",          # Level 3
    "101.101.101.101",  # TWNIC
    "210.196.3.183",    # IIJ
    "203.80.96.10",     # HKBN
    "202.45.84.58",     # HGC
)


def query_dns(domain: str, dns_server: str) -> list[str]:
    """Resolve one domain against one DNS server."""
    resolver = dns.resolver.Resolver()
    resolver.nameservers = [dns_server]
    resolver.timeout = DNS_TIMEOUT_SEC
    resolver.lifetime = DNS_LIFETIME_SEC
    answers = resolver.resolve(domain, "A")
    return [rdata.address for rdata in answers]


def get_ip_list_from_dns(domain: str, dns_servers: tuple[str, ...] = INTERNATIONAL_DNS) -> list[str]:
    """Query all configured DNS resolvers in parallel for one domain."""
    print(f"  DNS query start: {domain} ({len(dns_servers)} resolvers)")
    ips: set[str] = set()
    max_workers = min(DNS_WORKERS, len(dns_servers))

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(query_dns, domain, dns_server): dns_server
            for dns_server in dns_servers
        }
        for future in as_completed(futures):
            dns_server = futures[future]
            try:
                ips.update(future.result())
            except Exception as exc:
                print(f"  DNS {dns_server} query failed for {domain}: {exc}")

    print(f"  DNS query done: {domain}, unique A records: {len(ips)}")
    return sorted(ips)


def process_domain(domain: str) -> tuple[str, list[str]]:
    """Collect candidate IPs for one domain."""
    print(f"\nProcessing: {domain}")
    ip_list = get_ip_list_from_dns(domain)
    print(f"  DNS IPs: {len(ip_list)}")
    print(f"  Total unique IPs: {len(ip_list)} for {domain}")
    return domain, ip_list


def write_raw_ip_output(results: dict[str, list[str]]) -> None:
    """Persist the fetched candidate IP list."""
    write_json_file(
        RAW_IPS_FILE,
        {
            "update_time": utc_timestamp(),
            "source": "github-action",
            "data": results,
        },
    )


def collect_domain_results() -> dict[str, list[str]]:
    """Fetch candidate IPs for every configured domain."""
    results: dict[str, list[str]] = {}
    total = len(TARGET_DOMAINS)

    with ThreadPoolExecutor(max_workers=DOMAIN_WORKERS) as executor:
        future_map = {executor.submit(process_domain, domain): domain for domain in TARGET_DOMAINS}

        for completed, future in enumerate(as_completed(future_map), start=1):
            domain = future_map[future]
            try:
                domain_name, ip_list = future.result()
                results[domain_name] = ip_list
            except Exception as exc:
                print(f"Failed processing {domain}: {exc}")
                results[domain] = []

            print(f"Progress: {completed}/{total} domains finished")

    return results


def main() -> None:
    print("=" * 60)
    print("Fetching target IPs from cloud (GitHub Action)")
    print("=" * 60)

    print("Domain source: hostsgen/config.py")
    print(f"Total target domains: {len(TARGET_DOMAINS)}")
    for index, domain in enumerate(TARGET_DOMAINS, start=1):
        print(f"  [{index:02d}] {domain}")

    ensure_output_dir()
    results = collect_domain_results()
    write_raw_ip_output(results)

    print("\n" + "=" * 60)
    print(f"Saved to {RAW_IPS_FILE.relative_to(PROJECT_ROOT)}")
    print(f"Total domains: {len(results)}")
    print(f"Total IP entries: {sum(len(ips) for ips in results.values())}")
    print("=" * 60)


if __name__ == "__main__":
    main()
