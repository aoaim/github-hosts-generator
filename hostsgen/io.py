import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

from hostsgen.config import HOSTS_FILE, HOSTS_JSON_FILE, OUTPUT_DIR

HOSTS_TEMPLATE = """# Hosts Generator Start
{content}# Update time: {update_time}
# Hosts Generator End
"""

HostEntry = tuple[str, str]


def ensure_output_dir() -> Path:
    """Create the output directory when it does not exist yet."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    return OUTPUT_DIR


def utc_timestamp() -> str:
    """Return a stable UTC ISO-8601 timestamp."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_text_file(file_path: Path, content: str) -> None:
    """Write UTF-8 text files with Unix newlines for stable diffs."""
    ensure_output_dir()
    with file_path.open("w", encoding="utf-8", newline="\n") as output_file:
        output_file.write(content)


def write_json_file(file_path: Path, payload: object) -> None:
    """Write formatted JSON output to the output directory."""
    ensure_output_dir()
    with file_path.open("w", encoding="utf-8", newline="\n") as output_file:
        json.dump(payload, output_file, ensure_ascii=False, indent=2)
        output_file.write("\n")


def render_hosts_content(entries: Iterable[HostEntry]) -> str:
    """Render the final hosts file content from selected mappings."""
    lines = [format_host_entry(ip, domain) for ip, domain in entries]
    if not lines:
        return ""

    update_time = datetime.now(timezone.utc).astimezone(
        timezone(timedelta(hours=8))
    ).replace(microsecond=0).isoformat()
    return HOSTS_TEMPLATE.format(content="\n".join(lines) + "\n", update_time=update_time)


def format_host_entry(ip: str, domain: str) -> str:
    """Format one hosts entry with aligned columns."""
    return f"{ip.ljust(30)}{domain}"


def write_hosts_content(entries: list[HostEntry]) -> str:
    """Write both `hosts` and `hosts.json` from selected IP mappings."""
    if not entries:
        return ""

    hosts_content = render_hosts_content(entries)

    write_text_file(HOSTS_FILE, hosts_content)
    write_json_file(HOSTS_JSON_FILE, entries)
    return hosts_content
