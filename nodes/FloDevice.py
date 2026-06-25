
from udi_interface import LOGGER, Node

from const import (
    MODE_INDEX_TO_NAME,
    SYSTEM_MODE_INDEX,
    UOM_BOOL,
    UOM_DBM,
    UOM_GPM,
    UOM_INDEX,
    UOM_PSI,
    UOM_RAW,
    UOM_TEMP_F,
    VALVE_CLOSED,
    VALVE_INDEX_TO_TARGET,
    VALVE_OPEN,
)


def _safe_float(value, prec=2):
    if value is None:
        return 0.0
    try:
        return round(float(value), prec)
    except (TypeError, ValueError):
        return 0.0


def _valve_index(valve_state):
    if valve_state in ('open', 'opening'):
        return VALVE_OPEN
    return VALVE_CLOSED


def _system_mode_index(mode):
    if mode is None:
        return SYSTEM_MODE_INDEX['home']
    return SYSTEM_MODE_INDEX.get(str(mode).lower(), SYSTEM_MODE_INDEX['home'])


class FloDevice(Node):
    def __init__(self, controller, primary, address, name, device_id, location_id, device_info):
        super().__init__(controller.poly, primary, address, name)
        self.controller = controller
        self.device_id = device_id
        self.location_id = location_id
        self.lpfx = f'{address}:{name}'
        controller.poly.subscribe(controller.poly.START, self.handler_start, address)
        self.update_from_dict(device_info)

    def handler_start(self):
        LOGGER.debug('%s: start', self.lpfx)
        self._ensure_driver_uoms()
        self.update()

    def _ensure_driver_uoms(self):
        """Re-report drivers with correct UOMs (clears stale IoX DB units)."""
        defaults = {
            'ST': (VALVE_CLOSED, UOM_INDEX),
            'GV1': (0, UOM_BOOL),
            'GV2': (0, UOM_GPM),
            'GV3': (0, UOM_PSI),
            'GV4': (0, UOM_TEMP_F),
            'GV5': (SYSTEM_MODE_INDEX['home'], UOM_INDEX),
            'GV6': (0, UOM_DBM),
            'GV7': (0, UOM_RAW),
            'GV8': (0, UOM_RAW),
        }
        for driver, (default, uom) in defaults.items():
            value = self.getDriver(driver)
            if value is None:
                value = default
            self.setDriver(driver, value, uom=uom, force=True)

    def long_poll(self):
        self.update()

    def run_api(self, coro):
        return self.controller.run_async(coro)

    def update_from_dict(self, info):
        if not info:
            return
        connected = 1 if info.get('isConnected') else 0
        self.setDriver('GV1', connected, uom=UOM_BOOL)
        telemetry = info.get('telemetry', {}).get('current', {})
        self.setDriver('GV2', _safe_float(telemetry.get('gpm')), uom=UOM_GPM)
        self.setDriver('GV3', _safe_float(telemetry.get('psi')), uom=UOM_PSI)
        self.setDriver('GV4', _safe_float(telemetry.get('tempF'), prec=1), uom=UOM_TEMP_F)
        valve = info.get('valve', {})
        valve_target = valve.get('target') or valve.get('lastKnown')
        self.setDriver('ST', _valve_index(valve_target), uom=UOM_INDEX)
        system_mode = info.get('systemMode', {})
        mode = system_mode.get('target') or system_mode.get('lastKnown')
        self.setDriver('GV5', _system_mode_index(mode), uom=UOM_INDEX)
        connectivity = info.get('connectivity', {})
        rssi = connectivity.get('rssi')
        if rssi is not None:
            self.setDriver('GV6', int(rssi), uom=UOM_DBM)
        notifications = info.get('notifications', {}).get('pending', {})
        self.setDriver('GV7', int(notifications.get('warningCount', 0)), uom=UOM_RAW)
        self.setDriver('GV8', int(notifications.get('criticalCount', 0)), uom=UOM_RAW)

    def update(self):
        if self.controller.api is None:
            return
        try:
            info = self.run_api(self.controller.api.device.get_info(self.device_id))
            self.update_from_dict(info)
        except Exception as ex:
            LOGGER.error('%s: update failed: %s', self.lpfx, ex, exc_info=True)

    def query(self, command=None):
        self.update()
        self.reportDrivers()

    def set_valve(self, command=None):
        if command is None:
            command = {}
        try:
            value = int(command.get('value', self.getDriver('ST')))
        except (TypeError, ValueError):
            value = VALVE_CLOSED
        target = VALVE_INDEX_TO_TARGET.get(value, 'closed')
        self._valve_command(target)

    def _valve_command(self, target):
        if self.controller.api is None:
            return
        try:
            if target == 'open':
                self.run_api(self.controller.api.device.open_valve(self.device_id))
            else:
                self.run_api(self.controller.api.device.close_valve(self.device_id))
            self.update()
        except Exception as ex:
            LOGGER.error('%s: valve %s failed: %s', self.lpfx, target, ex, exc_info=True)

    def health_test(self, command=None):
        if self.controller.api is None:
            return
        try:
            self.run_api(self.controller.api.device.run_health_test(self.device_id))
            LOGGER.info('%s: health test started', self.lpfx)
        except Exception as ex:
            LOGGER.error('%s: health test failed: %s', self.lpfx, ex, exc_info=True)

    def set_mode(self, command=None):
        if command is None:
            command = {}
        try:
            value = int(command.get('value', self.getDriver('GV5')))
        except (TypeError, ValueError):
            value = SYSTEM_MODE_INDEX['home']
        mode = MODE_INDEX_TO_NAME.get(value, 'home')
        self._set_mode(mode)

    def _set_mode(self, mode):
        if self.controller.api is None:
            return
        try:
            if mode == 'home':
                self.run_api(self.controller.api.location.set_mode_home(self.location_id))
            elif mode == 'away':
                self.run_api(self.controller.api.location.set_mode_away(self.location_id))
            else:
                self.run_api(
                    self.controller.api.location.set_mode_sleep(
                        self.location_id, 120, 'away'
                    )
                )
            self.update()
        except Exception as ex:
            LOGGER.error('%s: set mode %s failed: %s', self.lpfx, mode, ex, exc_info=True)

    # Hints: home / Relay / Open-Close Valve — https://github.com/UniversalDevicesInc/hints
    hint = [1, 4, 5, 0]

    id = 'modev'
    drivers = [
        {'driver': 'ST', 'value': VALVE_CLOSED, 'uom': UOM_INDEX},
        {'driver': 'GV1', 'value': 0, 'uom': UOM_BOOL},
        {'driver': 'GV2', 'value': 0, 'uom': UOM_GPM},
        {'driver': 'GV3', 'value': 0, 'uom': UOM_PSI},
        {'driver': 'GV4', 'value': 0, 'uom': UOM_TEMP_F},
        {'driver': 'GV5', 'value': SYSTEM_MODE_INDEX['home'], 'uom': UOM_INDEX},
        {'driver': 'GV6', 'value': 0, 'uom': UOM_DBM},
        {'driver': 'GV7', 'value': 0, 'uom': UOM_RAW},
        {'driver': 'GV8', 'value': 0, 'uom': UOM_RAW},
    ]
    commands = {
        'QUERY': query,
        'SET_VALVE': set_valve,
        'HEALTH': health_test,
        'SET_MODE': set_mode,
    }
