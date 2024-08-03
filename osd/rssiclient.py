import threading
import requests
import time


class RssiFetcher:
    def __init__(self):
        self.signal = 0
        thread = threading.Thread(target=self.loop, daemon=True)
        thread.start()

    def loop(self):
        while True:
            response = requests.get('http://plane:8133/signal_quality')
            self.signal = float(response.text)
            time.sleep(10)
