import time
from datetime import datetime, timezone
import logging

import paho.mqtt.client as mqtt

from co2watcher import Co2Monitor


class Co2MonitorMqtt:
    ERROR_WAIT_TIME = 5.0

    def __init__(
        self,
        name='co2monitor',
        mqtt_host='localhost',
        mqtt_port=1883,
        mqtt_username=None,
        mqtt_pw=None,
        mqtt_keepalive=60,
    ):
        self._logger = logging.getLogger(Co2MonitorMqtt.__name__)
        self.name = name
        self._monitor = Co2Monitor()
        self._mqtt_host = mqtt_host
        self._mqtt_port = mqtt_port
        self._mqtt_keepalive = mqtt_keepalive
        self._mqtt_client = mqtt.Client(name)
        if mqtt_pw and mqtt_username:
            self._mqtt_client.username_pw_set(username=mqtt_username, password=mqtt_pw)
        self._mqtt_client.will_set("{}/online".format(name), 'false', retain=True)
        self._connected = False

    def _connect(self):
        try:
            self._mqtt_client.connect(host=self._mqtt_host, port=self._mqtt_port, keepalive=self._mqtt_keepalive)
            self._mqtt_client.publish("{}/online".format(self.name), 'true', retain=True)
            return True
        except OSError as e:
            self._show_connection_error(e)
            return False

    def _show_connection_error(self, e):
        if e.errno == 101:
            self._logger.error("Could not connect to MQTT server, retrying...")
        else:
            self._logger.error("Could not publish to MQTT server: {}".format(str(e)))

    def start(self):
        self._monitor.start()
        while not self._connected:
            self._connected = self._connect()
            if not self._connected:
                time.sleep(self.ERROR_WAIT_TIME)
                continue
            else:
                self._logger.info("Connected to MQTT server")
                break

    def loop(self):
        while True:
            self._monitor.new_data_event.wait()
            timestamp, co2, temperature = self._monitor.get_data()
            isotime = datetime.fromtimestamp(int(timestamp), tz=timezone.utc).isoformat().replace("+00:00", "Z")
            try:
                self._mqtt_client.publish('{}/co2'.format(self.name), co2, retain=True)
                self._mqtt_client.publish(
                    '{}/temperature'.format(self.name), round(temperature, ndigits=2), retain=True
                )
                self._mqtt_client.publish('{}/timestamp'.format(self.name), isotime, retain=True)
            except OSError as e:
                self._show_connection_error(e)
                time.sleep(self.ERROR_WAIT_TIME)
            self._monitor.new_data_event.clear()

    def stop(self):
        self._monitor.stop()
        self._mqtt_client.publish("{}/online".format(self.name), 'false', retain=True)
        self._mqtt_client.disconnect()


if __name__ == '__main__':
    from config import config

    logging.basicConfig(level=logging.INFO)
    monitor = Co2MonitorMqtt(**config)
    try:
        monitor.start()
        monitor.loop()
    except KeyboardInterrupt:
        monitor.stop()
