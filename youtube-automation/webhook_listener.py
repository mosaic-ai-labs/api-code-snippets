#!/usr/bin/env python3
"""
Webhook listener for Mosaic agent callbacks.

This script starts a local web server to receive and display webhook
notifications from Mosaic agents and triggers.

Usage:
    python webhook_listener.py [--port PORT] [--ngrok]
    
Example:
    # Basic usage
    python webhook_listener.py
    
    # With custom port
    python webhook_listener.py --port 8080
    
    # With ngrok tunnel (requires ngrok installed)
    python webhook_listener.py --ngrok
"""

import argparse
import json
import logging
import os
import sys
import subprocess
import time
import threading
from datetime import datetime
from typing import Dict, Any, Optional
from flask import Flask, request, jsonify
from urllib.parse import urlparse


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)

# Store webhook history
webhook_history = []
MAX_HISTORY = 100  # Keep last 100 webhooks


class WebhookHandler:
    """Handles and formats webhook payloads."""
    
    @staticmethod
    def format_timestamp(timestamp_str: Optional[str]) -> str:
        """Format ISO timestamp to readable format."""
        if not timestamp_str:
            return "N/A"
        try:
            dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d %H:%M:%S UTC')
        except:
            return timestamp_str
    
    @staticmethod
    def format_webhook(data: Dict[str, Any]) -> str:
        """Format webhook data for console output."""
        output = []
        output.append("\n" + "="*80)
        output.append("🔔 WEBHOOK RECEIVED")
        output.append("="*80)
        
        # Basic info
        flag = data.get('flag', 'UNKNOWN')
        output.append(f"\n📌 Event Type: {flag}")
        output.append(f"🤖 Agent ID: {data.get('agent_id', 'N/A')}")
        output.append(f"🎯 Run ID: {data.get('run_id', 'N/A')}")
        output.append(f"📊 Status: {data.get('status', 'N/A')}")
        
        # Handle different event types
        if flag == 'RUN_STARTED':
            output.append("\n🚀 AGENT RUN STARTED")
            
            # Input videos
            inputs = data.get('inputs', [])
            if inputs:
                output.append(f"\n📹 Input Videos ({len(inputs)}):")
                for idx, inp in enumerate(inputs, 1):
                    output.append(f"   {idx}. Video ID: {inp.get('video_id', 'N/A')}")
                    if inp.get('video_url'):
                        output.append(f"      URL: {inp['video_url']}")
                    if inp.get('thumbnail_url'):
                        output.append(f"      Thumbnail: {inp['thumbnail_url']}")
            
            # Trigger info
            triggered_by = data.get('triggered_by')
            if triggered_by:
                output.append("\n⚡ TRIGGERED BY:")
                output.append(f"   Type: {triggered_by.get('type', 'N/A')}")
                
                if triggered_by.get('type') == 'youtube':
                    youtube_info = triggered_by.get('youtube', {})
                    output.append(f"   📺 YouTube Video:")
                    output.append(f"      Title: {youtube_info.get('title', 'N/A')}")
                    output.append(f"      Channel: {youtube_info.get('channel', 'N/A')}")
                    output.append(f"      Video ID: {youtube_info.get('id', 'N/A')}")
                    output.append(f"      URL: {youtube_info.get('url', 'N/A')}")
        
        elif flag == 'OUTPUTS_FINISHED':
            output.append("\n✨ OUTPUTS COMPLETED")
            
            outputs = data.get('output', [])  # Note: 'output' not 'outputs' for this event
            if outputs:
                output.append(f"\n🎬 Completed Outputs ({len(outputs)}):")
                for idx, out in enumerate(outputs, 1):
                    output.append(f"   {idx}. Video URL: {out.get('video_url', 'N/A')}")
                    if out.get('thumbnail_url'):
                        output.append(f"      Thumbnail: {out['thumbnail_url']}")
                    if out.get('completed_at'):
                        output.append(f"      Completed: {WebhookHandler.format_timestamp(out['completed_at'])}")
        
        elif flag == 'RUN_FINISHED':
            output.append("\n🏁 AGENT RUN FINISHED")
            
            # Inputs
            inputs = data.get('inputs', [])
            if inputs:
                output.append(f"\n📹 Processed Inputs ({len(inputs)}):")
                for idx, inp in enumerate(inputs, 1):
                    output.append(f"   {idx}. File: {inp.get('file_name', 'N/A')}")
                    if inp.get('file_url'):
                        output.append(f"      URL: {inp['file_url']}")
                    if inp.get('uploaded_at'):
                        output.append(f"      Uploaded: {WebhookHandler.format_timestamp(inp['uploaded_at'])}")
            
            # Outputs
            outputs = data.get('outputs', [])
            if outputs:
                output.append(f"\n🎬 Final Outputs ({len(outputs)}):")
                for idx, out in enumerate(outputs, 1):
                    output.append(f"   {idx}. Video URL: {out.get('video_url', 'N/A')}")
                    if out.get('thumbnail_url'):
                        output.append(f"      Thumbnail: {out['thumbnail_url']}")
                    if out.get('completed_at'):
                        output.append(f"      Completed: {WebhookHandler.format_timestamp(out['completed_at'])}")
            
            # Trigger info for finished runs
            triggered_by = data.get('triggered_by')
            if triggered_by:
                output.append("\n⚡ TRIGGERED BY:")
                output.append(f"   Type: {triggered_by.get('type', 'N/A')}")
                if triggered_by.get('type') == 'youtube':
                    output.append(f"   📺 YouTube:")
                    output.append(f"      Channel: {triggered_by.get('channel_name', 'N/A')} ({triggered_by.get('channel_id', 'N/A')})")
                    output.append(f"      Video: {triggered_by.get('video_title', 'N/A')}")
                    output.append(f"      Video ID: {triggered_by.get('video_id', 'N/A')}")
                    output.append(f"      URL: {triggered_by.get('video_url', 'N/A')}")
                    if triggered_by.get('triggered_at'):
                        output.append(f"      Triggered: {WebhookHandler.format_timestamp(triggered_by['triggered_at'])}")
            
            # Final status
            status = data.get('status', 'unknown')
            if status == 'completed':
                output.append("\n✅ Run completed successfully!")
            elif status == 'failed':
                output.append("\n❌ Run failed!")
        
        output.append("\n" + "="*80)
        return "\n".join(output)


