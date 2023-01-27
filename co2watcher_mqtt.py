from datetime import datetime, timezone

import paho.mqtt.client as mqtt

from co2watcher import Co2Monitor


class Co2MonitorMqtt:
    def __init__(
        self,
        name='co2monitor',
        mqtt_host='localhost',
        mqtt_port=1883,
        mqtt_username=None,
        mqtt_pw=None,
        mqtt_keepalive=60,
    ):
        self.name = name
        self._monitor = Co2Monitor()
        self._mqtt_client = mqtt.Client(name)
        if mqtt_pw and mqtt_username:
            self._mqtt_client.username_pw_set(username=mqtt_username, password=mqtt_pw)
        self._mqtt_client.will_set(f"{name}/online", 'false', retain=True)
        self._mqtt_client.connect(
            host=mqtt_host, port=mqtt_port, keepalive=mqtt_keepalive
        )
        self._mqtt_client.publish(f"{name}/online", 'true', retain=True)

    def loop(self):
        self._monitor.start()
        while True:
            self._monitor.new_data_event.wait()
            timestamp, co2, temperature = self._monitor.get_data()
            isotime = datetime.fromtimestamp(int(timestamp), tz=timezone.utc).isoformat().replace("+00:00", "Z")
            self._mqtt_client.publish(f'{self.name}/co2', co2, retain=True)
            self._mqtt_client.publish(
                f'{self.name}/temperature', round(temperature, ndigits=2), retain=True
            )
            self._mqtt_client.publish(f'{self.name}/timestamp', isotime, retain=True)
            self._monitor.new_data_event.clear()

    def stop(self):
        self._monitor.stop()
        self._mqtt_client.publish(f"{self.name}/online", 'false', retain=True)
        self._mqtt_client.disconnect()


if __name__ == '__main__':
    from config import config

    monitor = Co2MonitorMqtt(**config)
    try:
        monitor.loop()
    except KeyboardInterrupt:
        monitor.stop()
