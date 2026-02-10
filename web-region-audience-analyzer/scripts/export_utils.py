#!/usr/bin/env python3
"""
Utilities for export file paths.
"""
import os
import re
import urllib.parse
from datetime import datetime


def _sanitize_hostname(hostname):
    cleaned = hostname.strip().lower()
    if cleaned.startswith("www."):
        cleaned = cleaned[4:]
    cleaned = re.sub(r"[^a-z0-9.-]+", "-", cleaned)
    cleaned = cleaned.strip("-.")
    return cleaned or "unknown-site"


def get_default_downloads_dir(home_dir=None):
    base_home = home_dir or os.path.expanduser("~")
    return os.path.join(base_home, "Downloads")


def build_default_markdown_output_path(url, now=None, home_dir=None):
    dt = now or datetime.now()
    parsed = urllib.parse.urlparse(url or "")
    hostname = _sanitize_hostname(parsed.netloc or parsed.path or "unknown-site")
    timestamp = dt.strftime("%Y%m%d-%H%M%S")
    filename = f"web-region-audience-report-{hostname}-{timestamp}.md"
    return os.path.join(get_default_downloads_dir(home_dir=home_dir), filename)
