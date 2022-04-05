"""Media Source Implementation."""
from __future__ import annotations

import asyncio
import logging

from homeassistant.components.media_player.const import (
    MEDIA_CLASS_ALBUM,
    MEDIA_CLASS_ARTIST,
    MEDIA_CLASS_CHANNEL,
    MEDIA_CLASS_DIRECTORY,
    MEDIA_CLASS_MUSIC,
    MEDIA_CLASS_PLAYLIST,
    MEDIA_CLASS_TRACK,
    MEDIA_TYPE_ALBUM,
    MEDIA_TYPE_ARTIST,
    MEDIA_TYPE_MUSIC,
    MEDIA_TYPE_PLAYLIST,
    MEDIA_TYPE_TRACK,
)
from homeassistant.components.media_source.error import Unresolvable
from homeassistant.components.media_source.models import (
    BrowseMediaSource,
    MediaSource,
    MediaSourceItem,
    PlayMedia,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from music_assistant import MusicAssistant
from music_assistant.helpers.images import get_image_url
from music_assistant.models.media_items import Album, Track

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


MEDIA_TYPE_RADIO = "radio"

PLAYABLE_MEDIA_TYPES = [
    MEDIA_TYPE_PLAYLIST,
    MEDIA_TYPE_ALBUM,
    MEDIA_TYPE_ARTIST,
    MEDIA_TYPE_RADIO,
    MEDIA_TYPE_TRACK,
]

LIBRARY_ARTISTS = "artists"
LIBRARY_ALBUMS = "albums"
LIBRARY_TRACKS = "tracks"
LIBRARY_PLAYLISTS = "playlists"
LIBRARY_RADIO = "radio"


LIBRARY_TITLE_MAP = {
    # TODO: How to localize this ?
    LIBRARY_ARTISTS: "Artists",
    LIBRARY_ALBUMS: "Albums",
    LIBRARY_TRACKS: "Tracks",
    LIBRARY_PLAYLISTS: "Playlists",
    LIBRARY_RADIO: "Radio stations",
}

LIBRARY_MEDIA_CLASS_MAP = {
    LIBRARY_ARTISTS: MEDIA_CLASS_ARTIST,
    LIBRARY_ALBUMS: MEDIA_CLASS_ALBUM,
    LIBRARY_TRACKS: MEDIA_CLASS_TRACK,
    LIBRARY_PLAYLISTS: MEDIA_CLASS_PLAYLIST,
    LIBRARY_RADIO: MEDIA_CLASS_MUSIC,
}


async def async_get_media_source(hass: HomeAssistant) -> MusicAssistentSource:
    """Set up Music Assistant media source."""
    # Music Assistant supports only a single config entry
    entry = hass.config_entries.async_entries(DOMAIN)[0]

    return MusicAssistentSource(hass, entry)


class MusicAssistentSource(MediaSource):
    """Provide Music Assistent Media Items as media sources."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize CameraMediaSource."""
        super().__init__(DOMAIN)
        self.hass = hass
        self.entry = entry
        self.name = entry.title

    def get_mass(self) -> MusicAssistant | None:
        """Return the Music Assistant instance."""
        return self.hass.data.get(DOMAIN)

    async def async_resolve_media(self, item: MediaSourceItem) -> PlayMedia:
        """Resolve media to a url."""
        mass = self.get_mass()

        if mass is None:
            raise Unresolvable("MusicAssistant is not initialized")

        # this part is tricky because we need to know which player is requesting the media
        # so we can put the request on the correct queue
        # for now we have a workaround in place that intercepts the call_service command
        # to the media_player and find out the player from there.
        # Hacky but it does the job and let'd hope for a contextvar in the future.

        return PlayMedia(item.identifier, "audio/wav")

    async def async_browse_media(
        self,
        item: MediaSourceItem,
    ) -> BrowseMediaSource:
        """Return library media for Music Assistent instance."""
        mass = self.get_mass()

        if mass is None:
            raise Unresolvable("MusicAssistant is not initialized")

        if item is None or item.identifier is None:
            return self._build_main_listing()
        if item.identifier == LIBRARY_ARTISTS:
            return await self._build_artists_listing(mass)
        if item.identifier == LIBRARY_ALBUMS:
            return await self._build_albums_listing(mass)
        if item.identifier == LIBRARY_TRACKS:
            return await self._build_tracks_listing(mass)
        if item.identifier == LIBRARY_PLAYLISTS:
            return await self._build_playlists_listing(mass)
        if item.identifier == LIBRARY_RADIO:
            return await self._build_radio_listing(mass)
        if "artist" in item.identifier:
            return await self._build_artist_items_listing(mass, item.identifier)
        if "album" in item.identifier:
            return await self._build_album_items_listing(mass, item.identifier)
        if "playlist" in item.identifier:
            return await self._build_playlist_items_listing(mass, item.identifier)

        raise Unresolvable(f"Unknown identifier: {item.identifier}")

    @callback
    def _build_main_listing(self):
        """Build main browse listing."""
        parent_source = BrowseMediaSource(
            domain=DOMAIN,
            identifier=None,
            title=self.entry.title,
            media_class=MEDIA_CLASS_CHANNEL,
            media_content_type=MEDIA_TYPE_MUSIC,
            can_play=False,
            can_expand=True,
            children_media_class=MEDIA_CLASS_DIRECTORY,
            children=[],
        )
        for library, media_class in LIBRARY_MEDIA_CLASS_MAP.items():
            child_source = BrowseMediaSource(
                domain=DOMAIN,
                identifier=library,
                title=LIBRARY_TITLE_MAP[library],
                media_class=MEDIA_CLASS_DIRECTORY,
                media_content_type=MEDIA_TYPE_MUSIC,
                children_media_class=media_class,
                can_play=False,
                can_expand=True,
            )
            parent_source.children.append(child_source)
        return parent_source

    async def _build_playlists_listing(self, mass: MusicAssistant):
        """Build Playlists browse listing."""
        media_class = LIBRARY_MEDIA_CLASS_MAP[LIBRARY_PLAYLISTS]
        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=LIBRARY_PLAYLISTS,
            title=LIBRARY_TITLE_MAP[LIBRARY_PLAYLISTS],
            media_class=MEDIA_CLASS_DIRECTORY,
            media_content_type=MEDIA_TYPE_MUSIC,
            can_play=False,
            can_expand=True,
            children_media_class=media_class,
            children=[
                BrowseMediaSource(
                    domain=DOMAIN,
                    identifier=playlist.uri,
                    title=playlist.name,
                    media_class=media_class,
                    media_content_type=MEDIA_TYPE_PLAYLIST,
                    can_play=True,
                    can_expand=True,
                    thumbnail=await get_image_url(mass, playlist),
                )
                for playlist in await mass.music.playlists.library()
            ],
        )

    async def _build_playlist_items_listing(
        self, mass: MusicAssistant, identifier: str
    ):
        """Build Playlist items browse listing."""
        playlist = await mass.music.get_item_by_uri(identifier)
        tracks = await mass.music.playlists.tracks(playlist.item_id, playlist.provider)

        async def build_item(track: Track):
            return BrowseMediaSource(
                domain=DOMAIN,
                identifier=track.uri,
                title=f"{track.artists[0].name} - {track.name}",
                media_class=MEDIA_CLASS_TRACK,
                media_content_type=MEDIA_TYPE_TRACK,
                can_play=True,
                can_expand=False,
                thumbnail=await get_image_url(mass, track),
            )

        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=playlist.uri,
            title=playlist.name,
            media_class=MEDIA_CLASS_PLAYLIST,
            media_content_type=MEDIA_TYPE_PLAYLIST,
            can_play=True,
            can_expand=True,
            children_media_class=MEDIA_CLASS_TRACK,
            children=await asyncio.gather(
                *[build_item(track) for track in tracks],
            ),
        )

    async def _build_artists_listing(self, mass: MusicAssistant):
        """Build Albums browse listing."""
        media_class = LIBRARY_MEDIA_CLASS_MAP[LIBRARY_ARTISTS]
        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=LIBRARY_ARTISTS,
            title=LIBRARY_TITLE_MAP[LIBRARY_ARTISTS],
            media_class=MEDIA_CLASS_DIRECTORY,
            media_content_type=MEDIA_TYPE_MUSIC,
            can_play=False,
            can_expand=True,
            children_media_class=media_class,
            children=[
                BrowseMediaSource(
                    domain=DOMAIN,
                    identifier=artist.uri,
                    title=artist.name,
                    media_class=media_class,
                    media_content_type=MEDIA_TYPE_ARTIST,
                    can_play=True,
                    can_expand=True,
                    thumbnail=await get_image_url(mass, artist),
                )
                for artist in await mass.music.artists.library()
            ],
        )

    async def _build_artist_items_listing(self, mass: MusicAssistant, identifier: str):
        """Build Artist items browse listing."""
        artist = await mass.music.get_item_by_uri(identifier)
        albums = await mass.music.artists.albums(artist.item_id, artist.provider)

        async def build_item(album: Album):
            return BrowseMediaSource(
                domain=DOMAIN,
                identifier=album.uri,
                title=f"{album.name} ({album.artist.name})",
                media_class=MEDIA_CLASS_ALBUM,
                media_content_type=MEDIA_TYPE_ALBUM,
                can_play=True,
                can_expand=True,
                thumbnail=await get_image_url(mass, album),
            )

        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=artist.uri,
            title=artist.name,
            media_class=MEDIA_TYPE_ARTIST,
            media_content_type=MEDIA_TYPE_ARTIST,
            can_play=True,
            can_expand=True,
            children_media_class=MEDIA_CLASS_ALBUM,
            children=await asyncio.gather(
                *[build_item(album) for album in albums],
            ),
        )

    async def _build_albums_listing(self, mass: MusicAssistant):
        """Build Albums browse listing."""
        media_class = LIBRARY_MEDIA_CLASS_MAP[LIBRARY_ALBUMS]
        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=LIBRARY_ALBUMS,
            title=LIBRARY_TITLE_MAP[LIBRARY_ALBUMS],
            media_class=MEDIA_CLASS_DIRECTORY,
            media_content_type=MEDIA_TYPE_MUSIC,
            can_play=False,
            can_expand=True,
            children_media_class=media_class,
            children=[
                BrowseMediaSource(
                    domain=DOMAIN,
                    identifier=album.uri,
                    title=album.name,
                    media_class=media_class,
                    media_content_type=MEDIA_TYPE_ALBUM,
                    can_play=True,
                    can_expand=True,
                    thumbnail=await get_image_url(mass, album),
                )
                for album in await mass.music.albums.library()
            ],
        )

    async def _build_album_items_listing(self, mass: MusicAssistant, identifier: str):
        """Build Album items browse listing."""
        album = await mass.music.get_item_by_uri(identifier)
        tracks = await mass.music.albums.tracks(album.item_id, album.provider)

        async def build_item(track: Track):
            return BrowseMediaSource(
                domain=DOMAIN,
                identifier=track.uri,
                title=f"{track.artists[0].name} - {track.name}",
                media_class=MEDIA_CLASS_TRACK,
                media_content_type=MEDIA_TYPE_TRACK,
                can_play=True,
                can_expand=False,
                thumbnail=await get_image_url(mass, track),
            )

        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=album.uri,
            title=album.name,
            media_class=MEDIA_TYPE_ALBUM,
            media_content_type=MEDIA_TYPE_ALBUM,
            can_play=True,
            can_expand=True,
            children_media_class=MEDIA_CLASS_TRACK,
            children=await asyncio.gather(
                *[build_item(track) for track in tracks],
            ),
        )

    async def _build_tracks_listing(self, mass: MusicAssistant):
        """Build Tracks browse listing."""
        media_class = LIBRARY_MEDIA_CLASS_MAP[LIBRARY_TRACKS]
        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=LIBRARY_ALBUMS,
            title=LIBRARY_TITLE_MAP[LIBRARY_TRACKS],
            media_class=MEDIA_CLASS_DIRECTORY,
            media_content_type=MEDIA_TYPE_MUSIC,
            can_play=False,
            can_expand=True,
            children_media_class=media_class,
            children=[
                BrowseMediaSource(
                    domain=DOMAIN,
                    identifier=track.uri,
                    title=track.name,
                    media_class=media_class,
                    media_content_type=MEDIA_TYPE_TRACK,
                    can_play=True,
                    can_expand=False,
                    thumbnail=await get_image_url(mass, track),
                )
                for track in await mass.music.tracks.library()
            ],
        )

    async def _build_radio_listing(self, mass: MusicAssistant):
        """Build Radio browse listing."""
        media_class = LIBRARY_MEDIA_CLASS_MAP[LIBRARY_RADIO]
        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=LIBRARY_ALBUMS,
            title=LIBRARY_TITLE_MAP[LIBRARY_RADIO],
            media_class=MEDIA_CLASS_DIRECTORY,
            media_content_type=MEDIA_TYPE_MUSIC,
            can_play=False,
            can_expand=True,
            children_media_class=media_class,
            children=[
                BrowseMediaSource(
                    domain=DOMAIN,
                    identifier=radio.uri,
                    title=radio.name,
                    media_class=media_class,
                    media_content_type=MEDIA_TYPE_RADIO,
                    can_play=True,
                    can_expand=False,
                    thumbnail=await get_image_url(mass, radio),
                )
                for radio in await mass.music.radio.library()
            ],
        )


