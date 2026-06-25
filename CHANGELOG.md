# Changelog

## 1.0.0

- Initial release
- Moen Flo cloud authentication via aioflo (email/password)
- Discovery of smart water shutoff devices per location
- Shutoff **ST** status: valve Open / Closed
- Mode selector: Home, Away, Sleep
- Telemetry: flow rate, pressure, temperature, alerts
- Commands: Set Valve selector (Closed/Open), health test, Set Mode selector (Home/Away/Sleep)
- Fix asyncio event loop for aiohttp session creation
- IoX icons: Irrigation shutoff, GenericCtl controller; Open/Close Valve hint
- Correct IoX UOMs for flow, pressure, RSSI, and alert counts
