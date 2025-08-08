#!/usr/bin/env python3
"""
Webhook listener for Mosaic agent run callbacks.

Usage:
  python webhook_listener.py [--port 3000] [--host 0.0.0.0] [--ngrok] [--debug]

Environment:
  MOSAIC_WEBHOOK_SECRET=your_secret   # Optional: validate X-Mosaic-Signature
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import requests
from flask import Flask, jsonify, request


logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

webhook_history = []
MAX_HISTORY = 100


def format_ts(ts: Optional[str]) -> str:
    if not ts:
        return "N/A"
    try:
        return datetime.fromisoformat(ts.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S UTC')
    except Exception:
        return ts


def format_event(data: Dict[str, Any]) -> str:
    flag = data.get('flag', 'UNKNOWN')
    lines = ["\n" + "=" * 80, f"🔔 {flag}", "=" * 80]

    lines.append(f"agent: {data.get('agent_id')}")
    lines.append(f"run:   {data.get('run_id')}")
    lines.append(f"status:{data.get('status')}")

    if flag == 'RUN_STARTED':
        inputs = data.get('inputs', [])
        if inputs:
            lines.append(f"inputs: {len(inputs)}")
            for i, inp in enumerate(inputs, 1):
                lines.append(f"  {i}. {inp.get('video_url') or inp.get('file_url')}")

    if flag == 'OUTPUTS_FINISHED':
        outputs = data.get('output', [])
        if outputs:
            lines.append(f"outputs: {len(outputs)}")
            for i, out in enumerate(outputs, 1):
                lines.append(f"  {i}. {out.get('video_url')} (thumb: {out.get('thumbnail_url')})")

    if flag == 'RUN_FINISHED':
        outputs = data.get('outputs', [])
        if outputs:
            lines.append(f"outputs: {len(outputs)}")
            for i, out in enumerate(outputs, 1):
                lines.append(f"  {i}. {out.get('video_url')} (thumb: {out.get('thumbnail_url')})")

    lines.append("\n" + "=" * 80)
    return "\n".join(lines)


@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy"}), 200


@app.route('/history', methods=['GET'])
def history():
    return jsonify({"total": len(webhook_history), "history": webhook_history[-10:]})


@app.route('/', methods=['GET'])
def home():
    return jsonify({
        'status': 'running',
        'service': 'Mosaic Webhook Listener',
        'endpoints': {
            'webhook': '/webhook',
            'webhook_with_token': '/webhook/<token>',
            'webhooks_mosaic': '/webhooks/mosaic',
            'webhooks_mosaic_with_token': '/webhooks/mosaic/<token>',
            'history': '/history',
            'health': '/health',
        },
        'webhooks_received': len(webhook_history)
    })


@app.route('/webhooks/mosaic', methods=['POST'])
@app.route('/webhooks/mosaic/<path:token>', methods=['POST'])
def handle_webhook(token: Optional[str] = None):
    try:
        # Simple webhook secret validation
        expected_secret = app.config.get('WEBHOOK_SECRET') or os.environ.get('MOSAIC_WEBHOOK_SECRET')
        received_secret = request.headers.get('X-Mosaic-Signature')
        
        secret_valid = True
        if expected_secret:
            if not received_secret:
                logger.warning("Missing X-Mosaic-Signature header")
                print("\n⚠️  WEBHOOK SECRET VALIDATION FAILED")
                print(f"   Expected header: X-Mosaic-Signature")
                print(f"   Expected value:  {expected_secret}")
                print(f"   Received:        (header not present)")
                secret_valid = False
            elif received_secret != expected_secret:
                logger.warning("Invalid webhook secret")
                print("\n⚠️  WEBHOOK SECRET VALIDATION FAILED")
                print(f"   Expected: {expected_secret}")
                print(f"   Received: {received_secret}")
                print(f"   Match:    ❌ MISMATCH")
                secret_valid = False

        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON"}), 400

        entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'path': request.path,
            'token': token,
            'data': data,
        }
        webhook_history.append(entry)
        if len(webhook_history) > MAX_HISTORY:
            webhook_history.pop(0)

        print(format_event(data))
        # Also print raw JSON for debugging/inspection
        try:
            print(json.dumps(data, indent=2))
        except Exception:
            pass
        
        # Return appropriate response based on validation
        if not secret_valid:
            print("\n❌ Webhook rejected due to invalid secret (still displayed above for debugging)")
            return jsonify({"error": "Invalid webhook secret", "data": data}), 401
        
        # Echo raw payload back in response for convenience
        return jsonify({"received": True, "data": data}), 200
    except Exception as e:
        logger.exception("Webhook processing error")
        return jsonify({"error": str(e)}), 500


@app.route('/', methods=['POST'])
@app.route('/webhook', methods=['POST'])
@app.route('/webhook/<path:token>', methods=['POST'])
def root_webhook(token: Optional[str] = None):
    """Allow POST / and /webhook[/<token>] as webhook endpoints."""
    return handle_webhook(token)


def ngrok_available() -> bool:
    try:
        out = subprocess.run(['ngrok', 'version'], capture_output=True)
        return out.returncode == 0
    except FileNotFoundError:
        return False


def start_ngrok(port: int) -> Optional[str]:
    if not ngrok_available():
        logger.warning("ngrok not installed. Install from https://ngrok.com")
        return None
    proc = subprocess.Popen(['ngrok', 'http', str(port), '--log', 'stdout'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    time.sleep(2)
    try:
        r = requests.get('http://127.0.0.1:4040/api/tunnels', timeout=5)
        tunnels = r.json().get('tunnels', [])
        if not tunnels:
            return None
        https_url = None
        for t in tunnels:
            if t.get('public_url', '').startswith('https'):
                https_url = t['public_url']
                break
        return https_url or tunnels[0].get('public_url')
    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser(description="Webhook listener for Mosaic agent runs")
    parser.add_argument('--port', type=int, default=3000)
    parser.add_argument('--host', default='0.0.0.0')
    parser.add_argument('--ngrok', action='store_true')
    parser.add_argument('--debug', action='store_true')
    parser.add_argument('--webhook-secret', help='Secret to validate X-Mosaic-Signature header (overrides MOSAIC_WEBHOOK_SECRET env var)')
    args = parser.parse_args()

    if args.ngrok:
        print("\n🌐 Starting ngrok tunnel...")
        public = start_ngrok(args.port)
        if public:
            print(f"✅ Public URL: {public}")
            print(f"   Webhook:   {public}/webhooks/mosaic")
            print(f"   With token:{public}/webhooks/mosaic/your-token")
        else:
            print("⚠️  Could not start ngrok. Continuing locally.")

    print("\n📡 Webhook listener starting...")
    print(f"   Local:   http://localhost:{args.port}")
    print(f"   Health:  http://localhost:{args.port}/health")
    print(f"   History: http://localhost:{args.port}/history")
    print(f"   Webhook: http://localhost:{args.port}/webhooks/mosaic")
    print(f"   Alt:     http://localhost:{args.port}/webhook")
    
    # Store webhook secret from flag or env
    app.config['WEBHOOK_SECRET'] = args.webhook_secret
    
    if args.webhook_secret or os.environ.get('MOSAIC_WEBHOOK_SECRET'):
        print("\n🔐 Webhook secret validation: ENABLED")
        print("   Expecting X-Mosaic-Signature header to match secret")
        if args.webhook_secret:
            print("   Source: --webhook-secret flag")
        else:
            print("   Source: MOSAIC_WEBHOOK_SECRET env var")
    else:
        print("\n🔓 Webhook secret validation: DISABLED")
        print("   Set --webhook-secret flag or MOSAIC_WEBHOOK_SECRET env var to enable")

    app.run(host=args.host, port=args.port, debug=args.debug, use_reloader=False)


if __name__ == '__main__':
    main()


