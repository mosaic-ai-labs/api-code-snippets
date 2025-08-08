#!/usr/bin/env python3
"""
Run a Mosaic agent on one or more uploaded videos.

Usage:
  python run_agent.py --agent-id YOUR_AGENT_ID --video-ids VID1,VID2 [--callback-url URL]
"""

import argparse
import json
import os
import sys
from typing import List, Optional

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


def parse_ids(ids_str: str) -> List[str]:
    return [v.strip() for v in ids_str.split(',') if v.strip()]


def run_agent(base_url: str, headers: dict, agent_id: str, video_ids: List[str], callback_url: Optional[str]) -> str:
    payload = {"video_ids": video_ids}
    if callback_url:
        payload["callback_url"] = callback_url

    resp = requests.post(
        f"{base_url}/agent/{agent_id}/run",
        headers={**headers, "Content-Type": "application/json"},
        json=payload,
        timeout=60,
    )
    try:
        resp.raise_for_status()
    except requests.HTTPError as e:
        print(f"❌ Failed to start agent run: {e}\n{resp.text}")
        sys.exit(1)

    data = resp.json()
    run_id = data.get("run_id")
    if not run_id:
        print(f"❌ No run_id returned: {data}")
        sys.exit(1)
    return run_id


def main():
    parser = argparse.ArgumentParser(description="Run a Mosaic agent on uploaded videos")
    parser.add_argument("--agent-id", required=True)
    parser.add_argument("--video-ids", required=True, help="Comma-separated video IDs")
    parser.add_argument("--callback-url", help="Optional webhook callback URL")
    parser.add_argument("--api-key", help="Mosaic API key (or use MOSAIC_API_KEY env var)")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    args = parser.parse_args()

    api_key = resolve_api_key(args.api_key)
    headers = {"Authorization": f"Bearer {api_key}"}
    video_ids = parse_ids(args.video_ids)
    if not video_ids:
        print("❌ Provide at least one video id via --video-ids")
        sys.exit(1)

    print("\n🚀 Starting agent run...")
    run_id = run_agent(args.base_url, headers, args.agent_id, video_ids, args.callback_url)
    print(f"✅ Run started\nrun_id {run_id}")


if __name__ == "__main__":
    main()


