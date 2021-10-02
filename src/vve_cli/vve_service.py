import inspect
import sys
from json import JSONDecodeError

import requests
from vve_cli.main import IntervalTimer


class VveClient:
    __urlorigin: str

    def __init__(self, host: str, port: int) -> None:
        self.__urlorigin = "http://{}:{:d}".format(host, port)

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
        try:
            json_response = response.json()
        except JSONDecodeError:
            json_response = {}
        return json_response

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
        try:
            json_response = response.json()
        except JSONDecodeError:
            json_response = {}
        return json_response

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
        try:
            json_response = response.json()
        except JSONDecodeError:
            json_response = {}
        return json_response

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

    def accent_phrases(self, text, speaker_id, is_kana=False):
        t = IntervalTimer()
        response = self.__client.post(
            "/accent_phrases",
            params={"text": text, "speaker": speaker_id, "is_kana": is_kana},
        )
        response_time = t.elapsed()
        print(
            "{:>18}: {:7.3f} [sec] : {:3d} : {}".format(
                inspect.currentframe().f_code.co_name, response_time, len(text), text
            ),
            file=sys.stderr,
        )
        try:
            json_response = response.json()
        except JSONDecodeError:
            json_response = {}
        return json_response

    def mora_data(self, accent_phrase_json, speaker_id):
        t = IntervalTimer()
        response = self.__client.post(
            "/mora_data",
            json=accent_phrase_json,
            params={"speaker": speaker_id},
            headers={"Content-Type": "application/json"},
        )
        response_time = t.elapsed()
        print(
            "{:>18}: {:7.3f} [sec]".format(
                inspect.currentframe().f_code.co_name, response_time
            ),
            file=sys.stderr,
        )
        try:
            json_response = response.json()
        except JSONDecodeError:
            json_response = {}
        return json_response

    def mora_length(self, accent_phrase_json, speaker_id):
        t = IntervalTimer()
        response = self.__client.post(
            "/mora_length",
            json=accent_phrase_json,
            params={"speaker": speaker_id},
            headers={"Content-Type": "application/json"},
        )
        response_time = t.elapsed()
        print(
            "{:>18}: {:7.3f} [sec]".format(
                inspect.currentframe().f_code.co_name, response_time
            ),
            file=sys.stderr,
        )
        try:
            json_response = response.json()
        except JSONDecodeError:
            json_response = {}
        return json_response

    def mora_pitch(self, accent_phrase_json, speaker_id):
        t = IntervalTimer()
        response = self.__client.post(
            "/mora_pitch",
            json=accent_phrase_json,
            params={"speaker": speaker_id},
            headers={"Content-Type": "application/json"},
        )
        response_time = t.elapsed()
        print(
            "{:>18}: {:7.3f} [sec]".format(
                inspect.currentframe().f_code.co_name, response_time
            ),
            file=sys.stderr,
        )
        try:
            json_response = response.json()
        except JSONDecodeError:
            json_response = {}
        return json_response

    def multi_synthesis(self, aq_jsons, speaker_id):
        t = IntervalTimer()
        response = self.__client.post(
            "/multi_synthesis",
            json=aq_jsons,
            params={"speaker": speaker_id},
            headers={"Content-Type": "application/json"},
        )
        response_time = t.elapsed()
        print(
            "{:>18}: {:7.3f} [sec]".format(
                inspect.currentframe().f_code.co_name, response_time
            ),
            file=sys.stderr,
        )
        return response.content

    def connect_waves(self, base64_waves):
        t = IntervalTimer()
        response = self.__client.post(
            "/connect_waves",
            json=base64_waves,
            headers={"Content-Type": "application/json"},
        )
        response_time = t.elapsed()
        print(
            "{:>18}: {:7.3f} [sec]".format(
                inspect.currentframe().f_code.co_name, response_time
            ),
            file=sys.stderr,
        )
        return response.content
