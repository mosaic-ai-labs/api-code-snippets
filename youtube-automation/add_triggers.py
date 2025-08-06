#!/usr/bin/env python3
"""
Script to add YouTube channel triggers to a Mosaic agent.

Usage:
    python add_triggers.py --agent-id <AGENT_ID> --api-key <API_KEY> --channels <CHANNEL_IDS>
    
Example:
    python add_triggers.py --agent-id abc123 --api-key mk_your_key --channels UCxxxxxx,@channelname --webhook https://your-app.com/webhook
"""

import argparse
import requests
import json
import sys
from typing import List, Optional
from urllib.parse import urlparse


class MosaicTriggerManager:
    """Manages YouTube triggers for Mosaic agents."""
    
    def __init__(self, api_key: str, base_url: str = "https://api.mosaic.so"):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def add_youtube_channels(
        self, 
        agent_id: str, 
        channels: List[str], 
        callback_url: Optional[str] = None
    ) -> dict:
        """
        Add YouTube channels to an agent's trigger.
        
        Args:
            agent_id: The ID of the agent
            channels: List of YouTube channel IDs or URLs
            callback_url: Optional webhook URL for notifications
            
        Returns:
            Response from the API
        """
        endpoint = f"{self.base_url}/agent/{agent_id}/triggers/add_youtube_channels"
        
        payload = {
            "youtube_channels": channels
        }
        
        if callback_url is not None:
            payload["trigger_callback_url"] = callback_url
        
        print(f"\n📡 Adding YouTube channels to agent {agent_id}...")
        print(f"   Channels: {', '.join(channels)}")
        if callback_url:
            print(f"   Webhook URL: {callback_url}")
        
        try:
            response = requests.post(
                endpoint,
                headers=self.headers,
                json=payload
            )
            response.raise_for_status()
            return response.json() if response.text else {"status": "ok"}
        except requests.exceptions.HTTPError as e:
            print(f"\n❌ Error adding channels: {e}")
            if e.response.text:
                print(f"   Response: {e.response.text}")
            raise
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
            raise
    
    def get_triggers(self, agent_id: str) -> Optional[dict]:
        """
        Get the triggers configured for an agent.
        
        Args:
            agent_id: The ID of the agent
            
        Returns:
            Trigger configuration or None if no triggers exist
        """
        endpoint = f"{self.base_url}/agent/{agent_id}/triggers"
        
        print(f"\n🔍 Fetching triggers for agent {agent_id}...")
        
        try:
            response = requests.get(endpoint, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            print(f"\n❌ Error fetching triggers: {e}")
            if e.response.text:
                print(f"   Response: {e.response.text}")
            raise
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
            raise
    
    def validate_webhook_url(self, url: str) -> bool:
        """
        Validate that a webhook URL is properly formatted.
        
        Args:
            url: The webhook URL to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            result = urlparse(url)
            return all([result.scheme in ['http', 'https'], result.netloc])
        except:
            return False


def parse_channels(channels_str: str) -> List[str]:
    """
    Parse comma-separated channel IDs/URLs.
    
    Args:
        channels_str: Comma-separated string of channels
        
    Returns:
        List of channel IDs/URLs
    """
    channels = [ch.strip() for ch in channels_str.split(',') if ch.strip()]
    
    # Validate channel formats
    for channel in channels:
        if not channel:
            continue
        
        # Check if it's a channel ID (starts with UC and has 24 chars)
        if channel.startswith('UC') and len(channel) == 24:
            continue
        
        # Check if it's a valid YouTube URL
        if 'youtube.com' in channel or 'youtu.be' in channel:
            continue
        
        # Check if it's a handle (starts with @)
        if channel.startswith('@'):
            continue
        
        print(f"⚠️  Warning: '{channel}' may not be a valid channel ID or URL")
    
    return channels


def main():
    parser = argparse.ArgumentParser(
        description='Add YouTube channel triggers to a Mosaic agent',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Add a single channel
  python add_triggers.py --agent-id abc123 --api-key mk_xxx --channels UCxxxxxxxxxxxxxx
  
  # Add multiple channels with webhook
  python add_triggers.py --agent-id abc123 --api-key mk_xxx \\
    --channels "UCxxxxxx,@mkbhd,https://youtube.com/@channel" \\
    --webhook https://your-app.com/webhook
  
  # Use environment variable for API key
  export MOSAIC_API_KEY=mk_xxx
  python add_triggers.py --agent-id abc123 --channels UCxxxxxx
        '''
    )
    
    parser.add_argument(
        '--agent-id',
        required=True,
        help='The ID of the Mosaic agent'
    )
    
    parser.add_argument(
        '--api-key',
        help='Mosaic API key (or set MOSAIC_API_KEY env var)'
    )
    
    parser.add_argument(
        '--channels',
        required=True,
        help='Comma-separated list of YouTube channel IDs, handles (@name), or URLs'
    )
    
    parser.add_argument(
        '--webhook',
        help='Optional webhook URL for trigger notifications'
    )
    
    parser.add_argument(
        '--base-url',
        default='https://api.mosaic.so',
        help='Base URL for Mosaic API (default: https://api.mosaic.so)'
    )
    
    parser.add_argument(
        '--remove-webhook',
        action='store_true',
        help='Remove the webhook URL from the trigger (sets it to null)'
    )
    
    args = parser.parse_args()
    
    # Get API key from args or environment
    import os
    api_key = args.api_key or os.environ.get('MOSAIC_API_KEY')
    
    if not api_key:
        print("❌ Error: API key is required. Use --api-key or set MOSAIC_API_KEY environment variable")
        sys.exit(1)
    
    if not api_key.startswith('mk_'):
        print("❌ Error: Invalid API key format. Mosaic API keys should start with 'mk_'")
        sys.exit(1)
    
    # Parse channels
    channels = parse_channels(args.channels)
    
    if not channels:
        print("❌ Error: No valid channels provided")
        sys.exit(1)
    
    # Handle webhook URL
    webhook_url = None
    if args.remove_webhook:
        webhook_url = None
        print("📢 Will remove webhook URL from trigger")
    elif args.webhook:
        webhook_url = args.webhook
        # Validate webhook URL
        manager = MosaicTriggerManager(api_key, args.base_url)
        if not manager.validate_webhook_url(webhook_url):
            print(f"❌ Error: Invalid webhook URL format: {webhook_url}")
            sys.exit(1)
    
    # Initialize manager
    manager = MosaicTriggerManager(api_key, args.base_url)
    
    try:
        # Add channels to trigger
        result = manager.add_youtube_channels(
            args.agent_id,
            channels,
            webhook_url
        )
        
        print("\n✅ Successfully added YouTube channels to trigger!")
        if result and result != {"status": "ok"}:
            print(f"   Response: {json.dumps(result, indent=2)}")
        
        # Verify by fetching triggers
        print("\n" + "="*60)
        triggers = manager.get_triggers(args.agent_id)
        
        if triggers:
            print("\n✅ Trigger configuration verified!")
            
            # Display trigger info
            if isinstance(triggers, dict):
                # Single trigger format
                if triggers.get('type') == 'youtube':
                    youtube_channels = triggers.get('youtube_channels', [])
                    callback_url = triggers.get('callback_url')
                    
                    print(f"\n📺 YouTube Trigger:")
                    print(f"   ID: {triggers.get('id')}")
                    print(f"   Channels monitored: {len(youtube_channels)}")
                    for channel in youtube_channels:
                        print(f"     • {channel}")
                    
                    if callback_url:
                        print(f"   Webhook URL: {callback_url}")
                    else:
                        print(f"   Webhook URL: (not configured)")
            elif isinstance(triggers, list):
                # Multiple triggers format
                for trigger in triggers:
                    if trigger.get('type') == 'youtube':
                        youtube_channels = trigger.get('youtube_channels', [])
                        callback_url = trigger.get('callback_url')
                        
                        print(f"\n📺 YouTube Trigger:")
                        print(f"   ID: {trigger.get('id')}")
                        print(f"   Channels monitored: {len(youtube_channels)}")
                        for channel in youtube_channels:
                            print(f"     • {channel}")
                        
                        if callback_url:
                            print(f"   Webhook URL: {callback_url}")
                        else:
                            print(f"   Webhook URL: (not configured)")
        else:
            print("\n⚠️  No triggers found for this agent")
        
        print("\n" + "="*60)
        print("\n🎉 Setup complete! Your agent will now monitor the specified YouTube channels.")
        print("   New videos will automatically trigger agent runs.")
        
        if webhook_url:
            print(f"\n💡 Tip: Test your webhook endpoint with webhook_listener.py")
            print(f"   python webhook_listener.py --port 3000")
        
    except Exception as e:
        print(f"\n❌ Failed to add triggers: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
