#!/usr/bin/env python3
"""
Upload a video file to Mosaic using the NEW 3-step process with upfront metadata validation:
  1) Extract video metadata locally using moviepy
  2) POST /videos/get_upload_url with metadata (immediate validation)
  3) Upload video using resumable upload method
  4) POST /videos/finalize_upload

Usage:
  python upload_video.py --file /path/to/video.mp4 [--api-key YOUR_KEY]
"""

import argparse
import json
import os
import mimetypes
import sys
from typing import Optional, Tuple, Dict, Any

import requests
from moviepy.editor import VideoFileClip


DEFAULT_BASE_URL = "https://api.mosaic.so"


def resolve_api_key(explicit_key: Optional[str]) -> str:
    """Get API key from argument or environment variable."""
    api_key = explicit_key or os.environ.get("MOSAIC_API_KEY")
    if not api_key:
        print("❌ Error: API key required. Use --api-key or set MOSAIC_API_KEY")
        sys.exit(1)
    if not api_key.startswith("mk_"):
        print("❌ Error: Invalid API key format (must start with 'mk_')")
        sys.exit(1)
    return api_key


def get_video_metadata(file_path: str) -> Dict[str, Any]:
    """Extract metadata from video file using moviepy."""
    try:
        print("📊 Extracting video metadata...")
        with VideoFileClip(file_path) as clip:
            metadata = {
                "width": clip.w,
                "height": clip.h, 
                "duration_ms": int(clip.duration * 1000),
                "file_size": os.path.getsize(file_path)
            }
            
        print(f"   ✅ Resolution: {metadata['width']}x{metadata['height']}")
        print(f"   ✅ Duration: {metadata['duration_ms']/1000:.1f}s")
        print(f"   ✅ File size: {metadata['file_size']/(1024**2):.1f}MB")
        return metadata
        
    except Exception as e:
        print(f"   ❌ Failed to extract video metadata: {e}")
        print("   💡 Make sure moviepy is installed: pip install moviepy")
        sys.exit(1)


def determine_content_type(file_path: str, explicit: Optional[str]) -> str:
    """Determine content type from file extension or explicit parameter."""
    if explicit:
        return explicit
        
    content_type_map = {
        '.mp4': 'video/mp4',
        '.mov': 'video/quicktime',
        '.avi': 'video/x-msvideo',
        '.webm': 'video/webm',
        '.mkv': 'video/x-matroska',
        '.m4v': 'video/x-m4v'
    }
    
    file_ext = os.path.splitext(file_path)[1].lower()
    return content_type_map.get(file_ext, 'video/mp4')


def get_upload_url_with_metadata(
    base_url: str, 
    api_key: str, 
    filename: str, 
    content_type: str,
    metadata: Dict[str, Any]
) -> Tuple[str, str, str]:
    """Get upload URL with immediate metadata validation."""
    print("📤 Step 1: Getting upload URL with validation...")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "filename": filename,
        "content_type": content_type,
        "file_size": metadata["file_size"],
        "width": metadata["width"], 
        "height": metadata["height"],
        "duration_ms": metadata["duration_ms"]
    }
    
    try:
        resp = requests.post(
            f"{base_url}/videos/get_upload_url",
            headers=headers,
            json=payload,
            timeout=30,
        )
        
        # Handle immediate validation errors
        if resp.status_code == 413:
            error_data = resp.json()
            error_detail = error_data.get("detail", "File too large or too long")
            print(f"   ❌ File exceeds limits: {error_detail}")
            if "duration" in error_detail.lower():
                print("   📏 Maximum duration: 90 minutes")
            else:
                print("   📏 Maximum file size: 5GB")
            sys.exit(1)
            
        elif resp.status_code == 400:
            error_data = resp.json()
            error_detail = error_data.get("detail", "Invalid metadata")
            print(f"   ❌ Invalid metadata: {error_detail}")
            sys.exit(1)
            
        resp.raise_for_status()
        
    except requests.HTTPError as e:
        print(f"❌ Failed to get upload URL: {e}")
        if hasattr(resp, 'text'):
            print(f"   Response: {resp.text}")
        sys.exit(1)
    
    data = resp.json()
    
    # Validate response structure
    required_fields = ["video_id", "upload_url", "method"]
    for field in required_fields:
        if field not in data:
            print(f"❌ Missing field in response: {field}")
            print(f"   Response: {data}")
            sys.exit(1)
    
    video_id = data["video_id"]
    upload_url = data["upload_url"] 
    method = data["method"]
    
    print(f"   ✅ Got video_id: {video_id}")
    print(f"   ✅ Upload method: {method}")
    
    return video_id, upload_url, method


