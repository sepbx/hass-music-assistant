# Music Assistant

Turn your Home Assistant instance into a jukebox, hassle free streaming of your favorite media to Home Assistant media players.

## Introduction

Music Assistant is a music library manager for your offline and online music sources, combined with the power of Home assistant to easily stream your favourite music to a wide range of supported players.

Music Assistant consists of multiple building blocks:

- Music Assistant integration in Home Assistant - the core part that runs the Music Assistant engine and keeps track of your Music sources.
- Import Home Assistant media players into the Music Assistant engine to use as target for playback.
- Optionally export Music Assistant media players back to Home Assistant (for rich metadata etc.)
- Music Assistant 'Media Source' integration, allows browsing of your favorite media from Home Assistant's 'Media' panel.
- Music Assistant panel: A rich user interface with more advanced features than the standard Media panel.

### Features

- Supports multiple music sources through a provider implementation.
- Currently implemented music providers are Spotify, Qobuz, Tune-In Radio and local filesystem.
- More music providers can be easily added, soon available: Tidal and Deezer.
- Auto matches music on different providers (track linking).
- Fetches metadata for extended artist information.
- Keeps track of the entire music library in a compact database
- All media players available in Home Assistant that support streaming from an url are supported, which is basically almost all targets.
- Gapless, crossfade and volume normalization support for all players.
- Truly hassle free streaming of your favorite music to players, no advanced knowledge required.
- Rich User interface (Progressive Web App) hosted as panel directly in the Home Assistant user interface.

### Preview

![Preview image](https://raw.githubusercontent.com/music-assistant/hass-music-assistant/main/screenshots/screen1.png)
