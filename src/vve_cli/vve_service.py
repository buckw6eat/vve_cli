import inspect
import sys
from abc import ABCMeta, abstractmethod
from json import JSONDecodeError
from typing import Any, Dict, List

import requests
from requests.models import Response
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


class EndPoint(metaclass=ABCMeta):
    def run(self, client, **kwargs) -> Any:
        t = IntervalTimer()

        response = self.request(client, **kwargs)

        response_time = t.elapsed()
        self.put_log(response_time, response, **kwargs)

        return self.set_content(response)

    @abstractmethod
    def request(self, client, **kwargs) -> Response:
        pass

    @abstractmethod
    def put_log(self, response_time: float, response: Response, **kwargs) -> None:
        pass

    @abstractmethod
    def set_content(self, response: Response, **kwargs) -> Any:
        pass


class InformationQueryAPI(EndPoint):
    def __init__(self, api_name: str) -> None:
        self.__api_name = api_name

    def request(self, client, **kwargs) -> Response:
        return client.get(f"/{self.__api_name}")

    def put_log(self, response_time: float, response: Response, **kwargs) -> None:
        print(
            f"{self.__api_name:>18}: {response_time:7.3f} [sec]",
            file=sys.stderr,
        )

    def set_content(self, response: Response, **kwargs) -> Any:
        try:
            json_response = response.json()
        except JSONDecodeError:
            json_response = {}
        return json_response


class TextToAudioQueryAPI(EndPoint):
    def __init__(self, api_name: str) -> None:
        self.__api_name = api_name

    def request(self, client, text, speaker_id, **kwargs) -> Response:
        return client.post(
            f"/{self.__api_name}", params={"text": text, "speaker": speaker_id}
        )

    def put_log(self, response_time: float, response: Response, text, **kwargs) -> None:
        print(
            (
                f"{self.__api_name:>18}: {response_time:7.3f} [sec]"
                f" : {len(text):3d} : {text}"
            ),
            file=sys.stderr,
        )

    def set_content(self, response: Response, **kwargs) -> Any:
        try:
            json_response = response.json()
        except JSONDecodeError:
            json_response = {}
        return json_response


class AccentPhraseEditAPI(InformationQueryAPI):
    def __init__(self, api_name: str) -> None:
        super().__init__(api_name)
        self.__api_name = api_name

    def request(
        self, client, accent_phrases: List[Dict[str, Any]], speaker_id: int, **kwargs
    ) -> Response:
        return client.post(
            f"/{self.__api_name}",
            json=accent_phrases,
            params={"speaker": speaker_id},
            headers={"Content-Type": "application/json"},
        )


class VveService:
    def __init__(self, client: VveClient) -> None:
        self.__client = client

        self.__apis: Dict[str, EndPoint] = {}
        self.__apis["version"] = InformationQueryAPI("version")
        self.__apis["speakers"] = InformationQueryAPI("speakers")

        self.__apis["audio_query"] = TextToAudioQueryAPI("audio_query")

        self.__apis["mora_data"] = AccentPhraseEditAPI("mora_data")
        self.__apis["mora_length"] = AccentPhraseEditAPI("mora_length")
        self.__apis["mora_pitch"] = AccentPhraseEditAPI("mora_pitch")

    def version(self) -> str:
        api_name = inspect.currentframe().f_code.co_name
        return self.__apis[api_name].run(client=self.__client)

    def speakers(self) -> Dict[str, Any]:
        api_name = inspect.currentframe().f_code.co_name
        return self.__apis[api_name].run(client=self.__client)

    def audio_query(self, text: str, speaker_id: int) -> Dict[str, Any]:
        api_name = inspect.currentframe().f_code.co_name
        return self.__apis[api_name].run(
            client=self.__client, text=text, speaker_id=speaker_id
        )

    def synthesis(self, aq_json, speaker_id):
        t = IntervalTimer()
        response = self.__client.post(
            "/synthesis",
            json=aq_json,
            params={"speaker": speaker_id},
            headers={"Content-Type": "application/json"},
        )
        response_time = t.elapsed()

        speech_text = "".join(
            [
                mora["text"]
                for accent_phrase in aq_json["accent_phrases"]
                for mora in (
                    accent_phrase["moras"] + [accent_phrase["pause_mora"]]
                    if accent_phrase["pause_mora"] is not None
                    else accent_phrase["moras"]
                )
            ]
        )
        print(
            "{:>18}: {:7.3f} [sec] : {:3d} : {}".format(
                inspect.currentframe().f_code.co_name,
                response_time,
                len(speech_text),
                speech_text,
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

    def mora_data(
        self, accent_phrases: List[Dict[str, Any]], speaker_id: int
    ) -> List[Dict[str, Any]]:
        api_name = inspect.currentframe().f_code.co_name
        return self.__apis[api_name].run(
            client=self.__client, accent_phrases=accent_phrases, speaker_id=speaker_id
        )

    def mora_length(
        self, accent_phrases: List[Dict[str, Any]], speaker_id: int
    ) -> List[Dict[str, Any]]:
        api_name = inspect.currentframe().f_code.co_name
        return self.__apis[api_name].run(
            client=self.__client, accent_phrases=accent_phrases, speaker_id=speaker_id
        )

    def mora_pitch(
        self, accent_phrases: List[Dict[str, Any]], speaker_id: int
    ) -> List[Dict[str, Any]]:
        api_name = inspect.currentframe().f_code.co_name
        return self.__apis[api_name].run(
            client=self.__client, accent_phrases=accent_phrases, speaker_id=speaker_id
        )

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
