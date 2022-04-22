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

---

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

---

### Preview

![Preview image](https://raw.githubusercontent.com/music-assistant/hass-music-assistant/main/screenshots/screen1.png)

<details>
<summary>Click to show more screenshots</summary>

![Preview image](https://raw.githubusercontent.com/music-assistant/hass-music-assistant/main/screenshots/screen3.png)

![Preview image](https://raw.githubusercontent.com/music-assistant/hass-music-assistant/main/screenshots/screen2.png)

![Preview image](https://raw.githubusercontent.com/music-assistant/hass-music-assistant/main/screenshots/screen4.png)

![Preview image](https://raw.githubusercontent.com/music-assistant/hass-music-assistant/main/screenshots/screen5.png)

</details>

---

## Installation

### Using HACS

- In the HACS panel, go to integrations and click the 3 dots on the top right.
- In the menu, choose `custom repositories`.
- Paste this URL in the repository field: https://github.com/music-assistant/hass-music-assistant
- For the category field , choose `integration`.
- Press the `Add` button and close the dialog afterwards.
- Once back in the `integrations page` of HACS, click the big blue button on the bottom right to add a new integration.
- Search for `Music Assistant` and click `Download this repository with HACS`
- Restart HA to load the integration into HA.

### Manually (not recommended)

- Download the [latest release](https://github.com/music-assistant/hass-music-assistant/releases) as a **zip file** and extract it into the `custom_components` folder in your HA installation.</li>
- Restart HA to load the integration into HA.

## Configuration

- Go to Configuration -> Integrations and click the big `+` button.
- Look for Music Assistant and click to add it.
- Follow the steps for initial configuration.
- The Music Assistant integration is ready for use.
- You can find the panel in the menu on the left for the rich user interface or use the default Home Assistant Media panel to quickly browse your music.
- All configuration options can be adjusted later with the `configure` button on the integration's card.
- To change the name of the panel, simply rename the integration from the integrations page.
