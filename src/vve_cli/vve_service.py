import sys
from abc import ABCMeta, abstractmethod
from json import JSONDecodeError
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from requests.models import Response
from vve_cli.dumper import TaggedDumper
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


class MetaEndPoint(metaclass=ABCMeta):
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


class EndPoint(MetaEndPoint):
    def __init__(self, api_name: str, dump_dir: Optional[Path] = None) -> None:
        self._api_name = api_name
        self._dump_dir = dump_dir
        self._dumper: Optional[TaggedDumper] = None

    def put_log(self, response_time: float, response: Response, **kwargs) -> None:
        print(
            f"{self._api_name:>18}: {response_time:7.3f} [sec]",
            file=sys.stderr,
        )


class InformationQueryAPI(EndPoint):
    def request(self, client, **kwargs) -> Response:
        return client.get(f"/{self._api_name}")

    def set_content(self, response: Response, **kwargs) -> Any:
        try:
            json_response = response.json()
        except JSONDecodeError:
            json_response = {}
        return json_response


class TextToAudioQueryAPI(EndPoint):
    def request(self, client, text, speaker_id, **kwargs) -> Response:
        return client.post(
            f"/{self._api_name}", params={"text": text, "speaker": speaker_id}
        )

    def put_log(self, response_time: float, response: Response, text, **kwargs) -> None:
        print(
            (
                f"{self._api_name:>18}: {response_time:7.3f} [sec]"
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


class SynthesisAPI(EndPoint):
    def request(
        self, client, audio_query: Dict[str, Any], speaker_id, **kwargs
    ) -> Response:
        return client.post(
            f"/{self._api_name}",
            json=audio_query,
            params={"speaker": speaker_id},
            headers={"Content-Type": "application/json"},
        )

    def put_log(
        self,
        response_time: float,
        response: Response,
        audio_query: Dict[str, Any],
        **kwargs,
    ) -> None:
        speech_text = "".join(
            [
                mora["text"]
                for accent_phrase in audio_query["accent_phrases"]
                for mora in (
                    accent_phrase["moras"] + [accent_phrase["pause_mora"]]
                    if accent_phrase["pause_mora"] is not None
                    else accent_phrase["moras"]
                )
            ]
        )
        print(
            (
                f"{self._api_name:>18}: {response_time:7.3f} [sec]"
                f" : {len(speech_text):3d} : {speech_text}"
            ),
            file=sys.stderr,
        )

    def set_content(self, response: Response, **kwargs) -> Any:
        return response.content


class TextToAccentPhrasesAPI(TextToAudioQueryAPI):
    def request(self, client, text, speaker_id, is_kana=False, **kwargs) -> Response:
        return client.post(
            f"/{self._api_name}",
            params={"text": text, "speaker": speaker_id, "is_kana": is_kana},
        )


class AccentPhraseEditAPI(InformationQueryAPI):
    def request(
        self, client, accent_phrases: List[Dict[str, Any]], speaker_id: int, **kwargs
    ) -> Response:
        return client.post(
            f"/{self._api_name}",
            json=accent_phrases,
            params={"speaker": speaker_id},
            headers={"Content-Type": "application/json"},
        )


class BatchSynthesisAPI(EndPoint):
    def request(
        self, client, audio_queries: List[Dict[str, Any]], speaker_id, **kwargs
    ) -> Response:
        return client.post(
            f"/{self._api_name}",
            json=audio_queries,
            params={"speaker": speaker_id},
            headers={"Content-Type": "application/json"},
        )

    def set_content(self, response: Response, **kwargs) -> Any:
        return response.content


class ConcatWavesAPI(EndPoint):
    def request(self, client, base64_waves: List[str], **kwargs) -> Response:
        return client.post(
            f"/{self._api_name}",
            json=base64_waves,
            headers={"Content-Type": "application/json"},
        )

    def set_content(self, response: Response, **kwargs) -> Any:
        return response.content


class VveService:
    def __init__(self, client: VveClient) -> None:
        self.__client = client

        self.__apis: Dict[str, EndPoint] = {}
        self.__apis["version"] = InformationQueryAPI("version")
        self.__apis["speakers"] = InformationQueryAPI("speakers")

        self.__apis["audio_query"] = TextToAudioQueryAPI("audio_query")
        self.__apis["synthesis"] = SynthesisAPI("synthesis")

        self.__apis["accent_phrases"] = TextToAccentPhrasesAPI("accent_phrases")
        self.__apis["mora_data"] = AccentPhraseEditAPI("mora_data")
        self.__apis["mora_length"] = AccentPhraseEditAPI("mora_length")
        self.__apis["mora_pitch"] = AccentPhraseEditAPI("mora_pitch")

        self.__apis["multi_synthesis"] = BatchSynthesisAPI("multi_synthesis")
        self.__apis["connect_waves"] = ConcatWavesAPI("connect_waves")

    def version(self) -> str:
        return self.__apis["version"].run(client=self.__client)

    def speakers(self) -> Dict[str, Any]:
        return self.__apis["speakers"].run(client=self.__client)

    def audio_query(self, text: str, speaker_id: int) -> Dict[str, Any]:
        return self.__apis["audio_query"].run(
            client=self.__client, text=text, speaker_id=speaker_id
        )

    def synthesis(self, audio_query: Dict[str, Any], speaker_id: int) -> bytes:
        return self.__apis["synthesis"].run(
            client=self.__client, audio_query=audio_query, speaker_id=speaker_id
        )

    def accent_phrases(
        self, text: str, speaker_id: int, is_kana: bool = False
    ) -> List[Dict[str, Any]]:
        return self.__apis["accent_phrases"].run(
            client=self.__client, text=text, speaker_id=speaker_id, is_kana=is_kana
        )

    def mora_data(
        self, accent_phrases: List[Dict[str, Any]], speaker_id: int
    ) -> List[Dict[str, Any]]:
        return self.__apis["mora_data"].run(
            client=self.__client, accent_phrases=accent_phrases, speaker_id=speaker_id
        )

    def mora_length(
        self, accent_phrases: List[Dict[str, Any]], speaker_id: int
    ) -> List[Dict[str, Any]]:
        return self.__apis["mora_length"].run(
            client=self.__client, accent_phrases=accent_phrases, speaker_id=speaker_id
        )

    def mora_pitch(
        self, accent_phrases: List[Dict[str, Any]], speaker_id: int
    ) -> List[Dict[str, Any]]:
        return self.__apis["mora_pitch"].run(
            client=self.__client, accent_phrases=accent_phrases, speaker_id=speaker_id
        )

    def multi_synthesis(
        self, audio_queries: List[Dict[str, Any]], speaker_id: int
    ) -> bytes:
        return self.__apis["multi_synthesis"].run(
            client=self.__client, audio_queries=audio_queries, speaker_id=speaker_id
        )

    def connect_waves(self, base64_waves: List[str]) -> bytes:
        return self.__apis["connect_waves"].run(
            client=self.__client, base64_waves=base64_waves
        )