@app.route('/', methods=['GET'])
def home():
    """Home page showing webhook listener status."""
    return jsonify({
        'status': 'running',
        'service': 'Mosaic Webhook Listener',
        'endpoints': {
            'webhook': '/webhook',
            'webhook_with_token': '/webhook/<token>',
            'history': '/history',
            'health': '/health'
        },
        'webhooks_received': len(webhook_history)
    })


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({'status': 'healthy'}), 200


@app.route('/history', methods=['GET'])
def history():
    """Get webhook history."""
    return jsonify({
        'total': len(webhook_history),
        'history': webhook_history[-10:]  # Last 10 webhooks
    })


@app.route('/webhook', methods=['POST'])
@app.route('/webhook/<path:token>', methods=['POST'])
def webhook(token=None):
    """
    Main webhook endpoint.
    Accepts webhooks at /webhook or /webhook/{any-path}
    """
    try:
        # Get webhook data
        data = request.get_json()
        
        if not data:
            logger.warning("Received webhook with no JSON data")
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Get headers
        headers = dict(request.headers)
        webhook_secret = headers.get('X-Mosaic-Signature')
        
        # Store in history
        webhook_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'path': request.path,
            'token': token,
            'webhook_secret': webhook_secret,
            'data': data
        }
        
        webhook_history.append(webhook_entry)
        if len(webhook_history) > MAX_HISTORY:
            webhook_history.pop(0)
        
        # Format and display webhook
        formatted = WebhookHandler.format_webhook(data)
        print(formatted)
        
        # Log additional info
        logger.info(f"Webhook received at: {request.path}")
        if token:
            logger.info(f"Token/Path: {token}")
        if webhook_secret:
            logger.info(f"Webhook Secret: {webhook_secret[:10]}..." if len(webhook_secret) > 10 else webhook_secret)
        
        # Log raw JSON for debugging
        if os.environ.get('DEBUG') == '1':
            logger.debug("Raw webhook data:")
            print(json.dumps(data, indent=2))
        
        # Return success response
        return jsonify({'received': True, 'message': 'Webhook processed successfully'}), 200
        
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


