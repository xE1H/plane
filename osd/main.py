import json
import random

import flask

from telemeter import MavlinkTelemeter
from rssiclient import RssiFetcher

app = flask.Flask(__name__)
app.config['SECRET_KEY'] = str(random.random())

mavlink = MavlinkTelemeter("udpin:0.0.0.0:14555")
rssi = RssiFetcher()


@app.route('/osd')
def index():
    return flask.render_template('osd.html')


@app.route('/stream')
def stream():
    def generate():
        while True:
            mavlink.telemetry_changed.wait()
            yield f"data: {json.dumps(mavlink.telemetry + {'signal': rssi})}\n\n"
            mavlink.telemetry_changed.clear()

    return flask.Response(generate(), mimetype='text/event-stream')


if __name__ == '__main__':
    app.run()
