# Cudy router integration for Home Assistant

This is an unofficial integration of Cudy routers for Home Assistant.

Unofficial means that this is not supported by Cudy, file issues here, not for them.

As the project is in a really early stage (and who knows if it will be ever more than that),
breaking modifications, like configuration or entity ID changes may be introduced.
Please keep that in mind when using it.

## Features

This integration logs in to the standard administration UI and
scrapes the information from HTML pages.
Although Cudy routers has a JSON RPC interface, it is not open for the public.

- Provides sensors about 4G/LTE connection (network, cell, signal)
- Provides sensors about devices (count, top bandwidth users)
- Detailed report about configured devices (IP, bandwidth usage)

## Installing

[![](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=corebonts&repository=hass-cudy-router&category=integration)

put the `custom_component/cudy_router` folder into your Home Assistant `custom_components` folder.

## Contributing

It started as my personal project to satisfy my own requirements, therefore
it is far from complete.

It is only tested with my own LT18 router and with my Home Assistant installation.
There's no guarantee that it's working on other systems. Feedback and pull requests are welcome.

For major changes, please open an issue first to discuss what you
would like to change.

The project uses the code style configuration from Home Assistant Core.

## License

[GNU GPLv3](https://www.gnu.org/licenses/gpl-3.0.en.html)
