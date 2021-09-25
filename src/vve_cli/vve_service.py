import inspect
import sys

import requests

from vve_cli.main import IntervalTimer


class VveClient:
    __urlorigin: str

    def __init__(self) -> None:
        self.__urlorigin = "http://localhost:50021"

    def get(self, url):
        return requests.get(self.__urlorigin + url)

    def post(self, url, json=None, params=None, headers=None):
        return requests.post(
            self.__urlorigin + url, json=json, params=params, headers=headers
        )


class VveService:
    def __init__(self, client: VveClient) -> None:
        self.__client = client
        version = self.version()
        print("{:>18}:  {}".format("ENGINE version", version))

    def version(self):
        t = IntervalTimer()
        response = self.__client.get("/version")
        response_time = t.elapsed()
        print(
            "{:>18}: {:7.3f} [sec]".format(
                inspect.currentframe().f_code.co_name, response_time
            ),
            file=sys.stderr,
        )
        return response.json().strip()

    def speakers(self):
        t = IntervalTimer()
        response = self.__client.get("/speakers")
        response_time = t.elapsed()
        print(
            "{:>18}: {:7.3f} [sec]".format(
                inspect.currentframe().f_code.co_name, response_time
            ),
            file=sys.stderr,
        )
        return response.json()

    def audio_query(self, text, speaker_id):
        t = IntervalTimer()
        response = self.__client.post(
            "/audio_query", params={"text": text, "speaker": speaker_id}
        )
        response_time = t.elapsed()
        print(
            "{:>18}: {:7.3f} [sec] : {:3d} : {}".format(
                inspect.currentframe().f_code.co_name, response_time, len(text), text
            ),
            file=sys.stderr,
        )
        return response.json()

    def synthesis(self, aq_json, speaker_id):
        t = IntervalTimer()
        response = self.__client.post(
            "/synthesis",
            json=aq_json,
            params={"speaker": speaker_id},
            headers={"Content-Type": "application/json"},
        )
        response_time = t.elapsed()
        print(
            "{:>18}: {:7.3f} [sec] : {}".format(
                inspect.currentframe().f_code.co_name, response_time, aq_json["kana"]
            ),
            file=sys.stderr,
        )
        return response.content