# async def async_create_item_listing(mass: MusicAssistant, media_item: dict):
#     """Create BrowseMediaSource payload for the (parsed) media item."""
#     source = None
#     items = []
#     if media_item["media_type"] == "playlists":
#         items = await mass.get_library_playlists()
#     elif media_item["media_type"] == "artists":
#         items = await mass.get_library_artists()
#     elif media_item["media_type"] == "albums":
#         items = await mass.get_library_albums()
#     elif media_item["media_type"] == "tracks":
#         items = await mass.get_library_tracks()
#     elif media_item["media_type"] == "radios":
#         items = await mass.get_library_radios()
#     elif media_item["media_type"] == MEDIA_TYPE_PLAYLIST:
#         # playlist tracks
#         source = await async_create_media_item_source(
#             mass,
#             await mass.get_playlist(media_item["item_id"], media_item["provider"]),
#         )
#         items = await mass.get_playlist_tracks(
#             media_item["item_id"], media_item["provider"]
#         )
#     elif media_item["media_type"] == MEDIA_TYPE_ALBUM:
#         # album tracks
#         source = await async_create_media_item_source(
#             mass,
#             await mass.get_album(media_item["item_id"], media_item["provider"]),
#         )
#         items = await mass.get_album_tracks(
#             media_item["item_id"], media_item["provider"]
#         )
#     elif media_item["media_type"] == MEDIA_TYPE_ARTIST:
#         # artist albums
#         source = await async_create_media_item_source(
#             mass,
#             await mass.get_artist(media_item["item_id"], media_item["provider"]),
#         )
#         items = await mass.get_artist_albums(
#             media_item["item_id"], media_item["provider"]
#         )
#     if not source:
#         # create generic source
#         source = await async_create_generic_source(media_item)
#     # attach source childs
#     for item in items:
#         child_item = await async_create_media_item_source(mass, item)
#         source.children.append(child_item)

