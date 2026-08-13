from __future__ import annotations

import re

from rom_hub_sdk import SearchProvider, SearchResult

from .api import Api
from .common import site_url, text


PLATFORMS = {
    "windows": "pc", "dos": "pc", "linux": "pc", "mac": "mac",
    "playstation 1": "psx", "playstation": "psx", "playstation 2": "ps2",
    "playstation portable": "psp", "playstation vita": "psvita",
    "nintendo ds": "nds", "game boy advance": "gba", "game boy color": "gbc",
    "game boy": "gb", "nintendo 3ds": "3ds", "nintendo gamecube": "ngc",
    "dreamcast": "dc", "mega drive": "genesis-slash-megadrive",
    "genesis": "genesis-slash-megadrive", "snes": "snes", "nes": "nes",
    "wii": "wii", "wii u": "wiiu", "switch": "switch",
    "xbox": "xbox", "xbox 360": "xbox360",
}


def words(value: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", value.casefold())


class Search(SearchProvider):
    def search(self, query: str, platform: str | None, limit: int) -> list[SearchResult]:
        rows = Api(self.ctx).search(query or "")
        wanted = text(platform).casefold()
        terms = words(query or "")
        out = []
        for row in rows:
            mapped = PLATFORMS.get(row["platform"].casefold())
            if wanted and wanted not in {row["platform"].casefold(), str(mapped or "").casefold()}:
                continue
            if terms and not all(term in " ".join(words(row["title"])) for term in terms):
                continue
            source_id = f"ggn:{row['torrent_id']}" if row["native"] else f"ggn-link:{row['external_url']}"
            extra = {
                "group_id": row["group_id"], "torrent_id": row["torrent_id"],
                "seeders": str(row["seeders"]), "leechers": str(row["leechers"]),
                "files": str(row["file_count"]), "snatched": str(row["snatched"]),
                "category_id": row["category_id"], "torrent_type": row["torrent_type"],
                "native_torrent": str(row["native"]).lower(),
                "freeleech": str(row["freeleech"]).lower(),
                "neutral": str(row["neutral"]).lower(),
            }
            if row["info_hash"]:
                extra["info_hash"] = row["info_hash"]
            if row["release_type"]:
                extra["release_type"] = row["release_type"]
            if row["external_url"]:
                extra["external_url"] = row["external_url"]
            out.append(SearchResult(
                source_id=source_id,
                title=row["title"] or f"GGn torrent {row['torrent_id']}",
                platform=mapped or row["platform"] or None,
                size_bytes=row["size_bytes"] or None,
                url=site_url(self.ctx.config, f"torrents.php?id={row['group_id']}&torrentid={row['torrent_id']}"),
                extra=extra,
            ))
        return out[:max(0, limit)]
