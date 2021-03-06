# -*- coding: utf-8 -*-
"""
@author: Sam Schott  (ss2151@cam.ac.uk)

(c) Sam Schott; This work is licensed under a Creative Commons
Attribution-NonCommercial-NoDerivs 2.0 UK: England & Wales License.

"""

# system imports
import sys
import pkg_resources as pkgr
import time
import numpy as np
import logging
import traceback
from PyQt5 import QtCore, QtWidgets, uic

# local imports
from ..instruments.base import TempController
from .pyqt_labutils import LedIndicator, ConnectionDialog
from .pyqtplot_canvas import TemperatureHistoryPlot
from ..config.main import CONF

MAIN_UI_PATH = pkgr.resource_filename('cryocontrol', 'gui/main.ui')
logger = logging.getLogger(__name__)


class TemperatureControlGui(QtWidgets.QMainWindow):

    QUIT_ON_CLOSE = True
    MAX_DISPLAY = 24*60*60

    def __init__(self, controller: TempController):
        super(self.__class__, self).__init__()
        uic.loadUi(MAIN_UI_PATH, self)

        self.controller = controller

        # create popup Widgets
        self.connectionDialog = ConnectionDialog(self, self.controller, CONF)

        # create LED indicator
        self.led = LedIndicator(self)
        self.statusbar.addPermanentWidget(self.led)
        self.led.setChecked(False)

        # set up temperature plot, adjust window margins accordingly
        self.canvas = TemperatureHistoryPlot()
        self.gridLayoutCanvas.addWidget(self.canvas)
        w = self.canvas.y_axis_width
        self.gridLayoutTop.setContentsMargins(w, 0, w, 0)
        self.gridLayoutBottom.setContentsMargins(w, 0, w, 0)
        self.horizontalSlider.setMaximum(self.MAX_DISPLAY/60)

        # connect slider to plot
        self.horizontalSlider.valueChanged.connect(self.on_slider_changed)

        # adapt text edit colors to graph colors
        self.t1_reading.setStyleSheet('color:rgb%s' % str(self.canvas.GREEN))
        self.gf1_edit.setStyleSheet('color:rgb%s' % str(self.canvas.BLUE))
        self.h1_edit.setStyleSheet('color:rgb%s' % str(self.canvas.RED))
        self.gf1_edit.setMinimalStep(0.1)
        self.h1_edit.setMinimalStep(0.1)

        # set up data vectors for plot
        self.xdata = np.array([])
        self.xdata_min_zero = np.array([])
        self.ydata_tmpr = np.array([])
        self.ydata_gflw = np.array([])
        self.ydata_htr = np.array([])

        # restore previous window geometry
        self.restore_geometry()

        # connect to callbacks
        self.exitAction.triggered.connect(self.exit_)
        self.connectAction.triggered.connect(self.controller.connect)
        self.disconnectAction.triggered.connect(self.controller.disconnect)
        self.updateAddressAction.triggered.connect(self.connectionDialog.open)

        self.t2_edit.returnPressed.connect(self.change_t_setpoint)
        self.r1_edit.returnPressed.connect(self.change_ramp)
        self.r2_checkbox.clicked.connect(self.change_ramp_auto)
        self.gf1_edit.returnPressed.connect(self.change_flow)
        self.gf2_checkbox.clicked.connect(self.change_flow_auto)

        self.h1_edit.returnPressed.connect(self.change_heater)
        self.h2_checkbox.clicked.connect(self.change_heater_auto)

        # initially disable menu bar items, will be enabled later individually
        self.connectAction.setEnabled(True)
        self.disconnectAction.setEnabled(False)

        # initially disable controls, will be enabled later individually
        self.t2_edit.setEnabled(False)
        self.r1_edit.setEnabled(False)
        self.r2_checkbox.setEnabled(False)
        self.gf1_edit.setEnabled(False)
        self.gf2_checkbox.setEnabled(False)
        self.h1_edit.setEnabled(False)
        self.h2_checkbox.setEnabled(False)

        # check if instrument is connected
        self.display_message('Looking for temperature controller at %s...' %
                             self.controller.visa_address)

        # get new readings every second, update UI
        self.thread = DataCollectionThread(self.controller)
        self.thread.readings_signal.connect(self.update_readings)
        self.thread.readings_signal.connect(self.update_plot)
        self.thread.connected_signal.connect(self.update_gui_connection)
        self.thread.start()

