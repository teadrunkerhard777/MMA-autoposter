from collectors.pexels_video_collector import collect_pexels_videos


class Response:
    def __init__(self):
        self.payload = {
            "videos": [{
                "id": 42,
                "duration": 12,
                "url": "https://www.pexels.com/video/42/",
                "user": {"name": "Author"},
                "video_files": [
                    {
                        "file_type": "video/mp4",
                        "link": "https://cdn.test/4k.mp4",
                        "width": 2160,
                        "height": 3840,
                        "file_size": 40_000_000,
                    },
                    {
                        "file_type": "video/mp4",
                        "link": "https://cdn.test/hd.mp4",
                        "width": 720,
                        "height": 1280,
                        "file_size": 8_000_000,
                    },
                ],
            }]
        }

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def test_pexels_collector_uses_official_search_and_compact_mp4(monkeypatch):
    request = {}

    def get(url, **kwargs):
        request.update(url=url, **kwargs)
        return Response()

    monkeypatch.setattr("collectors.pexels_video_collector.requests.get", get)
    items = collect_pexels_videos(
        "secret", "mma sparring", "landscape", 30, 35, 49_000_000
    )
    assert request["headers"] == {"Authorization": "secret"}
    assert request["params"]["query"] == "mma sparring"
    assert request["params"]["orientation"] == "landscape"
    assert items[0]["video_url"] == "https://cdn.test/hd.mp4"
    assert items[0]["media_id"] == "pexels:42"


def test_pexels_accepts_missing_size_for_stream_validation(monkeypatch):
    response = Response()
    response.payload["videos"][0]["video_files"][1]["file_size"] = None
    monkeypatch.setattr(
        "collectors.pexels_video_collector.requests.get",
        lambda *args, **kwargs: response,
    )

    items = collect_pexels_videos(
        "secret", "mma sparring", "landscape", 30, 35, 49_000_000
    )

    assert items[0]["video_url"] == "https://cdn.test/hd.mp4"
