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

        response = self._request(client, **kwargs)

        response_time = t.elapsed()
        self._put_log(response_time, response, **kwargs)

        return self._set_content(response, **kwargs)

    @abstractmethod
    def _request(self, client, **kwargs) -> Response:
        pass

    @abstractmethod
    def _put_log(self, response_time: float, response: Response, **kwargs) -> None:
        pass

    @abstractmethod
    def _set_content(self, response: Response, **kwargs) -> Any:
        pass


class EndPoint(MetaEndPoint):
    def __init__(self, api_name: str, dump_dir: Optional[Path] = None) -> None:
        self._api_name = api_name
        self._dump_dir = dump_dir
        self._dumper: Optional[TaggedDumper] = None

    def _put_log(self, response_time: float, response: Response, **kwargs) -> None:
        print(
            f"{self._api_name:>18}: {response_time:7.3f} [sec]",
            file=sys.stderr,
        )


class InformationQueryAPI(EndPoint):
    def _request(self, client, **kwargs) -> Response:
        return client.get(f"/{self._api_name}")

    def _set_content(self, response: Response, **kwargs) -> Any:
        if self._dump_dir is not None:
            if self._dumper is None:
                self._dumper = TaggedDumper(self._dump_dir / self._api_name, "json")
            self._dumper.dump(response.text)

        try:
            json_response = response.json()
        except JSONDecodeError:
            json_response = {}
        return json_response


class TextToAudioQueryAPI(EndPoint):
    def _request(self, client, text: str, speaker_id: int, **kwargs) -> Response:
        return client.post(
            f"/{self._api_name}", params={"text": text, "speaker": speaker_id}
        )

    def _put_log(
        self, response_time: float, response: Response, text: str, **kwargs
    ) -> None:
        print(
            (
                f"{self._api_name:>18}: {response_time:7.3f} [sec]"
                f" : {len(text):3d} : {text}"
            ),
            file=sys.stderr,
        )

    def _set_content(
        self, response: Response, speaker_id: int, tag: str = "dump", **kwargs
    ) -> Any:
        if self._dump_dir is not None:
            if self._dumper is None:
                self._dumper = TaggedDumper(
                    self._dump_dir / self._api_name, "json", is_indexed=True
                )
            self._dumper.dump(response.text, tag + f"_s{speaker_id:02d}")

        try:
            json_response = response.json()
        except JSONDecodeError:
            json_response = {}
        return json_response


