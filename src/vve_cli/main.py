import time

import requests


class IntervalTimer:
    def __init__(self) -> None:
        self.__start = time.perf_counter()

    def elapsed(self) -> float:
        return round(time.perf_counter() - self.__start, 3)


class VveClient:
    __urlorigin: str

    def __init__(self) -> None:
        self.__urlorigin = "http://localhost:50021"

    def get(self, url):
        return requests.get(self.__urlorigin + url)


def run():
    client = VveClient()

    t1 = IntervalTimer()
    response = client.get("/version")
    print(response.status_code)
    print(response.json().strip())
    print("{:.3f} [sec]".format(t1.elapsed()))

    t2 = IntervalTimer()
    response = client.get("/speakers")
    print(response.status_code)
    print(response.json())
    print("{:.3f} [sec]".format(t2.elapsed()))
