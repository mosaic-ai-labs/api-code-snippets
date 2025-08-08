### Mosaic API: Upload, Run, Status, Webhooks

Utilities to work with Mosaic's REST API end-to-end:

- Upload a video (`upload_video.py`)
- Run an agent on uploaded videos (`run_agent.py`)
- Poll an agent run by ID (`get_status.py`)
- Receive webhooks for real-time updates (`webhook_listener.py`)

Requirements are in `api-call/requirements.txt`.

### Setup

```bash
pip install -r requirements.txt

# Export your API key (recommended)
export MOSAIC_API_KEY=mk_your_api_key

# (Optional) Validate your key
curl -s -H "Authorization: Bearer $MOSAIC_API_KEY" https://api.mosaic.so/whoami | jq .
```

### 1) Upload a video (signed form upload)

```bash
python upload_video.py --file /path/to/video.mp4

# The script uses signed form fields from the API and multipart/form-data
python upload_video.py --file /path/to/video.mov
```

Outputs a `video_id` you can pass to `run_agent.py`.

### 2) Run an agent

```bash
python run_agent.py \
  --agent-id YOUR_AGENT_ID \
  --video-ids VIDEO_ID_1,VIDEO_ID_2 \
  --callback-url https://your-app.com/webhooks/mosaic/abc123
```

Prints the `run_id` for tracking.

### 3) Poll status

```bash
# Single fetch
python get_status.py --run-id YOUR_RUN_ID

# Continuous watch until completed/failed
python get_status.py --run-id YOUR_RUN_ID --watch --interval 5
```

### 4) Webhook listener (local dev)

```bash
# Default: http://localhost:3000
python webhook_listener.py

# Custom port + ngrok tunnel
python webhook_listener.py --port 8080 --ngrok

# Optional secret verification
export MOSAIC_WEBHOOK_SECRET=your_webhook_secret
python webhook_listener.py
```

Listener endpoints:

- `POST /webhooks/mosaic` and `POST /webhooks/mosaic/<token>`
- `GET /history` (recent webhooks)
- `GET /health` (health check)

### Complete example (end-to-end)

```bash
# 1) Upload
VIDEO_ID=$(python upload_video.py --file ./my-video.mp4 | awk '/video_id/{print $2}')

# 2) Start listener (optional)
python webhook_listener.py --ngrok &

# 3) Run agent with webhook
RUN_ID=$(python run_agent.py \
  --agent-id YOUR_AGENT_ID \
  --video-ids "$VIDEO_ID" \
  --callback-url https://your-ngrok-url/webhooks/mosaic | awk '/run_id/{print $2}')

# 4) Poll until finished (optional alternative to webhooks)
python get_status.py --run-id "$RUN_ID" --watch --interval 5
```

Notes:

- API base URL defaults to `https://api.mosaic.so`; override with `--base-url` if needed.
- All scripts accept `--api-key` or `MOSAIC_API_KEY` env var.
- For large uploads, ensure stable network and correct `--content-type`.


