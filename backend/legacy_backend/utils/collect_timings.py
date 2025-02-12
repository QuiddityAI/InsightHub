import logging
import time


class Timings(object):
    def __init__(self) -> None:
        self.timings = []
        self.start = time.time()
        self.last_timestamp = self.start

    def log(self, description):
        now = time.time()
        duration = now - self.last_timestamp
        self.timings.append({"part": description, "duration": duration})
        self.last_timestamp = now

    def get_timestamps(self):
        return self.timings

    def print_to_logger(self):
        for timing in self.timings:
            logging.warning(f"{timing['part']}: {timing['duration'] * 1000:.2f}ms")
        logging.warning(f"Total time: {(self.last_timestamp - self.start):.3f}s")