def upload_video_resumable(
    upload_url: str, 
    method: str,
    file_path: str, 
    content_type: str,
    file_size: int
) -> None:
    """Upload video using resumable upload method."""
    print("⬆️  Step 2: Uploading video...")
    
    file_size_mb = file_size / (1024 * 1024)
    print(f"   📦 Uploading {file_size_mb:.2f}MB...")
    
    with open(file_path, "rb") as f:
        if method.upper() == "POST":
            # Resumable upload with proper headers
            headers = {
                "x-goog-resumable": "start",
                "Content-Type": content_type,
                "Content-Length": str(file_size)
            }
            upload_response = requests.post(
                upload_url,
                headers=headers,
                data=f,
                timeout=1800  # 30 minute timeout for large files
            )
        else:
            # Fallback PUT method
            headers = {"Content-Type": content_type}
            upload_response = requests.put(
                upload_url,
                headers=headers,
                data=f,
                timeout=1800
            )
    
    # Check upload success
    if upload_response.status_code in [200, 201, 204]:
        print("   ✅ Upload successful")
    else:
        print(f"   ❌ Upload failed with status {upload_response.status_code}")
        if hasattr(upload_response, 'text'):
            print(f"   Response: {upload_response.text}")
        raise Exception(f"Upload failed: HTTP {upload_response.status_code}")


def finalize_upload(base_url: str, api_key: str, video_id: str) -> None:
    """Finalize upload."""
    print("✅ Step 3: Finalizing upload...")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {"video_id": video_id}
    
    try:
        resp = requests.post(
            f"{base_url}/videos/finalize_upload",
            headers=headers,
            json=payload,
            timeout=30,
        )
        
        if resp.status_code == 200:
            print("   ✅ Finalization complete")
            return
        else:
            error_data = resp.json() if resp.headers.get('content-type', '').startswith('application/json') else {}
            error_detail = error_data.get("detail", "Unknown error")
            print(f"   ❌ Finalization failed: {error_detail}")
            raise Exception(f"Finalization failed: HTTP {resp.status_code}")
            
    except requests.HTTPError as e:
        print(f"❌ Failed to finalize upload: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Upload a video to Mosaic with upfront metadata validation")
    parser.add_argument("--file", required=True, help="Path to local video file")
    parser.add_argument("--content-type", help="Explicit Content-Type for the file (e.g., video/mp4)")
    parser.add_argument("--api-key", help="Mosaic API key (or use MOSAIC_API_KEY env var)")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    args = parser.parse_args()

    # Validate file exists
    if not os.path.isfile(args.file):
        print(f"❌ File not found: {args.file}")
        sys.exit(1)

    api_key = resolve_api_key(args.api_key)
    filename = os.path.basename(args.file)
    content_type = determine_content_type(args.file, args.content_type)

    try:
        # Step 0: Extract metadata locally
        metadata = get_video_metadata(args.file)
        
        # Step 1: Get upload URL with validation  
        video_id, upload_url, method = get_upload_url_with_metadata(
            args.base_url, api_key, filename, content_type, metadata
        )
        
        # Step 2: Upload video
        upload_video_resumable(
            upload_url, method, args.file, content_type, metadata["file_size"]
        )
        
        # Step 3: Finalize upload
        finalize_upload(args.base_url, api_key, video_id)
        
        # Success!
        print(f"\n🎉 Upload complete!")
        print(f"Video ID: {video_id}")
        print(f"✅ All validation passed upfront - no surprises!")
        print(f"✅ Processing complete with upfront validation")
        
        # Output for script chaining
        print(f"\nvideo_id {video_id}")
        
    except KeyboardInterrupt:
        print(f"\n❌ Upload cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Upload failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()