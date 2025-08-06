Step 1: Create an agent at app.mosaic.so. **You don't need to add a youtube trigger.** Just create the agent from video input start to finish. Grab the id of the agent.

Step 2: Call `/agent/{agent_id}/triggers/add_youtube_channels` POST with payload:

```
{
    "youtube_channels": [
        "youtube_channel_id_here"
    ],
    "trigger_callback_url": "url_here"
}

This creates a youtube trigger on your agent if a youtube trigger node doesn't already exist on your agent. If there is a youtube trigger on your agent already, making this POST request will just add those channels to that youtube trigger node. Note that trigger_callback_url is the webhook url that gets hit with POST requests whenever the youtube trigger node gets triggered. If you add `trigger_callback_url` to your POST request and you already have a callback_url to your trigger, it will overwrite that callback_url on your trigger.

For best practice, we recommend adding a bunch of youtube channels on one youtube trigger node through calling `/triggers/add_youtube_channels` and using `trigger_callback_url` as a way to check for finished outputs from an uploaded youtube video. When a run starts from a youtube video upload, a POST request will be sent to callback_url with this payload:

```
{
  "flag": "RUN_STARTED",
  "agent_id": "123e4567-e89b-12d3-a456-789012345678",
  "run_id": "7f8d9c2b-4a6e-8b3f-1d5c-9e2f3a4b5c6d",
  "status": "running",
  "inputs": [
    {
      "video_id": "550e8400-e29b-41d4-a716-446655440000",
      "video_url": "https://storage.googleapis.com/mosaic-inputs/input.mp4",
      "thumbnail_url": "https://storage.googleapis.com/mosaic-inputs/thumb.jpg"
    }
  ],
  "triggered_by": {  // Only present for triggered runs
    "id": "8f7d6c5b-4a3e-2b1f-9d8c-1a2b3c4d5e6f",
    "type": "youtube",
    "youtube": {
      "id": "dQw4w9WgXcQ",
      "channel": "UCxxxxxxxxxxxxxx",
      "title": "Never Gonna Give You Up",
      "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    }
  }
}
```

When an output is finished, this POST request payload will be sent:

```
{
  "flag": "OUTPUTS_FINISHED",
  "agent_id": "uuid-of-agent",
  "run_id": "uuid-of-agent-state",
  "status": "running",
  "output": [
    {
      "video_url": "https://storage-url/path/to/video.mp4",
      "thumbnail_url": "https://storage-url/path/to/thumbnail.jpg",
      "completed_at": "2024-01-15T10:30:00Z"
    }
    // ... more outputs if multiple videos were generated
  ]
}
```

When a run is fully finished, this POST request payload will be sent:

```
{
  "flag": "RUN_FINISHED",
  "agent_id": "uuid-of-agent",
  "run_id": "uuid-of-agent-state",
  "status": "completed",
  "inputs": [
    {
      "file_url": "https://storage-url/path/to/input.mp4",
      "file_name": "input_video.mp4",
      "uploaded_at": "2024-01-15T09:00:00Z"
    }
  ],
  "outputs": [
    {
      "video_url": "https://storage-url/path/to/output.mp4",
      "thumbnail_url": "https://storage-url/path/to/thumbnail.jpg",
      "completed_at": "2024-01-15T10:30:00Z"
    }
    // ... all outputs from all nodes
  ],
  "triggered_by": {  // Optional field, only present for triggered runs
    "type": "youtube",
    "channel_id": "UC...",
    "channel_name": "Channel Name",
    "video_id": "dQw4w9WgXcQ",
    "video_title": "Video Title",
    "video_url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
    "triggered_at": "2024-01-15T09:00:00Z"
  }
}
```

To test webhooks locally, we recommend setting up an ngrok channel so api.mosaic.so can hit your webhook endpoint.

In this folder, we have two files:

app.py -> this script takes in an agent_id and adds youtube channels to your agent as a trigger. After adding them, the script calls GET `/agent/[agent_id]/triggers` to validate that the youtube channels have been added to your agent.
webhook_listener.py -> this script listens to webhook requests and prints them out to the console.