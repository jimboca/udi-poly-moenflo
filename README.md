# Moen Flo Node Server

Polyglot v3 Node Server for **Flo by Moen** smart water shutoff devices.

Uses the [aioflo](https://github.com/bachya/aioflo) Python library to connect to the Moen Flo cloud API.

## Features

- Monitor flow rate (GPM), water pressure (PSI), and temperature
- Valve open/closed status and cloud connectivity
- System mode (Home / Away / Sleep)
- Warning and critical alert counts
- Commands: open/close valve, run health test, set Home/Away mode
- Automatic discovery of shutoff devices at each Flo location

## Requirements

- Python 3.9+
- Moen Flo account (email and password used in the Flo mobile app)
- Polyglot v3 (Polisy / eISY)

## Installation

1. Add the plugin from the PG3 store.
2. Configure **Custom Configuration Parameters** (see [CONFIG.md](CONFIG.md)).

## IoX Nodes

| Node | Description |
|------|-------------|
| **Moen Flo Controller** | Bridge; authorization status and device count |
| **Moen Flo Shutoff** | One node per smart water shutoff (address = device MAC) |

## License

MIT — see [LICENSE](LICENSE).
