# Mosaic API Tools

Scripts to upload videos, run agents, and track progress.

## Setup
```bash
pip install -r requirements.txt
export MOSAIC_API_KEY=mk_your_api_key
```

## Scripts

### 1. Upload Video
```bash
python upload_video.py --file video.mp4
# Returns: video_id
```

### 2. Run Agent
```bash
python run_agent.py --agent-id YOUR_AGENT_ID --video-ids VIDEO_ID
# Returns: run_id
```

### 3. Check Status
```bash
# One-time check
python get_status.py --run-id RUN_ID

# Watch until complete
python get_status.py --run-id RUN_ID --watch
```

### 4. Webhook Listener
```bash
# Basic
python webhook_listener.py

# With options
python webhook_listener.py --port 8080 --webhook-secret my_secret --ngrok
```

## Full Example
```bash
# Upload
VIDEO_ID=$(python upload_video.py --file video.mp4 | grep video_id | awk '{print $2}')

# Run agent
RUN_ID=$(python run_agent.py --agent-id YOUR_AGENT_ID --video-ids $VIDEO_ID | grep run_id | awk '{print $2}')

# Watch progress
python get_status.py --run-id $RUN_ID --watch
```

## Webhook Validation
Set webhook secret via flag or env:
```bash
python webhook_listener.py --webhook-secret your_secret
# OR
export MOSAIC_WEBHOOK_SECRET=your_secret
python webhook_listener.py
```

Validates `X-Mosaic-Signature` header against your secret.