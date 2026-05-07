import threading
import itertools
import sys
import time
import click


class Spinner:
    def __init__(self, message: str):
        self._msg     = message
        self._stop    = threading.Event()
        self._thread  = threading.Thread(target=self._spin, daemon=True)
        self._frames  = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]

    def _spin(self):
        for frame in itertools.cycle(self._frames):
            if self._stop.is_set():
                break
            sys.stdout.write(f"\r  {click.style(frame, fg='cyan')}  {self._msg}   ")
            sys.stdout.flush()
            time.sleep(0.08)
        sys.stdout.write("\r" + " " * (len(self._msg) + 10) + "\r")
        sys.stdout.flush()

    def __enter__(self):
        self._thread.start()
        return self

    def __exit__(self, *_):
        self._stop.set()
        self._thread.join()