from collectors.pixabay_video_collector import collect_pixabay_videos


class Response:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "hits": [{
                "id": 77,
                "duration": 14,
                "pageURL": "https://pixabay.com/videos/id-77/",
                "videos": {
                    "large": {
                        "url": "https://cdn.test/4k.mp4",
                        "width": 3840,
                        "height": 2160,
                        "size": 40_000_000,
                    },
                    "medium": {
                        "url": "https://cdn.test/hd.mp4",
                        "width": 1920,
                        "height": 1080,
                        "size": 12_000_000,
                    },
                },
            }]
        }


def test_pixabay_collector_uses_sports_safe_search(monkeypatch):
    request = {}

    def get(url, **kwargs):
        request.update(url=url, **kwargs)
        return Response()

    monkeypatch.setattr("collectors.pixabay_video_collector.requests.get", get)
    items = collect_pixabay_videos("secret", "kickboxing", 30, 35, 49_000_000)
    assert request["params"]["category"] == "sports"
    assert request["params"]["safesearch"] == "true"
    assert items[0]["video_url"] == "https://cdn.test/hd.mp4"
    assert items[0]["media_id"] == "pixabay:77"
