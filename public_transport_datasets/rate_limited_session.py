import requests
import time
import threading


class RateLimitedSession(requests.Session):
    def __init__(self, max_requests_per_minute):
        super().__init__()
        self.max_requests_per_minute = max_requests_per_minute
        self.lock = threading.Lock()
        self.requests_made = []

    def request(self, method, url, *args, **kwargs):
        with self.lock:
            current_time = time.time()
            self.requests_made = [
                t for t in self.requests_made if current_time - t < 60
            ]
            if len(self.requests_made) >= self.max_requests_per_minute:
                sleep_time = 60 - (current_time - self.requests_made[0])
                time.sleep(sleep_time)
            self.requests_made.append(time.time())
        return super().request(method, url, *args, **kwargs)

    def dump(self):
        print(self.requests_made)