# =================== BASIC UI SETUP ==========================================

    def restore_geometry(self):
        x = CONF.get('Window', 'x')
        y = CONF.get('Window', 'y')
        w = CONF.get('Window', 'width')
        h = CONF.get('Window', 'height')

        self.setGeometry(x, y, w, h)

    def save_geometry(self):
        geo = self.geometry()
        CONF.set('Window', 'height', geo.height())
        CONF.set('Window', 'width', geo.width())
        CONF.set('Window', 'x', geo.x())
        CONF.set('Window', 'y', geo.y())

    def exit_(self):
        self.controller.disconnect()
        self.save_geometry()
        self.deleteLater()

    def closeEvent(self, event):
        if self.QUIT_ON_CLOSE:
            self.thread.running = False
            self.thread.wait()
            self.exit_()
        else:
            self.hide()

    def on_slider_changed(self):
        # determine first plotted data point
        sv = self.horizontalSlider.value()

        self.timeLabel.setText('Show last %s min' % sv)
        self.canvas.set_xmin(-sv)
        self.canvas.p0.setXRange(-sv, 0)
        self.canvas.p0.enableAutoRange(x=False, y=True)

    @QtCore.pyqtSlot(bool)
    def update_gui_connection(self, connected):

        if connected:
            self.led.setChecked(True)

            # enable / disable menu bar items
            self.connectAction.setEnabled(False)
            self.disconnectAction.setEnabled(True)

            # enable controls
            self.t2_edit.setEnabled(True)
            self.r1_edit.setEnabled(True)
            self.r2_checkbox.setEnabled(True)
            self.gf1_edit.setEnabled(True)
            self.gf2_checkbox.setEnabled(True)
            self.h1_edit.setEnabled(True)
            self.h2_checkbox.setEnabled(True)

        else:
            self.display_error('Connection lost.')
            self.led.setChecked(False)

            # enable / disable menu bar items
            self.connectAction.setEnabled(True)
            self.disconnectAction.setEnabled(False)

            # disable controls
            self.t2_edit.setEnabled(False)
            self.r1_edit.setEnabled(False)
            self.r2_checkbox.setEnabled(False)
            self.gf1_edit.setEnabled(False)
            self.gf2_checkbox.setEnabled(False)

            self.h1_edit.setEnabled(False)
            self.h2_checkbox.setEnabled(False)

    def display_message(self, text):
        self.statusbar.showMessage('%s' % text, 5000)

    def display_error(self, text):
        self.statusbar.showMessage('%s' % text)

    @QtCore.pyqtSlot(object)
    def update_readings(self, readings):

        # heater signals
        self.h1_label.setText('Heater, {} V:'.format(readings.get('HeaterVolt')))
        self.h1_edit.updateValue(readings.get('HeaterPercent'))

        is_heater_auto = readings.get('HeaterAuto')
        self.h1_edit.setReadOnly(is_heater_auto)
        self.h1_edit.setEnabled(not is_heater_auto)
        self.h2_checkbox.setChecked(is_heater_auto)
        self.h2_checkbox.setEnabled(True)

        # gas flow signals
        self.gf1_edit.updateValue(readings.get('FlowPercent'))

        is_gf_auto = readings.get('FlowAuto')
        self.gf1_edit.setReadOnly(is_gf_auto)
        self.gf1_edit.setEnabled(not is_gf_auto)
        self.gf2_checkbox.setChecked(is_gf_auto)
        self.gf2_checkbox.setEnabled(True)

        # temperature signals
        self.t1_reading.setText('{} K'.format(readings.get('Temp')))
        self.t2_edit.updateValue(readings.get('TempSetpoint'))
        self.r1_edit.updateValue(readings.get('TempRamp'))

        is_ramp_enable = readings.get('TempRampEnable')
        self.r2_checkbox.setChecked(is_ramp_enable)

        # alarms
        alarms = readings.get('Alarms')
        self.alarm_label.setText(alarms)

        if alarms:
            self.alarm_label.show()
        else:
            self.alarm_label.hide()

    @QtCore.pyqtSlot(object)
    def update_plot(self, readings):
        # append data for plotting
        self.xdata = np.append(self.xdata, time.time())
        self.ydata_tmpr = np.append(self.ydata_tmpr, readings.get('Temp'))
        self.ydata_gflw = np.append(self.ydata_gflw, readings.get('FlowPercent') / 100)
        self.ydata_htr = np.append(self.ydata_htr, readings.get('HeaterPercent') / 100)

        # prevent data vector from exceeding MAX_DISPLAY
        self.xdata = self.xdata[-self.MAX_DISPLAY:]
        self.ydata_tmpr = self.ydata_tmpr[-self.MAX_DISPLAY:]
        self.ydata_gflw = self.ydata_gflw[-self.MAX_DISPLAY:]
        self.ydata_htr = self.ydata_htr[-self.MAX_DISPLAY:]

        # convert xData to minutes and set current time to t = 0
        self.xdata_min_zero = (self.xdata - self.xdata[-1]) / 60

        # update plot
        self.canvas.update_data(self.xdata_min_zero, self.ydata_tmpr,
                                self.ydata_gflw, self.ydata_htr)

    def clear_plot(self):
        # append data for plotting
        self.xdata = np.array([])
        self.xdata_min_zero = np.array([])
        self.ydata_tmpr = np.array([])
        self.ydata_gflw = np.array([])
        self.ydata_htr = np.array([])

        # update plot
        self.canvas.update_data(self.xdata, self.ydata_tmpr,
                                self.ydata_gflw, self.ydata_htr)

