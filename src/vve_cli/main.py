import requests


class VveClient:
    __urlorigin: str

    def __init__(self) -> None:
        self.__urlorigin = "http://localhost:50021"

    def get(self, url):
        return requests.get(self.__urlorigin + url)


def run():
    client = VveClient()

    response = client.get("/version")
    print(response.status_code)
    print(response.json().strip())

    response = client.get("/speakers")
    print(response.status_code)
    print(response.json())
