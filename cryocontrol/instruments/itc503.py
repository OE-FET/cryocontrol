# -*- coding: utf-8 -*-
"""
@author: Sam Schott  (ss2151@cam.ac.uk)

(c) Sam Schott; This work is licensed under a Creative Commons
Attribution-NonCommercial-NoDerivs 2.0 UK: England & Wales License.

"""
import re
from .base import TempController


class Itc503(TempController):

    def __init__(self, visa_address, visa_library='@py', **kwargs):
        super().__init__(visa_address, visa_library, read_termination='\r', **kwargs)

    def connect(self, **kwargs):
        super().connect(**kwargs)

        if self.connected:
            self.connection.write('Q0')  # read termination with CR
            self.connection.query('C3')  # set to remote mode

    def _get_status(self):
        status = self.connection.query('X')
        pattern = ('(?P<system>X\d)(?P<auto>A\d)(?P<lock>C\d)'
                   '(?P<sweep>S\d{1,2})(?P<control_sensor>H\d)(?P<auto_pid>L\d)')
        match = re.fullmatch(pattern, status)
        return match.groupdict()

    def _read_channel(self, number):
        resp = self.connection.query('R{:.0f}'.format(number))
        return float(resp[1:])

    def select_temp_module(self, name):
        """
        Updates module list after the new modules have been selected. Only applicable
        for temperature controllers which handle multiple cryostats and PID loops.

        :param str name: Name of module to select.
        """
        if name not in ('1', '2', '3'):
            raise ValueError("Sensor name must be '1', '2' or '3'")
        self.connection.query('H{}'.format(name))

    def select_heater_module(self, name):
        """
        Selects the heater module to use.

        :param str name: Name of module to select.
        """
        raise NotImplementedError('The current instrument does not support this')

    def select_gasflow_module(self, name):
        """
        Selects the gasflow module to use.

        :param str name: Name of module to select.
        """
        raise NotImplementedError('The current instrument does not support this')

    @property
    def temperature(self):
        """Returns the current temperature in Kelvin."""
        return self._read_channel(1)

    @property
    def temperature_setpoint(self):
        """Current temperature setpoint in Kelvin."""
        return self._read_channel(0)

    @temperature_setpoint.setter
    def temperature_setpoint(self, value):
        """Setter: Current temperature setpoint in Kelvin."""
        if not 0 <= value <= 300:
            raise ValueError('Temperature must be between 0 K and 300 K')

        value = round(value, 2)
        self.connection.query('T{}'.format(str(value)))

    @property
    def temperature_ramp(self):
        """Temperature ramp speed in Kelvin / min."""
        return 0

    @temperature_ramp.setter
    def temperature_ramp(self, value):
        """Setter: Temperature ramp speed in Kelvin / min."""
        raise NotImplementedError('The current instrument does not support this')

    @property
    def temperature_ramp_enabled(self):
        """Temperature ramp enabled."""
        return False

    @temperature_ramp_enabled.setter
    def temperature_ramp_enabled(self, value):
        """Setter: Temperature ramp enabled."""
        raise NotImplementedError('The current instrument does not support this')

    @property
    def heater_volt(self):
        """Current heater voltage in Volts."""
        return self._read_channel(6)

    @property
    def heater_auto(self):
        """Automatic heater control enabled / disabled."""
        status = self._get_status()
        if status['auto'] in ('A1', 'A3'):  # heater auto
            return True
        else:
            return False

    @heater_auto.setter
    def heater_auto(self, value):
        """Setter: Automatic heater control enabled / disabled."""
        status = self._get_status()
        if status['auto'] in ('A0', 'A1'):  # gas manual
            if value:
                self.connection.query('A1')  # heater auto, gas manual
            else:
                self.connection.query('A0')  # heater manual, gas manual
        else:  # gas auto
            if value:
                self.connection.query('A3')  # heater auto, gas auto
            else:
                self.connection.query('A2')  # heater manual, gas auto

    @property
    def heater_setpoint(self):
        """Heater setpoint in percent of maximum voltage."""
        # return the actual heater percent, not the setpoint
        return self._read_channel(5)

    @heater_setpoint.setter
    def heater_setpoint(self, value):
        """Setter: Heater setpoint in percent of maximum voltage."""
        if not 0 <= value <= 99.9:
            raise ValueError('Heater output must be between 0 and 99.9%')
        value = round(value, 1)
        self.connection.query('O{}'.format(str(value)))

    @property
    def gasflow(self):
        """Current gasflow in percent."""
        return self._read_channel(7)

    @property
    def gasflow_auto(self):
        """Automatic gasflow control enabled / disabled."""
        status = self._get_status()
        if status['auto'] in ('A2', 'A3'):  # gas auto
            return True
        else:
            return False

    @gasflow_auto.setter
    def gasflow_auto(self, value):
        """Setter: Automatic gasflow control enabled / disabled."""
        status = self._get_status()
        if status['auto'] in ('A0', 'A2'):  # heater manual
            if value:
                self.connection.query('A2')  # heater manual, gas auto
            else:
                self.connection.query('A0')  # heater manual, gas manual
        else:  # heater auto
            if value:
                self.connection.query('A3')  # heater auto, gas auto
            else:
                self.connection.query('A1')  # heater auto, gas manual

    @property
    def gasflow_setpoint(self):
        """Gasflow setpoint in percent."""
        # return the actual gasflow instead
        return self.gasflow

    @gasflow_setpoint.setter
    def gasflow_setpoint(self, value):
        """Setter: Gasflow setpoint in percent."""
        if not 0 <= value <= 99.9:
            raise ValueError('Gas flow must be between 0 and 99.9%')

        value = round(value, 1)
        self.connection.query('G{}'.format(str(value)))

    @property
    def alarms(self):
        return dict()
