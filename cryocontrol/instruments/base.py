# -*- coding: utf-8 -*-
"""
@author: Sam Schott  (ss2151@cam.ac.uk)

(c) Sam Schott; This work is licensed under a Creative Commons
Attribution-NonCommercial-NoDerivs 2.0 UK: England & Wales License.

"""
import threading
from enum import Enum
import pyvisa
from abc import ABC, abstractmethod
from typing import List


class Control(Enum):
    Auto = 0
    Manual = 1


class TempController(ABC):

    def __init__(self, visa_address: str, visa_library: str='@py', **kwargs) -> None:
        self._lock = threading.RLock()
        self.visa_address = visa_address
        self.visa_library = visa_library
        self._connection_kwargs = kwargs
        self.rm = pyvisa.ResourceManager(self.visa_library)
        self.connect(**kwargs)

    def connect(self, **kwargs) -> None:

        kwargs = kwargs or self._connection_kwargs  # use specified or remembered kwargs

        with self._lock:
            try:
                self.connection = self.rm.open_resource(self.visa_address, **kwargs)
            except ConnectionError:
                print('Connection to the instrument failed. Please check ' +
                      'that no other program is connected.')
                self.connection = None
            except AttributeError:
                print('Invalid VISA address {}.'.format(self.visa_address))
                self.connection = None
            except Exception as exc:
                print('Could not connect to {}: {}'.format(self.visa_address, exc))
                self.connection = None

    def disconnect(self) -> None:

        with self._lock:
            if self.connection:
                self.connection.close()
                self.connection = None

    @property
    def connected(self) -> bool:
        return self.connection is not None

    def query(self, value: str) -> str:
        with self._lock:
            try:
                return self.connection.query(value)
            except Exception:
                raise ConnectionError('Connection to the instrument failed')

    def read(self) -> str:
        with self._lock:
            try:
                return self.connection.read()
            except Exception:
                raise ConnectionError('Connection to the instrument failed')

    def write(self, value: str) -> None:
        with self._lock:
            try:
                self.connection.write(value)
            except Exception:
                raise ConnectionError('Connection to the instrument failed')

    def __repr__(self) -> str:
        return '<{}({})>'.format(type(self).__name__, self.visa_address)

    # ABSTRACT METHODS

    @abstractmethod
    def select_temp_module(self, name: str) -> None:
        """
        Updates module list after the new modules have been selected. Only applicable
        for temperature controllers which handle multiple cryostats and PID loops.

        :param str name: Name of module to select.
        """
        raise NotImplementedError()

    @abstractmethod
    def get_temp_modules(self) -> List[str]:
        """
        Returns a list of all available temperature sensors.
        """
        raise NotImplementedError()

    @abstractmethod
    def select_heater_module(self, name: str) -> None:
        """
        Selects the heater module to use for the current temperature sensor.

        :param str name: Name of module to select.
        """
        raise NotImplementedError()

    @abstractmethod
    def get_heater_modules(self) -> List[str]:
        """
        Returns a list of all available heaters.
        """
        raise NotImplementedError()

    @abstractmethod
    def select_gasflow_module(self, name: str) -> None:
        """
        Selects the gasflow module to use for the current temperature sensor.

        :param str name: Name of module to select.
        """
        raise NotImplementedError()

    @abstractmethod
    def get_gasflow_modules(self) -> List[str]:
        """
        Returns a list of all available gas flow modules.
        """
        raise NotImplementedError()

    @property
    @abstractmethod
    def temperature(self) -> float:
        """Returns the current temperature in Kelvin."""
        raise NotImplementedError()

    @property
    @abstractmethod
    def temperature_setpoint(self) -> float:
        """Current temperature setpoint in Kelvin."""
        raise NotImplementedError()

    @temperature_setpoint.setter
    @abstractmethod
    def temperature_setpoint(self, value: float):
        """Setter: Current temperature setpoint in Kelvin."""
        raise NotImplementedError()

    @property
    @abstractmethod
    def temperature_ramp(self) -> float:
        """Temperature ramp speed in Kelvin / min."""
        raise NotImplementedError()

    @temperature_ramp.setter
    @abstractmethod
    def temperature_ramp(self, value: float):
        """Setter: Temperature ramp speed in Kelvin / min."""
        raise NotImplementedError()

    @property
    @abstractmethod
    def temperature_ramp_enabled(self) -> bool:
        """Temperature ramp enabled."""
        raise NotImplementedError()

    @temperature_ramp_enabled.setter
    @abstractmethod
    def temperature_ramp_enabled(self, value: bool):
        """Setter: Temperature ramp enabled."""
        raise NotImplementedError()

    @property
    @abstractmethod
    def heater_volt(self) -> float:
        """Current heater voltage in Volts."""
        raise NotImplementedError()

    @property
    @abstractmethod
    def heater_auto(self) -> bool:
        """Automatic heater control enabled / disabled."""
        raise NotImplementedError()

    @heater_auto.setter
    @abstractmethod
    def heater_auto(self, value: bool):
        """Setter: Automatic heater control enabled / disabled."""
        raise NotImplementedError()

    @property
    @abstractmethod
    def heater_setpoint(self) -> float:
        """Heater setpoint in percent of maximum voltage."""
        raise NotImplementedError()

    @heater_setpoint.setter
    @abstractmethod
    def heater_setpoint(self, value: float):
        """Setter: Heater setpoint in percent of maximum voltage."""
        raise NotImplementedError()

    @property
    @abstractmethod
    def gasflow(self) -> float:
        """Current gasflow in percent."""
        raise NotImplementedError()

    @property
    @abstractmethod
    def gasflow_auto(self) -> bool:
        """Automatic gasflow control enabled / disabled."""
        raise NotImplementedError()

    @gasflow_auto.setter
    @abstractmethod
    def gasflow_auto(self, value: bool):
        """Setter: Automatic gasflow control enabled / disabled."""
        raise NotImplementedError()

    @property
    @abstractmethod
    def gasflow_setpoint(self) -> float:
        """Gasflow setpoint in percent."""
        raise NotImplementedError()

    @gasflow_setpoint.setter
    @abstractmethod
    def gasflow_setpoint(self, value: float) -> None:
        """Setter: Gasflow setpoint in percent."""
        raise NotImplementedError()

    @property
    @abstractmethod
    def alarms(self) -> dict:
        raise NotImplementedError()
