#!/usr/bin/env python
# -*- coding:utf-8 -*-

import json
import socket
import time
from datetime import datetime
from typing import Any

from hostsgen.config import RAW_IPS_FILE, REPORT_FILE, TARGET_DOMAINS
from hostsgen.io import HostEntry, ensure_output_dir, write_hosts_content, write_json_file

TCP_TIMEOUT_SEC = 2.0
TEST_PORT = 443
TCP_SAMPLE_COUNT = 5
DISCARD_LIST = {"1.0.1.1", "1.2.1.1", "127.0.0.1"}
MISSING_IP_PLACEHOLDER = "# IP Address Not Found"

CandidateResult = tuple[str, float, bool]
TCP_CACHE: dict[str, float] = {}


def load_raw_ips() -> dict[str, list[str]]:
    """Load candidate IP data produced by the remote fetch step."""
    if not RAW_IPS_FILE.exists():
        raise FileNotFoundError(
            f"未找到 {RAW_IPS_FILE.name}，请先从远端更新该文件（由 GitHub Action 生成）"
        )

    with RAW_IPS_FILE.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    data = payload.get("data", {})
    if not isinstance(data, dict):
        raise ValueError(f"{RAW_IPS_FILE.name} 格式错误：缺少 data 字段")
    return data


def load_candidates(raw_data: dict[str, list[str]], domain: str) -> list[str]:
    """Return unique candidates with known invalid IPs removed."""
    return sorted({ip for ip in raw_data.get(domain, []) if ip not in DISCARD_LIST})


def tcp_connect_time(ip: str, port: int = TEST_PORT) -> float:
    """Measure median TCP connect time over repeated attempts."""
    cached = TCP_CACHE.get(ip)
    if cached is not None:
        return cached

    times = []
    for _ in range(TCP_SAMPLE_COUNT):
        try:
            start = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(TCP_TIMEOUT_SEC)
            sock.connect((ip, port))
            sock.close()
            times.append((time.time() - start) * 1000)
        except (socket.timeout, socket.error, OSError):
            times.append(TCP_TIMEOUT_SEC * 1000)

    result = sorted(times)[TCP_SAMPLE_COUNT // 2]
    TCP_CACHE[ip] = result
    return result


def test_ip_candidates(ip_list: list[str]) -> list[CandidateResult]:
    """Benchmark all candidate IPs and sort by latency."""
    timeout_ms = TCP_TIMEOUT_SEC * 1000
    measured = [(ip, tcp_connect_time(ip, TEST_PORT)) for ip in ip_list]
    return sorted(
        [(ip, delay, delay < timeout_ms) for ip, delay in measured],
        key=lambda item: item[1],
    )


def select_best_ip(ip_list: list[str]) -> tuple[str | None, list[CandidateResult]]:
    """Prefer the fastest reachable IP, then fall back to the fastest timeout."""
    if not ip_list:
        return None, []

    test_results = test_ip_candidates(ip_list)
    selected = next((item for item in test_results if item[2]), test_results[0])
    return selected[0], test_results


def build_report_entry(
    selected_ip: str | None,
    candidates: list[str],
    test_results: list[CandidateResult],
) -> dict[str, Any]:
    """Build a serialisable report entry for one domain."""
    return {
        "selected_ip": selected_ip,
        "candidates": candidates,
        "results": [
            {"ip": ip, "delay_ms": round(delay, 1), "working": ok}
            for ip, delay, ok in test_results
        ],
    }


def format_top_results(test_results: list[CandidateResult]) -> list[str]:
    """Return a compact preview of the best candidate measurements."""
    return [
        f"{ip}:{delay:.1f}ms{'(ok)' if ok else '(timeout)'}"
        for ip, delay, ok in test_results[:5]
    ]


def build_hosts_entry(selected_ip: str | None, domain: str) -> HostEntry:
    """Create the final hosts mapping for one domain."""
    return selected_ip or MISSING_IP_PLACEHOLDER, domain


def write_report(report: dict[str, dict[str, Any]]) -> None:
    """Write the connectivity report to the output directory."""
    write_json_file(REPORT_FILE, report)


def main() -> None:
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Start local connectivity test")
    ensure_output_dir()
    raw_data = load_raw_ips()

    hosts_entries: list[HostEntry] = []
    report: dict[str, dict[str, Any]] = {}

    for index, domain in enumerate(TARGET_DOMAINS, start=1):
        candidates = load_candidates(raw_data, domain)
        print(f"[{index}/{len(TARGET_DOMAINS)}] {domain} - candidates: {len(candidates)}")

        best_ip, test_results = select_best_ip(candidates)
        if best_ip is None:
            print("  No candidate IP found")
        else:
            print(f"  Top results: {format_top_results(test_results)}")
            print(f"  Selected: {best_ip}")

        hosts_entries.append(build_hosts_entry(best_ip, domain))
        report[domain] = build_report_entry(best_ip, candidates, test_results)

    write_hosts_content(hosts_entries)
    write_report(report)
    print(f"Report saved: {REPORT_FILE.name}")
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - End local connectivity test")


if __name__ == "__main__":
    main()