#     return source


# async def async_create_generic_source(media_item: dict):
#     """Create a BrowseMedia source for a generic (root folder) item."""
#     media_class = CONTENT_TYPE_MEDIA_CLASS[media_item["media_type"]]
#     title = LIBRARY_MAP.get(media_item["content_id"])
#     image = ""
#     return BrowseMediaSource(
#         domain=DOMAIN,
#         identifier=f'{media_item["media_type"]}/{media_item["content_id"]}',
#         title=title,
#         media_class=media_class["parent"],
#         children_media_class=media_class["children"],
#         media_content_type=CONTENT_TYPE_MUSIC,
#         can_play=media_item["media_type"] in PLAYABLE_MEDIA_TYPES,
#         children=[],
#         can_expand=True,
#         thumbnail=image,
#     )


# async def async_create_media_item_source(mass: MusicAssistant, media_item: dict):
#     """Convert Music Assistant media_item into a BrowseMedia item."""
#     # get media_type and class
#     media_type = media_item["media_type"]
#     media_class = CONTENT_TYPE_MEDIA_CLASS[media_type]

#     # get image url
#     image = await mass.get_media_item_image_url(media_item)
#     # create title
#     if media_type == "album":
#         title = f'{media_item["artist"]["name"]} - {media_item["name"]}'
#     if media_type == "track":
#         artist_names = [i["name"] for i in media_item["artists"]]
#         artist_names_str = " / ".join(artist_names)
#         title = f'{artist_names_str} - {media_item["name"]}'
#     else:
#         title = media_item["name"]

