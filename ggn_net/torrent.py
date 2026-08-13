from __future__ import annotations

from urllib.parse import quote

from rom_hub_sdk import SearchResult, TorrentProvider, TorrentSource

from .api import Api, GgnError
from .common import info_hash, site_url, text


class TorrentRefused(Exception):
    """The selected GGn row is not a native torrent."""


class Torrents(TorrentProvider):
    def resolve(self, result: SearchResult) -> TorrentSource:
        source = text(result.source_id, 4000)
        title = text(result.title, 500) or None
        if source.startswith("ggn-link:"):
            external = source[len("ggn-link:"):]
            if external.startswith("magnet:"):
                return TorrentSource(kind="magnet", source=external, name=title, extra={"origin": "GGn external link"})
            raise TorrentRefused("GGn exposed an external web page, not a native .torrent or magnet")
        if not source.startswith("ggn:") or not source[4:].isdigit():
            raise TorrentRefused("the result is not a GGn torrent identifier")
        torrent_id = source[4:]
        passkey = text(self.ctx.config.get("passkey"), 128)
        if not passkey:
            try:
                passkey = Api(self.ctx).quick_user_passkey()
            except GgnError as exc:
                raise TorrentRefused(str(exc)) from exc
        source_url = (
            f"{site_url(self.ctx.config, 'torrents.php')}?action=download"
            f"&id={quote(torrent_id)}&authkey=rom-hub&torrent_pass={quote(passkey)}"
        )
        return TorrentSource(
            kind="torrent_url",
            source=source_url,
            name=title,
            info_hash=info_hash(result.extra.get("info_hash", "")),
            extra={"origin": "gazellegames.net", "torrent_id": torrent_id, "private": "true"},
        )
