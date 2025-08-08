#!/usr/bin/env python3
"""
Fetch or watch the status of a Mosaic agent run by run_id.

Usage:
  python get_status.py --run-id RUN_ID [--watch] [--interval 5]
"""

import argparse
import json
import os
import sys
import time
from typing import Optional

import requests


DEFAULT_BASE_URL = "http://localhost:8080"


def resolve_api_key(explicit_key: Optional[str]) -> str:
    api_key = explicit_key or os.environ.get("MOSAIC_API_KEY")
    if not api_key:
        print("❌ Error: API key required. Use --api-key or set MOSAIC_API_KEY")
        sys.exit(1)
    if not api_key.startswith("mk_"):
        print("❌ Error: Invalid API key format (must start with 'mk_')")
        sys.exit(1)
    return api_key


def fetch_status(base_url: str, headers: dict, run_id: str) -> dict:
    resp = requests.get(f"{base_url}/agent_run/{run_id}", headers=headers, timeout=30)
    try:
        resp.raise_for_status()
    except requests.HTTPError as e:
        print(f"❌ Failed to fetch status: {e}\n{resp.text}")
        sys.exit(1)
    return resp.json()


def print_summary(data: dict) -> None:
    status = data.get("status")
    print(f"status {status}")
    outputs = data.get("outputs") or []
    if outputs:
        print(f"outputs {len(outputs)}")
        for idx, out in enumerate(outputs, 1):
            url = out.get("video_url") or out.get("url")
            if url:
                print(f"  {idx}. {url}")


def main():
    parser = argparse.ArgumentParser(description="Get or watch a Mosaic agent run status")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--watch", action="store_true", help="Poll until completed or failed")
    parser.add_argument("--interval", type=int, default=5, help="Polling interval seconds")
    parser.add_argument("--api-key", help="Mosaic API key (or use MOSAIC_API_KEY env var)")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    args = parser.parse_args()

    api_key = resolve_api_key(args.api_key)
    headers = {"Authorization": f"Bearer {api_key}"}

    if not args.watch:
        data = fetch_status(args.base_url, headers, args.run_id)
        print(json.dumps(data, indent=2))
        return

    # watch mode
    print(f"👀 Watching run {args.run_id} (every {args.interval}s)...")
    while True:
        data = fetch_status(args.base_url, headers, args.run_id)
        print_summary(data)
        if data.get("status") in ("completed", "failed"):
            print("\n📦 Full response:")
            print(json.dumps(data, indent=2))
            break
        time.sleep(args.interval)


if __name__ == "__main__":
    main()


