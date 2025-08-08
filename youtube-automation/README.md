# YouTube Automation for Mosaic

Auto-trigger Mosaic agents when YouTube channels upload new videos.

## Setup
```bash
pip install -r requirements.txt
export MOSAIC_API_KEY=mk_your_api_key
```

## Quick Start

### 1. Test Your API Key
```bash
python test_auth.py
```

### 2. Add YouTube Triggers
```bash
# Single channel
python add_triggers.py --agent-id YOUR_AGENT_ID --channels UCxxxxxx

# Multiple channels with webhook
python add_triggers.py \
  --agent-id YOUR_AGENT_ID \
  --channels "UCxxxxxx,@mkbhd,https://youtube.com/@channel" \
  --webhook https://your-app.com/webhook

# Remove webhook
python add_triggers.py --agent-id YOUR_AGENT_ID --channels UCxxxxxx --remove-webhook
```

Accepted formats:
- Channel IDs: `UCxxxxxxxxxxxxxxxxxxxxxx`
- Handles: `@channelname`
- URLs: `https://youtube.com/@channel`

### 3. Webhook Listener (Optional)
```bash
# Basic
python webhook_listener.py

# With ngrok for public URL
python webhook_listener.py --ngrok --port 3000
```

## Complete Workflow
```bash
# 1. Test auth
python test_auth.py

# 2. Start webhook listener with ngrok
python webhook_listener.py --ngrok
# Note the public URL (e.g., https://abc123.ngrok.io)

# 3. Add triggers with webhook
python add_triggers.py \
  --agent-id YOUR_AGENT_ID \
  --channels "@YourFavoriteChannel" \
  --webhook https://abc123.ngrok.io/webhook

# 4. Wait for YouTube uploads to trigger your agent
# Watch webhook listener console for events
```

## Webhook Events

When a YouTube video triggers your agent:

1. **RUN_STARTED** - Agent begins processing
2. **OUTPUTS_FINISHED** - Individual outputs ready
3. **RUN_FINISHED** - Complete with all outputs

## API Reference

### Add YouTube Channels
```
POST /agent/{agent_id}/triggers/add_youtube_channels
{
  "youtube_channels": ["channel_id"],
  "trigger_callback_url": "optional_webhook_url"
}
```

### Get Triggers
```
GET /agent/{agent_id}/triggers
```

Returns configured YouTube channels and webhook URL.