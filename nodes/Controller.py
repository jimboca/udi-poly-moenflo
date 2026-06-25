
import asyncio
import logging
import time
from pathlib import Path
from threading import Thread

import markdown2
from aiohttp import ClientSession
from aioflo import async_get_api
from aioflo.errors import RequestError

from udi_interface import Custom, LOGGER, LOG_HANDLER, Node

from const import AUTH_AUTHORIZED, AUTH_FAILED, AUTH_NOT_STARTED, AUTH_STARTED
from node_funcs import device_address, get_valid_node_name
from .FloDevice import FloDevice

mainloop = asyncio.new_event_loop()


class Controller(Node):
    def __init__(self, poly, primary, address, name):
        super().__init__(poly, primary, address, name)
        self.hb = 0
        self.api = None
        self.session = None
        self.connect_st = AUTH_NOT_STARTED
        self.handler_params_st = None
        self.handler_add_node_done_st = False
        self.n_queue = []
        self.loop_thread = None
        self.Notices = Custom(poly, 'notices')
        self.Params = Custom(poly, 'customparams')
        poly.subscribe(poly.START, self.handler_start, address)
        poly.subscribe(poly.POLL, self.handler_poll)
        poly.subscribe(poly.CUSTOMPARAMS, self.handler_custom_params)
        poly.subscribe(poly.LOGLEVEL, self.handler_log_level)
        poly.subscribe(poly.CONFIGDONE, self.handler_config_done)
        poly.subscribe(poly.ADDNODEDONE, self.handler_add_node_done)
        poly.subscribe(poly.DISCOVER, self.discover)
        self.Notices.clear()
        poly.ready()
        poly.addNode(self, conn_status='ST')

    def run_async(self, coro, timeout=30):
        self._ensure_loop_running()
        future = asyncio.run_coroutine_threadsafe(coro, mainloop)
        return future.result(timeout=timeout)

    def _ensure_loop_running(self):
        if self.loop_thread is not None and self.loop_thread.is_alive():
            return
        asyncio.set_event_loop(mainloop)
        try:
            mainloop.set_exception_handler(self._asyncio_exception_handler)
        except Exception as ex:
            LOGGER.debug('asyncio exception handler not installed: %s', ex)
        self.loop_thread = Thread(target=mainloop.run_forever, daemon=True)
        self.loop_thread.start()

    def handler_start(self):
        LOGGER.info('Started Moen Flo NodeServer %s', self.poly.serverdata.get('version'))
        self._ensure_loop_running()
        self.setDriver('ST', 1)
        configuration_help = Path(__file__).resolve().parent.parent / 'CONFIG.md'
        if configuration_help.is_file():
            try:
                self.poly.setCustomParamsDoc(
                    markdown2.markdown_path(
                        str(configuration_help),
                        extras=['tables', 'fenced-code-blocks'],
                    )
                )
            except Exception:
                LOGGER.exception('Failed to convert/set CONFIG.md as custom params doc')
        else:
            LOGGER.warning('CONFIG.md not found')
        self.heartbeat(0)

    def _asyncio_exception_handler(self, loop, context):
        msg = context.get('message', 'asyncio error')
        exc = context.get('exception')
        if exc is not None:
            LOGGER.error('%s: %s', msg, exc, exc_info=exc)
        else:
            LOGGER.error('%s context=%s', msg, context)

    def handler_add_node_done(self, data):
        LOGGER.debug('add_node_done: %s', data)
        if data.get('address') == self.address:
            if self.connect():
                self.discover()
            self.handler_add_node_done_st = True
        if isinstance(data, dict) and data.get('address'):
            self._node_queue_pop(data['address'])

    def _node_queue_pop(self, address):
        if self.n_queue and self.n_queue[0] == address:
            self.n_queue.pop(0)

    def wait_for_node_done(self, address):
        self.n_queue.append(address)
        while address in self.n_queue:
            time.sleep(0.1)

    def handler_config_done(self):
        self.poly.addLogLevel('DEBUG_MODULES', 9, 'Debug + Modules')

    def handler_log_level(self, level):
        if level['level'] < 10:
            LOG_HANDLER.set_basic_config(True, logging.DEBUG)
        else:
            LOG_HANDLER.set_basic_config(True, logging.WARNING)

    def handler_poll(self, polltype):
        if not self.handler_add_node_done_st:
            return
        if polltype == 'longPoll':
            self.heartbeat()
            if self.connect_st == AUTH_FAILED:
                self.connect()
        elif polltype == 'shortPoll':
            if self.connect_st == AUTH_FAILED:
                self.connect()
            elif self.connect_st == AUTH_AUTHORIZED:
                for node in self.poly.nodes():
                    if node.address != self.address and hasattr(node, 'long_poll'):
                        try:
                            node.long_poll()
                        except Exception:
                            LOGGER.error('long_poll failed for %s', node.address, exc_info=True)

    def handler_custom_params(self, data):
        LOGGER.debug('custom_params: %s', data)
        defaults = {
            'username': 'YourFloEmail',
            'password': 'YourFloPassword',
        }
        if data is None:
            self.Params['username'] = defaults['username']
            return
        self.Params.load(data)
        ok = True
        for param, placeholder in defaults.items():
            if param not in data:
                self.Params[param] = placeholder
                return
            if not data[param] or data[param] == placeholder:
                msg = f'Please set Moen Flo {param}'
                LOGGER.error(msg)
                self.Notices[param] = msg
                ok = False
            else:
                self.Notices.delete(param)
        self.handler_params_st = ok
        if ok and self.handler_add_node_done_st:
            if self.connect():
                self.discover()

    def set_connect_st(self, value):
        self.connect_st = value
        self.setDriver('GV1', value)

    async def _async_connect(self):
        """Create aiohttp session and authenticate on the asyncio loop thread."""
        if self.session is not None and not self.session.closed:
            await self.session.close()
        self.session = ClientSession()
        return await async_get_api(
            self.Params['username'],
            self.Params['password'],
            session=self.session,
        )

    def connect(self):
        if self.handler_params_st is not True:
            LOGGER.error('Cannot connect until configuration is complete')
            return False
        self.set_connect_st(AUTH_STARTED)
        try:
            self.api = self.run_async(self._async_connect())
            self.set_connect_st(AUTH_AUTHORIZED)
            self.Notices.delete('auth')
            LOGGER.info('Moen Flo authentication succeeded')
            return True
        except (RequestError, OSError, asyncio.TimeoutError, KeyError) as ex:
            self.api = None
            self.set_connect_st(AUTH_FAILED)
            msg = f'Moen Flo authentication failed: {ex}'
            LOGGER.error(msg)
            self.Notices['auth'] = msg
            return False
        except Exception as ex:
            self.api = None
            self.set_connect_st(AUTH_FAILED)
            msg = f'Unexpected Moen Flo authentication error: {ex}'
            LOGGER.error(msg, exc_info=True)
            self.Notices['auth'] = msg
            return False

    def discover(self, command=None):
        if self.connect_st != AUTH_AUTHORIZED or self.api is None:
            LOGGER.error('Cannot discover: not connected (st=%s)', self.connect_st)
            return False
        try:
            user_info = self.run_async(
                self.api.user.get_info(include_location_info=True)
            )
            device_count = 0
            for location in user_info.get('locations', []):
                location_id = location.get('id')
                if not location_id:
                    continue
                location_info = self.run_async(
                    self.api.location.get_info(location_id, include_device_info=True)
                )
                location_name = location_info.get('nickname') or location.get('nickname') or 'Home'
                for device in location_info.get('devices', []):
                    device_id = device.get('id')
                    mac = device.get('macAddress')
                    device_type = device.get('deviceType', '')
                    if not device_id or not mac:
                        continue
                    if device_type and not str(device_type).startswith('flo_device'):
                        LOGGER.debug('Skipping non-shutoff device type %s (%s)', device_type, device_id)
                        continue
                    address = device_address(mac)
                    nickname = device.get('nickname') or 'Flo Shutoff'
                    name = get_valid_node_name(f'{location_name} {nickname}')
                    if self.poly.getNode(address):
                        existing = self.poly.getNode(address)
                        existing.device_id = device_id
                        existing.location_id = location_id
                        existing.update_from_dict(device)
                        device_count += 1
                        continue
                    node = FloDevice(
                        self,
                        self.address,
                        address,
                        name,
                        device_id,
                        location_id,
                        device,
                    )
                    self.poly.addNode(node)
                    self.wait_for_node_done(address)
                    device_count += 1
            self.setDriver('GV2', device_count)
            LOGGER.info('Discovery complete: %s device(s)', device_count)
            return True
        except Exception as ex:
            LOGGER.error('Discovery failed: %s', ex, exc_info=True)
            self.Notices['discover'] = f'Discovery failed: {ex}'
            return False

    def heartbeat(self, init=False):
        if init is not False:
            self.hb = init
        if self.hb == 0:
            self.reportCmd('DON', 2)
            self.hb = 1
        else:
            self.reportCmd('DOF', 2)
            self.hb = 0

    def query(self, command=None):
        self.reportDrivers()
        self.discover()

    id = 'controller'
    commands = {
        'QUERY': query,
        'DISCOVER': discover,
    }
    drivers = [
        {'driver': 'ST', 'value': 1, 'uom': 25},
        {'driver': 'GV1', 'value': 0, 'uom': 25},
        {'driver': 'GV2', 'value': 0, 'uom': 70},
    ]