#     # create media_content_id from provider/item_id combination
#     media_item_id = (
#         f'{media_item["provider"]}{ITEM_ID_SEPERATOR}{media_item["item_id"]}'
#     )

#     # we're constructing the identifier and media_content_id manually
#     # this way we're compatible with both BrowseMedia and BrowseMediaSource
#     identifier = f"{media_type}/{media_item_id}"
#     media_content_id = f"{MASS_URI_SCHEME}{identifier}"
#     src = BrowseMedia(
#         title=title,
#         media_class=media_class["parent"],
#         children_media_class=media_class["children"],
#         media_content_id=media_content_id,
#         media_content_type=CONTENT_TYPE_MUSIC,
#         can_play=media_type in PLAYABLE_MEDIA_TYPES,
#         children=[],
#         can_expand=media_type not in [MEDIA_TYPE_TRACK, MEDIA_TYPE_RADIO],
#         thumbnail=image,
#     )
#     # set these manually so we're compatible with BrowseMediaSource
#     src.identifier = identifier
#     src.domain = DOMAIN
#     return src


# async def async_parse_uri(uri: str) -> dict:
#     """Parse uri (item identifier) to some values we can understand."""
#     content_id = ""
#     provider = ""
#     item_id = ""
#     if uri.startswith(MASS_URI_SCHEME):
#         uri = uri.split(MASS_URI_SCHEME)[1]
#     if uri.startswith("/"):
#         uri = uri[1:]
#     mass_id = uri.split("/")[0]
#     media_type = uri.split("/")[1]
#     # music assistant needs a provider and item_id combination for all media items (or an uri)
#     # we've mangled both in the content_id, used by Hass internally
#     if len(uri.split("/")) > 2:
#         content_id = uri.split("/")[2]
#         if content_id:
#             provider, item_id = content_id.split(ITEM_ID_SEPERATOR)
#     # return a dict that is (partly) compatible with the Music Assistant MediaItem structure
#     return {
#         "item_id": item_id,
#         "provider": provider,
#         "media_type": media_type,
#         "mass_id": mass_id,
#         "content_id": content_id,
#     }
