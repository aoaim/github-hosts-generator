#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author      :   aoaim
#   Orig Author :   XueWeiHan
#   Date        :   2025-03-18
#   Desc        :   使用 raw_ips.json 在本地测试连通性并生成 hosts
import json
import socket
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from common import write_hosts_content
from domains import GITHUB_URLS


TCP_TIMEOUT_SEC: float = 2.0
TEST_PORT: int = 443
RAW_IPS_FILE = "raw_ips.json"
REPORT_FILE = "connectivity_report.json"
DISCARD_LIST: List[str] = ["1.0.1.1", "1.2.1.1", "127.0.0.1"]

TCP_LIST: Dict[str, float] = {}


def load_raw_ips() -> Dict[str, List[str]]:
    file_path = Path(__file__).parent / RAW_IPS_FILE
    if not file_path.exists():
        raise FileNotFoundError(
            f"未找到 {RAW_IPS_FILE}，请先从远端更新该文件（由 GitHub Action 生成）"
        )

    with file_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    data = payload.get("data", {})
    if not isinstance(data, dict):
        raise ValueError(f"{RAW_IPS_FILE} 格式错误：缺少 data 字段")
    return data


def tcp_connect_time(ip: str, port: int = TEST_PORT) -> float:
    if ip in TCP_LIST:
        return TCP_LIST[ip]

    times = []
    for _ in range(3):
        try:
            start = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(TCP_TIMEOUT_SEC)
            sock.connect((ip, port))
            sock.close()
            elapsed = (time.time() - start) * 1000
            times.append(elapsed)
        except (socket.timeout, socket.error, OSError):
            times.append(TCP_TIMEOUT_SEC * 1000)

    times.sort()
    result = times[1]
    TCP_LIST[ip] = result
    return result


def test_ip_candidates(ip_list: List[str]) -> List[Tuple[str, float, bool]]:
    results: List[Tuple[str, float, bool]] = []
    timeout_ms = TCP_TIMEOUT_SEC * 1000
    for ip in ip_list:
        delay = tcp_connect_time(ip, TEST_PORT)
        results.append((ip, delay, delay < timeout_ms))
    results.sort(key=lambda x: x[1])
    return results


def select_best_ip(ip_list: List[str]) -> Tuple[Optional[str], List[Tuple[str, float, bool]]]:
    if not ip_list:
        return None, []

    test_results = test_ip_candidates(ip_list)
    working = [item for item in test_results if item[2]]
    if working:
        return working[0][0], test_results
    return test_results[0][0], test_results


def write_report(report: Dict[str, Dict[str, object]]) -> None:
    output_file = Path(__file__).parent / REPORT_FILE
    with output_file.open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)


def main() -> None:
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Start local connectivity test")
    raw_data = load_raw_ips()

    content = ""
    content_list = []
    report: Dict[str, Dict[str, object]] = {}

    for index, github_url in enumerate(GITHUB_URLS, start=1):
        candidates = list(raw_data.get(github_url, []))
        candidates = sorted({ip for ip in candidates if ip not in DISCARD_LIST})

        print(f"[{index}/{len(GITHUB_URLS)}] {github_url} - candidates: {len(candidates)}")

        best_ip, test_results = select_best_ip(candidates)
        if best_ip is None:
            ip_text = "# IP Address Not Found"
            print("  No candidate IP found")
        else:
            ip_text = best_ip
            preview = [f"{ip}:{delay:.1f}ms{'(ok)' if ok else '(timeout)'}" for ip, delay, ok in test_results[:5]]
            print(f"  Top results: {preview}")
            print(f"  Selected: {best_ip}")

        content += ip_text.ljust(30) + github_url
        if best_ip is not None and TCP_LIST.get(best_ip, 0) >= TCP_TIMEOUT_SEC * 1000:
            content += "  # Timeout"
        content += "\n"
        content_list.append((ip_text, github_url))

        report[github_url] = {
            "selected_ip": best_ip,
            "candidates": candidates,
            "results": [
                {"ip": ip, "delay_ms": round(delay, 1), "working": ok}
                for ip, delay, ok in test_results
            ],
        }

    write_hosts_content(content, content_list)
    write_report(report)
    print(f"Report saved: {REPORT_FILE}")
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - End local connectivity test")


if __name__ == "__main__":
    main()
