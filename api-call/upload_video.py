#!/usr/bin/env python3
"""
Upload a video file to Mosaic using the 3-step process with Google Cloud
Signed Form Upload (multipart/form-data):
  1) GET /videos/get_upload_url (returns upload_url, fields, video_id)
  2) POST multipart/form-data to upload_url with signed form fields and file
  3) POST /videos/finalize_upload

Usage:
  python upload_video_fixed.py --file /path/to/video.mp4 [--content-type video/mp4]
"""

import argparse
import json
import os
import mimetypes
import sys
from typing import Optional, Tuple, Dict, Any

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


def guess_content_type(file_path: str, explicit: Optional[str]) -> str:
    if explicit:
        return explicit
    ctype, _ = mimetypes.guess_type(file_path)
    return ctype or "application/octet-stream"


def get_upload_url(base_url: str, api_key: str, filename: str, content_type: str) -> Tuple[str, str, Dict[str, Any]]:
    # Use POST with JSON body and X-API-Key header (and keep Authorization for compatibility)
    req_headers = {
        "X-API-Key": api_key,
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    payload = {"filename": filename, "content_type": content_type}
    resp = requests.post(
        f"{base_url}/videos/get_upload_url",
        headers=req_headers,
        json=payload,
        timeout=30,
    )
    try:
        resp.raise_for_status()
    except requests.HTTPError as e:
        print(f"❌ Failed to get upload URL: {e}\n{resp.text}")
        sys.exit(1)
    data = resp.json()
    # Expect fields for signed form upload
    if "fields" not in data or "upload_url" not in data or "video_id" not in data:
        print(f"❌ Unexpected response from get_upload_url: {data}")
        sys.exit(1)
    return data["video_id"], data["upload_url"], data["fields"]


def gcs_form_upload(upload_url: str, fields: Dict[str, Any], file_path: str) -> None:
    """Perform a signed form POST (multipart/form-data) to GCS.

    fields must be sent as form fields and the file must be in the files param.
    The file part should come after fields (requests ensures correct multipart ordering).
    """
    # Get file size for logging
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    print(f"   File size: {file_size_mb:.2f} MB")
    
    with open(file_path, "rb") as f:
        # Note: using 'file' field name per convention
        resp = requests.post(
            upload_url,
            data=fields,
            files={"file": (os.path.basename(file_path), f)},
            timeout=1800,
        )
    
    # IMPORTANT: Check for success FIRST!
    if resp.status_code == 204:
        # Success! GCS returns 204 No Content for successful uploads
        print("   ✅ Upload successful (204 No Content)")
        return
    elif resp.status_code == 400:
        # 400 indicates policy violation (e.g., file > 5GB)
        print(f"❌ Upload rejected by GCS: File exceeds 5GB size limit")
        print(f"   Response: {resp.text}")
        raise Exception("File > 5GB! Rejected by GCS policy")
    else:
        # Any other status code is an unexpected error
        print(f"❌ Upload failed with status {resp.status_code}")
        print(f"   Response: {resp.text}")
        raise Exception(f"Upload failed: HTTP {resp.status_code}")


def finalize_upload(base_url: str, headers: dict, video_id: str) -> None:
    payload = {"video_id": video_id}
    resp = requests.post(
        f"{base_url}/videos/finalize_upload",
        headers={**headers, "Content-Type": "application/json"},
        json=payload,
        timeout=30,
    )
    
    # Check for specific error codes
    if resp.status_code == 200:
        # Success!
        return
    elif resp.status_code == 413:
        # 413 indicates file too large or duration too long
        error_detail = resp.json().get("detail", "Limit exceeded")
        if "duration" in error_detail.lower():
            print(f"❌ Video duration exceeds 90 minute limit")
            raise Exception("Video > 90 min!")
        else:
            print(f"❌ Video exceeds limits: {error_detail}")
            raise Exception(f"Video exceeds limits: {error_detail}")
    else:
        # Other errors
        print(f"❌ Failed to finalize upload: HTTP {resp.status_code}")
        print(f"   Response: {resp.text}")
        raise Exception(f"Finalization failed: HTTP {resp.status_code}")


def main():
    parser = argparse.ArgumentParser(description="Upload a video to Mosaic (signed form upload)")
    parser.add_argument("--file", required=True, help="Path to local video file")
    parser.add_argument("--content-type", help="Explicit Content-Type for the file (e.g., video/mp4)")
    parser.add_argument("--api-key", help="Mosaic API key (or use MOSAIC_API_KEY env var)")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    args = parser.parse_args()

    if not os.path.isfile(args.file):
        print(f"❌ File not found: {args.file}")
        sys.exit(1)

    api_key = resolve_api_key(args.api_key)
    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        print("\n📤 Step 1: Getting upload URL...")
        filename = os.path.basename(args.file)
        content_type = guess_content_type(args.file, args.content_type)
        video_id, upload_url, fields = get_upload_url(args.base_url, api_key, filename, content_type)
        print(f"   ✅ Got video_id: {video_id}")
        print(f"   Method: POST with policy (5GB size limit enforced)")

        print("\n⬆️  Step 2: Uploading via signed form...")
        gcs_form_upload(upload_url, fields, args.file)

        print("\n✅ Step 3: Finalizing upload...")
        finalize_upload(args.base_url, headers, video_id)
        print("   ✅ Finalization complete")

        print(f"\n🎉 Upload complete!")
        print(f"   Video ID: {video_id}")
        print(f"   All checks passed: Size ≤ 5GB, Duration ≤ 90min")
        
    except Exception as e:
        print(f"\n❌ Upload failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
