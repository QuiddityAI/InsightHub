import time


class Timings(object):

    def __init__(self) -> None:
        self.timings = []
        self.last_timestamp = time.time()

    def log(self, description):
        now = time.time()
        duration = now - self.last_timestamp
        self.timings.append({"part": description, "duration": duration})
        self.last_timestamp = now

    def get_timestamps(self):
        return self.timings
