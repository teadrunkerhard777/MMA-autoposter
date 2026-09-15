# Video queue

Add licensed MP4 clips to `index.json`. The runner publishes at most one unused
entry for the requested `day` or `evening` slot. Empty queues are a safe no-op.

```json
[
  {
    "id": "unique-video-id",
    "slot": "day",
    "title": "Яркий момент тренировки",
    "note": "Короткая редакционная заметка на русском языке.",
    "source": "Rights holder name",
    "source_url": "https://example.com/original",
    "video_url": "https://cdn.example.com/licensed-clip.mp4",
    "rights_confirmed": true,
    "license_note": "Used with permission"
  }
]
```

Only credential-free HTTPS MP4 URLs are accepted. Set `rights_confirmed` only
after confirming that the channel may republish the clip. Do not add social
network page URLs or media obtained by bypassing access controls.
