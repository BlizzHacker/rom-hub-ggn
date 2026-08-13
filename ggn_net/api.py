from __future__ import annotations

from urllib.parse import urlencode

from .common import first, https_url, info_hash, integer, site_url, text


class GgnError(RuntimeError):
    """The GGn API was unavailable or rejected the request."""


def _mapping(value) -> dict:
    return value if isinstance(value, dict) else {}


def _items(value):
    if isinstance(value, dict):
        return [(str(k), v) for k, v in value.items() if isinstance(v, dict)]
    if isinstance(value, list):
        return [(str(i), v) for i, v in enumerate(value) if isinstance(v, dict)]
    return []


def _platform(group: dict) -> str:
    artists = first(group, "Artists", "artists", default=[])
    values = []
    for artist in artists if isinstance(artists, list) else []:
        value = first(artist, "name", "Name", default="") if isinstance(artist, dict) else artist
        value = text(value, 120)
        if value:
            values.append(value)
    return ", ".join(dict.fromkeys(values))


def _title(group: dict, torrent: dict) -> str:
    group_name = text(first(group, "Name", "name", "GroupName", "groupName"))
    release = text(first(torrent, "ReleaseTitle", "releaseTitle", "Name", "name"))
    value = release or group_name
    year = integer(first(group, "Year", "year", default=0))
    if year and str(year) not in value:
        value = f"{value} ({year})"
    flags = []
    for key in ("Format", "Encoding", "Language", "Region", "Miscellaneous", "GameDOXType"):
        item = text(first(torrent, key, key[0].lower() + key[1:], default=""), 100)
        if item:
            flags.append(item)
    return f"{value} [{' / '.join(flags)}]" if flags else value


def _torrent_type(torrent: dict) -> str:
    return text(first(torrent, "TorrentType", "torrentType", "Type", "type", default="Torrent"), 40).casefold()


def _link(torrent: dict) -> str:
    raw = text(first(torrent, "Link", "link", "URL", "url", default=""), 2000)
    if raw.startswith("magnet:"):
        return raw
    return https_url(raw)


def normalise_group_rows(payload: dict, *, include_external: bool = True) -> list[dict]:
    if not isinstance(payload, dict) or payload.get("status") != "success":
        return []
    rows = []
    for group_key, group in _items(payload.get("response")):
        group_id = text(first(group, "ID", "id", "GroupID", "groupId", default=group_key), 64)
        for torrent_key, torrent in _items(first(group, "Torrents", "torrents", default={})):
            torrent_id = text(first(torrent, "ID", "id", "TorrentID", "torrentId", default=torrent_key), 64)
            kind = _torrent_type(torrent)
            link = _link(torrent)
            native = kind in {"", "torrent"}
            if not native and not (include_external and link):
                continue
            platform = _platform(group) or text(first(group, "Platform", "platform", default=""), 120)
            rows.append({
                "group_id": group_id,
                "torrent_id": torrent_id,
                "title": _title(group, torrent),
                "platform": platform,
                "size_bytes": integer(first(torrent, "Size", "size", default=0)),
                "seeders": integer(first(torrent, "Seeders", "seeders", default=0)),
                "leechers": integer(first(torrent, "Leechers", "leechers", default=0)),
                "file_count": integer(first(torrent, "FileCount", "fileCount", default=0)),
                "snatched": integer(first(torrent, "Snatched", "snatched", default=0)),
                "category_id": text(first(torrent, "CategoryID", "categoryId", default=first(group, "CategoryID", "categoryId", default="")), 32),
                "freeleech": str(first(torrent, "FreeTorrent", "freeTorrent", default="0")).casefold() in {"1", "true", "freeleech"},
                "neutral": str(first(torrent, "NeutralTorrent", "neutralTorrent", default="0")).casefold() in {"1", "true", "neutral"},
                "info_hash": info_hash(first(torrent, "InfoHash", "infoHash", default="")),
                "release_type": text(first(torrent, "ReleaseType", "releaseType", default=""), 80),
                "torrent_type": kind or "torrent",
                "external_url": link,
                "native": native,
            })
    return rows


class Api:
    def __init__(self, ctx):
        self.ctx = ctx
        self.config = ctx.config
        self.api_key = str(self.config.get("api_key") or "").strip()

    def call(self, params: dict) -> dict:
        if not self.api_key:
            raise GgnError("GGn api_key is not configured")
        query = urlencode({k: v for k, v in params.items() if v not in (None, "")})
        response = self.ctx.http.get(
            f"{site_url(self.config, 'api.php')}?{query}",
            headers={"X-API-Key": self.api_key},
        )
        if response.status_code in (401, 403):
            raise GgnError(f"GGn rejected the API key (HTTP {response.status_code})")
        if response.status_code == 429:
            raise GgnError("GGn API rate limit reached; retry after cooldown")
        if response.status_code != 200:
            raise GgnError(f"GGn API returned HTTP {response.status_code}")
        try:
            payload = response.json()
        except (TypeError, ValueError) as exc:
            raise GgnError("GGn returned a non-JSON API response") from exc
        if not isinstance(payload, dict) or payload.get("status") != "success":
            error = text(payload.get("error") if isinstance(payload, dict) else "")
            raise GgnError(f"GGn API failure{(': ' + error) if error else ''}")
        return payload

    def search(self, query: str) -> list[dict]:
        field = "groupname" if self.config.get("search_group_names") else "searchstr"
        return normalise_group_rows(self.call({
            "request": "search",
            "search_type": "torrents",
            "empty_groups": "filled",
            "order_by": "time",
            "order_way": "desc",
            field: text(query, 200),
        }), include_external=bool(self.config.get("include_external_links", True)))

    def quick_user_passkey(self) -> str:
        response = self.call({"request": "quick_user"}).get("response")
        value = text(first(_mapping(response), "PassKey", "passkey", "passKey", default=""), 128)
        if not value:
            raise GgnError("GGn quick_user did not return a passkey")
        return value
