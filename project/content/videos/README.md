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
    "video_path": "project/content/videos/clips/licensed-clip.mp4",
    "rights_confirmed": true,
    "license_note": "Used with permission"
  }
]
```

Repository-owned `video_path` files must stay inside the `clips` directory.
Credential-free HTTPS MP4 URLs remain supported for externally hosted media.
Set `rights_confirmed` only after confirming that the channel may republish the
clip. Do not add social network page URLs or media obtained by bypassing access
controls.
