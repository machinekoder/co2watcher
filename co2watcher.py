import json
from os import times
import time
import hid
from threading import Event, Lock, Thread

from flask import Flask

class ReadError(Exception):
    pass

class Co2Monitor:
    def __init__(self) -> None:
        self._device = None

        self._timestamp = 0
        self._co2 = 0
        self._temperature = 0.0

        self._stop_event = Event()
        self._data_lock = Lock()
        self._thread = None
    
    def _open(self):
        print("Opening device...")
        vendor_id=0x04d9
        product_id=0xa052
        self._device = hid.device()
        try:
            self._device.open(vendor_id, product_id)
            self._device.send_feature_report([0x00, 0x00])  # Don't understand why we should send two 0 to put the device in read mode ...
        except OSError as e:
            raise ReadError("Opening device failed") from e

    def _read_data(self):
        """Read current data from device. Return only when the whole data set is ready.
        Returns:
            float, float, float: time [Unix timestamp], co2 [ppm], and temperature [°C]
        """

        # It takes multiple reading from the device to read both co2 and temperature
        co2 = t = None
        while(co2 is None or t is None):

            try:
                data = list(self._device.read(8, 10000))  # Times out after 10 s to avoid blocking permanently the thread
            except KeyboardInterrupt:
                self._exit()
                return
            except OSError as e:
                print('Could not read the device, check that it is correctly plugged:', e)
                self._exit()
                return

            key = data[0]
            value = data[1] << 8 | data[2]
            if (key == 0x50):
                co2 = value
            elif (key == 0x42):
                t = value / 16.0 - 273.15

        return time.time(), co2, t
    
    def get_data(self):
        with self._data_lock:
            return self._timestamp, self._co2, self._temperature
    
    def start(self):
        if self._thread:
            return
        self._stop_event.clear()
        self._thread = Thread(target=self._worker_thread,args=(self,), name="Worker Thread")
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
                print(e)
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
        print(f"read data {co2} {temperature}")
    
    def _exit(self):
        print("Closing device")
        self._device.close()

app = Flask(__name__)
co2Monitor = None

@app.route('/')
def entry_point():
    timestamp, co2, temperature = co2Monitor.get_data()
    return json.dumps({'timestamp': int(timestamp), 'co2': co2, 'temperature': round(temperature, ndigits=1)})

if __name__ == '__main__':
    co2Monitor = Co2Monitor()
    co2Monitor.start()
    try:
        app.run(debug=True, use_reloader=False, port=23423, host="0.0.0.0")
    except KeyboardInterrupt:
        co2Monitor.stop()
