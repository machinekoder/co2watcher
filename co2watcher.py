import time
import logging
from threading import Event, Lock, Thread

import hid


class Co2Monitor:
    def __init__(self) -> None:
        self._logger = logging.getLogger(Co2Monitor.__name__)
        self._device = None

        self._timestamp = 0
        self._co2 = 0
        self._temperature = 0.0

        self._stop_event = Event()
        self._data_lock = Lock()
        self._thread = None
        self.new_data_event = Event()

    def _open(self):
        self._logger.info("Opening device...")
        vendor_id = 0x04D9
        product_id = 0xA052
        self._device = hid.device()
        try:
            self._device.open(vendor_id, product_id)
            self._device.send_feature_report(
                [0x00, 0x00]
            )  # Don't understand why we should send two 0 to put the device in read mode ...
        except OSError as e:
            raise ReadError("Opening device failed") from e

    def _read_data(self):
        """Read current data from device. Return only when the whole data set is ready.
        Returns:
            float, float, float: time [Unix timestamp], co2 [ppm], and temperature [°C]
        """

        # It takes multiple reading from the device to read both co2 and temperature
        co2 = t = None
        while co2 is None or t is None:

            try:
                data = list(
                    self._device.read(8, 10000)
                )  # Times out after 10 s to avoid blocking permanently the thread
            except KeyboardInterrupt:
                self._exit()
                return
            except OSError as e:
                self._logger.error(
                    'Could not read the device, check that it is correctly plugged:', e
                )
                self._exit()
                return

            if len(data) < 3:
                self._logger.debug("Received incomplete data: {}".format(data))
                continue
            key = data[0]
            value = data[1] << 8 | data[2]
            if key == 0x50:
                co2 = value
            elif key == 0x42:
                t = value / 16.0 - 273.15

        return time.time(), co2, t

    def get_data(self):
        with self._data_lock:
            return self._timestamp, self._co2, self._temperature

    def start(self):
        if self._thread:
            return
        self._stop_event.clear()
        self._thread = Thread(
            target=self._worker_thread, args=(self,), name="Worker Thread"
        )
        self._thread.start()

    def stop(self):
        if self._thread:
            self._stop_event.set()
            self._thread.join()
            self._thread = None

    @staticmethod
    def _worker_thread(self):
        while not self._stop_event.is_set():
            try:
                self._open()
                while not self._stop_event.is_set():
                    self._read_loop()
            except ReadError as e:
                self._logger.error(e)
                time.sleep(3.0)
        self._exit()

    def _read_loop(self):
        data = self._read_data()
        if not data:
            raise ReadError("Reading from device failed")
        timestamp, co2, temperature = data
        with self._data_lock:
            self._timestamp = timestamp
            self._co2 = co2
            self._temperature = temperature

        self._logger.debug("read data {} {}".format(co2, temperature))
        self.new_data_event.set()

    def _exit(self):
        self._logger.info("Closing device")
        self._device.close()


class ReadError(Exception):
    pass
