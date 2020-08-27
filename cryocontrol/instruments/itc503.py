# -*- coding: utf-8 -*-
"""
@author: Sam Schott  (ss2151@cam.ac.uk)

(c) Sam Schott; This work is licensed under a Creative Commons
Attribution-NonCommercial-NoDerivs 2.0 UK: England & Wales License.

"""
import time
import threading
import re
from .base import TempController


def sign(x):
    return (1, -1)[x < 0]


class ITC503(TempController):

    _status_pattern = re.compile('(?P<system>X\d)(?P<auto>A\d)(?P<lock>C\d)'
                                 '(?P<sweep>S\d{1,2})(?P<control_sensor>H\d)'
                                 '(?P<auto_pid>L\d)')

    def __init__(self, visa_address, visa_library='@py', **kwargs):
        super().__init__(visa_address, visa_library, read_termination='\r\n', **kwargs)
        self._last_status = 0
        self._cached_status = None
        self._ramp_speed = 5  # in Kelvin / min
        self._ramp_enabled = False
        self._cancel_ramp = threading.Event()
        self._ramp_thread = None

    def connect(self, **kwargs):
        super().connect(**kwargs)

        if self.connected:
            self.write('Q2')  # read termination with CR
            self.query('C3')  # set to remote mode

    def _get_status(self):

        with self._lock:

            if time.time() - self._last_status > 1 or not self._cached_status:
                status = self.query('X')
                match = re.fullmatch(self._status_pattern, status)
                self._cached_status = match.groupdict()
                self._last_status = time.time()

            return self._cached_status

    def _read_channel(self, number):
        resp = self.query('R{:.0f}'.format(number))
        if resp.startswith('?'):
            raise IOError('Bad response: "{}"'.format(resp))

        numeric = ''.join(list(filter(lambda s: s in '0123456789.', resp)))
        return float(numeric)

    def select_temp_module(self, name):
        if name not in self.get_temp_modules():
            raise ValueError("Sensor name must be '1', '2' or '3'")
        self.query('H{}'.format(name))

    def get_temp_modules(self):
        return ['1', '2', '3']

    def select_heater_module(self, name):
        raise NotImplementedError('The current instrument does not support this')

    def get_heater_modules(self):
        return ['1', '2', '3']

    def select_gasflow_module(self, name):
        raise NotImplementedError('The current instrument does not support this')

    def get_gasflow_modules(self):
        return ['1']

    @property
    def temperature(self):
        return self._read_channel(1)

    @property
    def temperature_setpoint(self):
        return self._read_channel(0)

    @temperature_setpoint.setter
    def temperature_setpoint(self, value):

        if not 0 <= value <= 300:
            raise ValueError('Temperature must be between 0 K and 300 K')

        value = round(value, 2)

        if not self._ramp_enabled:
            self.query('T{}'.format(str(value)))
        else:

            # cancel previous ramp
            self._cancel_ramp.set()
            if self._ramp_thread:
                self._ramp_thread.join()

            # start new ramp
            self._ramp_thread = threading.Thread(
                target=self._ramp_to_temperature,
                args=(value,),
                name='ITC503-temperature-ramp'
            )

    @property
    def temperature_ramp(self):
        return self._ramp_speed

    @temperature_ramp.setter
    def temperature_ramp(self, value):
        if self._ramp_speed <= 0:
            raise ValueError('Temperature ramp must be larger than 0 K/min')
        self._ramp_speed = value

    @property
    def temperature_ramp_enabled(self):
        return self._ramp_enabled

    @temperature_ramp_enabled.setter
    def temperature_ramp_enabled(self, value):
        self._ramp_enabled = bool(value)

    @property
    def heater_volt(self):
        return self._read_channel(6)

    @property
    def heater_auto(self):
        status = self._get_status()
        if status['auto'] in ('A1', 'A3'):  # heater auto
            return True
        else:
            return False

    @heater_auto.setter
    def heater_auto(self, value):
        status = self._get_status()
        if status['auto'] in ('A0', 'A1'):  # gas manual
            if value:
                self.query('A1')  # heater auto, gas manual
            else:
                self.query('A0')  # heater manual, gas manual
        else:  # gas auto
            if value:
                self.query('A3')  # heater auto, gas auto
            else:
                self.query('A2')  # heater manual, gas auto

    @property
    def heater_setpoint(self):
        # return the actual heater percent, not the setpoint
        return self._read_channel(5)

    @heater_setpoint.setter
    def heater_setpoint(self, value):
        if not 0 <= value <= 99.9:
            raise ValueError('Heater output must be between 0 and 99.9%')
        value = round(value, 1)
        self.query('O{}'.format(str(value)))

    @property
    def gasflow(self):
        return self._read_channel(7)

    @property
    def gasflow_auto(self):
        status = self._get_status()
        if status['auto'] in ('A2', 'A3'):  # gas auto
            return True
        else:
            return False

    @gasflow_auto.setter
    def gasflow_auto(self, value):
        status = self._get_status()
        if status['auto'] in ('A0', 'A2'):  # heater manual
            if value:
                self.query('A2')  # heater manual, gas auto
            else:
                self.query('A0')  # heater manual, gas manual
        else:  # heater auto
            if value:
                self.query('A3')  # heater auto, gas auto
            else:
                self.query('A1')  # heater auto, gas manual

    @property
    def gasflow_setpoint(self):
        # return the actual gasflow instead
        return self.gasflow

    @gasflow_setpoint.setter
    def gasflow_setpoint(self, value):
        if not 0 <= value <= 99.9:
            raise ValueError('Gas flow must be between 0 and 99.9%')

        value = round(value, 1)
        self.query('G{}'.format(str(value)))

    @property
    def alarms(self):
        return dict()

    def _ramp_to_temperature(self, target):

        self._cancel_ramp.clear()

        current = self.temperature_setpoint

        while self._ramp_enabled and not self._cancel_ramp.is_set() \
                and round(current, 2) != target:
            if self._ramp_enabled:
                step = sign(target - current) * self._ramp_speed / 60  # in Kelvin / sec
                current += step
                self.query('T{}'.format(str(round(current, 2))))
                time.sleep(1)
            else:
                self.query('T{}'.format(str(round(current, 2))))
                self._cancel_ramp.set()
