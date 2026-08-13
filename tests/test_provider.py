import pytest
from rom_hub.types import SearchResult
from rom_hub_sdk.context import PluginContext

from ggn_net.api import normalise_group_rows
from ggn_net.search import Search
from ggn_net.torrent import TorrentRefused, Torrents


PAYLOAD = {
    "status": "success",
    "response": {"1": {
        "ID": "1", "Name": "Example Game", "Year": 2026,
        "Artists": [{"name": "Windows"}],
        "Torrents": {
            "42": {
                "ID": "42", "TorrentType": "Torrent",
                "ReleaseTitle": "Example_Game-v1", "Size": 2048,
                "Seeders": 7, "Leechers": 2, "FileCount": 1,
                "InfoHash": "ABCDEF0123456789ABCDEF0123456789ABCDEF01",
            },
            "43": {
                "ID": "43", "TorrentType": "Link",
                "ReleaseTitle": "Example Game external",
                "Link": "magnet:?xt=urn:btih:ABCDEF0123456789ABCDEF0123456789ABCDEF01",
            },
        },
    }},
}


class Response:
    status_code = 200
    def __init__(self, payload): self.payload = payload
    def json(self): return self.payload


class Http:
    def __init__(self, *payloads):
        self.payloads = list(payloads)
        self.urls = []
        self.headers = []
    def get(self, url, params=None, headers=None):
        self.urls.append(url)
        self.headers.append(headers or {})
        return Response(self.payloads.pop(0))


def context(http, **extra):
    return PluginContext(config={"api_key": "api-secret", **extra}, http=http)


def test_api_parser_separates_native_and_external_rows():
    rows = normalise_group_rows(PAYLOAD)
    assert [row["torrent_id"] for row in rows] == ["42", "43"]
    assert rows[0]["native"] is True
    assert rows[1]["native"] is False


def test_search_uses_api_without_putting_key_in_url():
    http = Http(PAYLOAD)
    results = Search(context(http)).search("Example Game", "pc", 10)
    assert results[0].source_id == "ggn:42"
    assert results[0].platform == "pc"
    assert results[0].extra["seeders"] == "7"
    assert "api-secret" not in http.urls[0]
    assert http.headers[0] == {"X-API-Key": "api-secret"}
    assert "request=search" in http.urls[0]


def test_private_download_keeps_passkey_and_hash():
    result = Search(context(Http(PAYLOAD))).search("Example", None, 1)[0]
    source = Torrents(context(Http(PAYLOAD), passkey="pass-secret")).resolve(result)
    assert source.kind == "torrent_url"
    assert "id=42" in source.source
    assert "torrent_pass=pass-secret" in source.source
    assert source.info_hash == "abcdef0123456789abcdef0123456789abcdef01"


def test_missing_passkey_uses_quick_user():
    result = SearchResult(source_id="ggn:42", title="Example")
    http = Http({"status": "success", "response": {"PassKey": "resolved-pass"}})
    source = Torrents(context(http)).resolve(result)
    assert "torrent_pass=resolved-pass" in source.source
    assert "request=quick_user" in http.urls[0]


def test_external_page_is_not_called_a_torrent():
    result = SearchResult(source_id="ggn-link:https://example.invalid/game", title="External")
    with pytest.raises(TorrentRefused, match="external web page"):
        Torrents(context(Http({}))).resolve(result)


def test_external_magnet_is_supported():
    result = SearchResult(
        source_id="ggn-link:magnet:?xt=urn:btih:ABCDEF0123456789ABCDEF0123456789ABCDEF01",
        title="External torrent",
    )
    source = Torrents(context(Http({}))).resolve(result)
    assert source.kind == "magnet"