# =================== CALLBACKS FOR SETTING CHANGES ===========================

    @QtCore.pyqtSlot()
    def change_t_setpoint(self):
        new_t = self.t2_edit.value()

        if 0 <= new_t <= 300:
            self.controller.temperature_setpoint = new_t
            self.display_message('T_setpoint = %s K' % new_t)
        else:
            self.display_error('Error: Only temperature setpoints between ' +
                               '0 K and 300 K allowed.')

    @QtCore.pyqtSlot()
    def change_ramp(self):
        self.controller.temperature_ramp = self.r1_edit.value()
        self.display_message('Ramp = %s K/min' % self.r1_edit.value())

    @QtCore.pyqtSlot(bool)
    def change_ramp_auto(self, checked):
        self.controller.temperature_ramp_enabled = checked
        if checked:
            self.display_message('Ramp is turned ON')
        else:
            self.display_message('Ramp is turned OFF')

    @QtCore.pyqtSlot()
    def change_flow(self):
        self.controller.gasflow_setpoint = self.gf1_edit.value()
        self.display_message('Gas flow = %s%%' % self.gf1_edit.value())

    @QtCore.pyqtSlot(bool)
    def change_flow_auto(self, checked):
        if checked:
            self.controller.gasflow_auto = True
            self.display_message('Gas flow is automatically controlled.')
            self.gf1_edit.setReadOnly(True)
            self.gf1_edit.setEnabled(False)
        else:
            self.controller.gasflow_auto = False
            self.display_message('Gas flow is manually controlled.')
            self.gf1_edit.setReadOnly(False)
            self.gf1_edit.setEnabled(True)

    @QtCore.pyqtSlot()
    def change_heater(self):
        self.controller.heater_setpoint = self.h1_edit.value()
        self.display_message('Heater power  = %s%%' % self.h1_edit.value())

    @QtCore.pyqtSlot(bool)
    def change_heater_auto(self, checked):
        if checked:
            self.controller.heater_auto = True
            self.display_message('Heater is automatically controlled.')
            self.h1_edit.setReadOnly(True)
            self.h1_edit.setEnabled(False)
        else:
            self.controller.heater_auto = False
            self.display_message('Heater is manually controlled.')
            self.h1_edit.setReadOnly(False)
            self.h1_edit.setEnabled(True)


class DataCollectionThread(QtCore.QThread):

    readings_signal = QtCore.pyqtSignal(object)
    connected_signal = QtCore.pyqtSignal(bool)

    def __init__(self, controller, refresh=1):
        super().__init__()

        self.refresh = refresh
        self.controller = controller
        self.running = True
        self._connection_lost = True

        self.connected_signal.emit(self.controller.connected)

    def run(self):

        while self.running:
            try:
                readings = self.get_readings()
                # emit readings
                self.readings_signal.emit(readings)
                if self._connection_lost:
                    self.connected_signal.emit(True)
                    self._connection_lost = False
            except ConnectionError:
                self.connected_signal.emit(False)
                self._connection_lost = True
                logger.info('Connection to instrument lost.')
            except Exception:
                traceback.print_exc()
                logger.exception('Error when getting readings')

            QtCore.QThread.sleep(int(self.refresh))

    def get_readings(self):

        readings = {}

        # read temperature data
        readings['Temp'] = self.controller.temperature
        readings['TempSetpoint'] = self.controller.temperature_setpoint
        readings['TempRamp'] = self.controller.temperature_ramp
        readings['TempRampEnable'] = self.controller.temperature_ramp_enabled

        # read heater data
        readings['HeaterVolt'] = self.controller.heater_volt
        readings['HeaterAuto'] = self.controller.heater_auto
        readings['HeaterPercent'] = self.controller.heater_setpoint

        readings['FlowAuto'] = self.controller.gasflow_auto
        readings['FlowPercent'] = self.controller.gasflow
        readings['FlowSetpoint'] = self.controller.gasflow_setpoint

        # read alarms
        alarms = self.controller.alarms
        readings['Alarms'] = str(alarms) if alarms else ''

        return readings


def run():

    from ..instruments import ITC503
    from ..config.main import CONF

    app = QtWidgets.QApplication(sys.argv)

    address = CONF.get('Connection', 'VISA_ADDRESS')
    lib = CONF.get('Connection', 'VISA_LIBRARY')

    itc = ITC503(address, lib, open_timeout=1)

    gui = TemperatureControlGui(itc)
    gui.show()

    app.exec_()


if __name__ == '__main__':
    run()
