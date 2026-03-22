import threading
import time


class TimerEngine:
    def __init__(self, callback, interval=0.25):
        self.callback = callback
        self.interval = interval
        self._running = False
        self._thread = None

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def _run(self):
        while self._running:
            try:
                self.callback()
            except Exception as e:
                print(f"[TimerEngine] Erreur: {e}")
            time.sleep(self.interval)