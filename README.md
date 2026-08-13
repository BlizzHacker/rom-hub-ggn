# GazelleGames.net (GGn) for ROM Hub / ROMarr

An RPP v1 private-tracker plugin for GazelleGames.net. It searches GGn's
authenticated JSON API and hands native torrent rows to the host as GGn
download URLs, preserving the private tracker's private announce/passkey flow.

The API key and optional passkey are ROM Hub secret settings. The plugin does
not run a torrent client, rebuild private torrents as public magnets, or put
credentials in a catalogue.

Install:

    rom-hub plugin install https://git.moveweight.com/BlizzHacker/rom-hub-ggn
    rom-hub plugin secret set ggn api_key --stdin
    rom-hub search ggn "Kobayakawa-san"

This plugin requires a ROM Hub build with the RPP v1 `torrent` capability and
brokered request-header support. Older proof-stack builds report
`unknown capability 'torrent'` during install; upgrade the Hub source first.

If passkey is not configured, the plugin calls GGn's authenticated
request=quick_user endpoint when a native torrent is handed off.

The supplied GGn page showed two External Link rows and no native torrent
rows. Those links are retained as result metadata, but a normal Booth/Plicy
web page is not treated as a .torrent; torrent handoff refuses it rather
than guessing. A literal external magnet is supported.

ROMarr normally searches Prowlarr. Current Prowlarr releases already ship a
native GazelleGames definition using this same API; configure GGn there with
its API key and mark it private. This plugin is for ROM Hub direct use and
keeps the same source available through the ROM Hub catalogue.

Use only for content you are entitled to access and in accordance with GGn's
rules and applicable law. Unofficial; not affiliated with GazelleGames.net.

MIT — see LICENSE.