class NgrokManager:
    """Manages ngrok tunnel for local development."""
    
    @staticmethod
    def check_ngrok_installed() -> bool:
        """Check if ngrok is installed."""
        try:
            result = subprocess.run(['ngrok', 'version'], capture_output=True, text=True)
            return result.returncode == 0
        except FileNotFoundError:
            return False
    
    @staticmethod
    def start_tunnel(port: int) -> Optional[str]:
        """Start ngrok tunnel and return public URL."""
        if not NgrokManager.check_ngrok_installed():
            logger.warning("ngrok is not installed. Install it from https://ngrok.com")
            return None
        
        try:
            # Start ngrok in a subprocess
            process = subprocess.Popen(
                ['ngrok', 'http', str(port), '--log', 'stdout'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Give ngrok time to start
            time.sleep(2)
            
            # Get tunnel info using ngrok API
            import requests
            try:
                response = requests.get('http://127.0.0.1:4040/api/tunnels')
                tunnels = response.json()
                if tunnels['tunnels']:
                    public_url = tunnels['tunnels'][0]['public_url']
                    # Prefer HTTPS URL
                    for tunnel in tunnels['tunnels']:
                        if tunnel['public_url'].startswith('https'):
                            public_url = tunnel['public_url']
                            break
                    return public_url
            except:
                logger.warning("Could not retrieve ngrok URL. Check http://127.0.0.1:4040")
                return None
                
        except Exception as e:
            logger.error(f"Failed to start ngrok: {e}")
            return None


def main():
    parser = argparse.ArgumentParser(
        description='Webhook listener for Mosaic agent callbacks',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Start listener on default port (3000)
  python webhook_listener.py
  
  # Use custom port
  python webhook_listener.py --port 8080
  
  # Start with ngrok tunnel (requires ngrok installed)
  python webhook_listener.py --ngrok
  
  # Enable debug mode for raw JSON output
  DEBUG=1 python webhook_listener.py
        '''
    )
    
    parser.add_argument(
        '--port',
        type=int,
        default=3000,
        help='Port to listen on (default: 3000)'
    )
    
    parser.add_argument(
        '--host',
        default='0.0.0.0',
        help='Host to bind to (default: 0.0.0.0)'
    )
    
    parser.add_argument(
        '--ngrok',
        action='store_true',
        help='Start ngrok tunnel for public URL'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable Flask debug mode'
    )
    
    args = parser.parse_args()
    
    # Set debug env if flag is set
    if args.debug:
        os.environ['DEBUG'] = '1'
    
    print("\n" + "="*60)
    print("🚀 MOSAIC WEBHOOK LISTENER")
    print("="*60)
    
    # Start ngrok if requested
    ngrok_url = None
    if args.ngrok:
        print(f"\n🌐 Starting ngrok tunnel...")
        ngrok_url = NgrokManager.start_tunnel(args.port)
        if ngrok_url:
            print(f"✅ Ngrok tunnel started!")
            print(f"   Public URL: {ngrok_url}")
            print(f"   Webhook URL: {ngrok_url}/webhook")
            print(f"   With token: {ngrok_url}/webhook/your-secret-token")
            print(f"\n💡 Use this URL in add_triggers.py:")
            print(f"   python add_triggers.py --agent-id YOUR_ID --channels CHANNEL_ID --webhook {ngrok_url}/webhook")
        else:
            print("⚠️  Could not start ngrok tunnel. Continuing with local server only.")
    
    # Display local URLs
    print(f"\n📡 Starting webhook listener...")
    print(f"   Local URL: http://localhost:{args.port}")
    print(f"   Network URL: http://{args.host}:{args.port}")
    print(f"\n🔗 Endpoints:")
    print(f"   Webhook: http://localhost:{args.port}/webhook")
    print(f"   With token: http://localhost:{args.port}/webhook/your-secret-token")
    print(f"   History: http://localhost:{args.port}/history")
    print(f"   Health: http://localhost:{args.port}/health")
    
    print("\n⏳ Waiting for webhooks... (Press Ctrl+C to stop)")
    print("="*60 + "\n")
    
    try:
        # Run Flask app
        app.run(
            host=args.host,
            port=args.port,
            debug=args.debug,
            use_reloader=False  # Disable reloader to avoid duplicate messages
        )
    except KeyboardInterrupt:
        print("\n\n🛑 Webhook listener stopped")
        print(f"📊 Total webhooks received: {len(webhook_history)}")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Failed to start webhook listener: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