class SynthesisAPI(EndPoint):
    def _request(
        self, client, audio_query: Dict[str, Any], speaker_id: int, **kwargs
    ) -> Response:
        return client.post(
            f"/{self._api_name}",
            json=audio_query,
            params={"speaker": speaker_id},
            headers={"Content-Type": "application/json"},
        )

    def _put_log(
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
                for mora in accent_phrase["moras"]
                + (
                    [accent_phrase["pause_mora"]]
                    if "pause_mora" in accent_phrase
                    and accent_phrase["pause_mora"] is not None
                    else []
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

    def _set_content(
        self, response: Response, speaker_id: int, tag: str = "dump", **kwargs
    ) -> Any:
        if self._dump_dir is not None:
            if self._dumper is None:
                self._dumper = TaggedDumper(
                    self._dump_dir / self._api_name, "wav", is_indexed=True
                )
            self._dumper.dump(response.content, tag + f"_s{speaker_id:02d}")

        return response.content


class TextToAccentPhrasesAPI(TextToAudioQueryAPI):
    def _request(self, client, text, speaker_id, is_kana=False, **kwargs) -> Response:
        # OpenAPI boolean should be lowercase keyword
        flag_kana = "true" if is_kana else "false"

        return client.post(
            f"/{self._api_name}",
            params={"text": text, "speaker": speaker_id, "is_kana": flag_kana},
        )


class AccentPhraseEditAPI(EndPoint):
    def _request(
        self, client, accent_phrases: List[Dict[str, Any]], speaker_id: int, **kwargs
    ) -> Response:
        return client.post(
            f"/{self._api_name}",
            json=accent_phrases,
            params={"speaker": speaker_id},
            headers={"Content-Type": "application/json"},
        )

    def _set_content(
        self, response: Response, speaker_id: int, tag: str = "dump", **kwargs
    ) -> Any:
        if self._dump_dir is not None:
            if self._dumper is None:
                self._dumper = TaggedDumper(
                    self._dump_dir / self._api_name, "json", is_indexed=True
                )
            self._dumper.dump(response.text, tag + f"_s{speaker_id:02d}")

        try:
            json_response = response.json()
        except JSONDecodeError:
            json_response = {}
        return json_response


class BatchSynthesisAPI(EndPoint):
    def _request(
        self, client, audio_queries: List[Dict[str, Any]], speaker_id: int, **kwargs
    ) -> Response:
        return client.post(
            f"/{self._api_name}",
            json=audio_queries,
            params={"speaker": speaker_id},
            headers={"Content-Type": "application/json"},
        )

    def _set_content(
        self, response: Response, speaker_id: int, tag: str = "dump", **kwargs
    ) -> Any:
        if self._dump_dir is not None:
            if self._dumper is None:
                self._dumper = TaggedDumper(
                    self._dump_dir / self._api_name, "zip", is_indexed=True
                )
            self._dumper.dump(response.content, tag + f"_s{speaker_id:02d}")

        return response.content


class ConcatWavesAPI(EndPoint):
    def _request(self, client, base64_waves: List[str], **kwargs) -> Response:
        return client.post(
            f"/{self._api_name}",
            json=base64_waves,
            headers={"Content-Type": "application/json"},
        )

    def _set_content(self, response: Response, tag: str = "dump", **kwargs) -> Any:
        if self._dump_dir is not None:
            if self._dumper is None:
                self._dumper = TaggedDumper(
                    self._dump_dir / self._api_name, "wav", is_indexed=True
                )
            self._dumper.dump(response.content, tag)

        return response.content


class VveService:
    def __init__(self, client: VveClient, dump_root_dir: Optional[Path] = None) -> None:
        self.__client = client
        self.__dump_root_dir = dump_root_dir

        self.__apis: Dict[str, EndPoint] = {}

    def _get_api(self, endpoint_type, api_name):
        if not api_name in self.__apis:
            self.__apis[api_name] = endpoint_type(api_name, self.__dump_root_dir)
        return self.__apis[api_name]

    def version(self) -> str:
        api = self._get_api(InformationQueryAPI, "version")
        return api.run(self.__client)

    def speakers(self) -> Dict[str, Any]:
        api = self._get_api(InformationQueryAPI, "speakers")
        return api.run(self.__client)

    def audio_query(
        self, text: str, speaker_id: int, tag: str = "dump"
    ) -> Dict[str, Any]:
        api = self._get_api(TextToAudioQueryAPI, "audio_query")
        return api.run(self.__client, text=text, speaker_id=speaker_id, tag=tag)

    def synthesis(
        self, audio_query: Dict[str, Any], speaker_id: int, tag: str = "dump"
    ) -> bytes:
        api = self._get_api(SynthesisAPI, "synthesis")
        return api.run(
            self.__client, audio_query=audio_query, speaker_id=speaker_id, tag=tag
        )

    def accent_phrases(
        self, text: str, speaker_id: int, is_kana: bool = False, tag: str = "dump"
    ) -> List[Dict[str, Any]]:
        api = self._get_api(TextToAccentPhrasesAPI, "accent_phrases")
        return api.run(
            self.__client, text=text, speaker_id=speaker_id, is_kana=is_kana, tag=tag
        )

    def mora_data(
        self, accent_phrases: List[Dict[str, Any]], speaker_id: int, tag: str = "dump"
    ) -> List[Dict[str, Any]]:
        api = self._get_api(AccentPhraseEditAPI, "mora_data")
        return api.run(
            self.__client, accent_phrases=accent_phrases, speaker_id=speaker_id, tag=tag
        )

    def mora_length(
        self, accent_phrases: List[Dict[str, Any]], speaker_id: int, tag: str = "dump"
    ) -> List[Dict[str, Any]]:
        api = self._get_api(AccentPhraseEditAPI, "mora_length")
        return api.run(
            self.__client, accent_phrases=accent_phrases, speaker_id=speaker_id, tag=tag
        )

    def mora_pitch(
        self, accent_phrases: List[Dict[str, Any]], speaker_id: int, tag: str = "dump"
    ) -> List[Dict[str, Any]]:
        api = self._get_api(AccentPhraseEditAPI, "mora_pitch")
        return api.run(
            self.__client, accent_phrases=accent_phrases, speaker_id=speaker_id, tag=tag
        )

    def multi_synthesis(
        self, audio_queries: List[Dict[str, Any]], speaker_id: int, tag: str = "dump"
    ) -> bytes:
        api = self._get_api(BatchSynthesisAPI, "multi_synthesis")
        return api.run(
            self.__client, audio_queries=audio_queries, speaker_id=speaker_id, tag=tag
        )

    def connect_waves(self, base64_waves: List[str], tag: str = "dump") -> bytes:
        api = self._get_api(ConcatWavesAPI, "connect_waves")
        return api.run(self.__client, base64_waves=base64_waves, tag=tag)
