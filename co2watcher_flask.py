import json
from flask import Flask

from co2watcher import Co2Monitor

app = Flask(__name__)
co2Monitor = None


@app.route('/')
def entry_point():
    timestamp, co2, temperature = co2Monitor.get_data()
    return json.dumps(
        {
            'timestamp': int(timestamp),
            'co2': co2,
            'temperature': round(temperature, ndigits=1),
        }
    )


if __name__ == '__main__':
    co2Monitor = Co2Monitor()
    co2Monitor.start()
    try:
        app.run(debug=True, use_reloader=False, port=23423, host="0.0.0.0")
    except KeyboardInterrupt:
        co2Monitor.stop()
