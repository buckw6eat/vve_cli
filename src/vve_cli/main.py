import argparse
import inspect
import json
import pprint
import time
from pathlib import Path

import requests
import simpleaudio


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

    def post(self, url, json=None, params=None, headers=None):
        return requests.post(
            self.__urlorigin + url, json=json, params=params, headers=headers
        )


class VveServer:
    def __init__(self, client: VveClient) -> None:
        self.__client = client
        version = self.version()
        print("{:>18}:  {}".format("ENGINE version", version))

    def version(self):
        t = IntervalTimer()
        response = self.__client.get("/version")
        response_time = t.elapsed()
        print(
            "{:>18}:  {:.3f} [sec]".format(
                inspect.currentframe().f_code.co_name, response_time
            )
        )
        return response.json().strip()

    def speakers(self):
        t = IntervalTimer()
        response = self.__client.get("/speakers")
        response_time = t.elapsed()
        print(
            "{:>18}:  {:.3f} [sec]".format(
                inspect.currentframe().f_code.co_name, response_time
            )
        )
        return response.json()

    def audio_query(self, text, speaker_id):
        t = IntervalTimer()
        response = self.__client.post(
            "/audio_query", params={"text": text, "speaker": speaker_id}
        )
        response_time = t.elapsed()
        print(
            "{:>18}:  {:.3f} [sec]  :  {:3d} : {}".format(
                inspect.currentframe().f_code.co_name, response_time, len(text), text
            )
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
            "{:>18}:  {:.3f} [sec]  : {}".format(
                inspect.currentframe().f_code.co_name, response_time, aq_json["kana"]
            )
        )
        return response.content


def main(speaker_id):
    client = VveClient()

    server = VveServer(client)
    pprint.pprint(server.speakers())

    with open("q/speech.txt", encoding="utf-8") as f:
        texts = [line.strip() for line in f.readlines()]

    output_dir = Path("a/audio_query")
    output_dir.mkdir(parents=True, exist_ok=True)

    t3 = IntervalTimer()
    for i, text in enumerate(texts):
        aq = server.audio_query(text, speaker_id)
        (output_dir / "text-{:03d}_s{:02d}.json".format(i + 1, speaker_id)).write_text(
            json.dumps(aq, ensure_ascii=False), encoding="utf-8"
        )
    print("{:.3f} [sec]".format(t3.elapsed()))

    input_dir = Path("a/audio_query")

    output_dir = Path("a/synthesis")
    output_dir.mkdir(parents=True, exist_ok=True)

    t4 = IntervalTimer()
    for aq_path in input_dir.glob("*_s{:02d}.json".format(speaker_id)):
        wave = server.synthesis(
            json.loads(aq_path.read_text(encoding="utf-8")), speaker_id
        )
        (output_dir / (aq_path.stem + ".wav")).write_bytes(wave)
    print("{:.3f} [sec]".format(t4.elapsed()))

    input_dir = Path("a/synthesis")
    for wave_path in input_dir.glob("*_s{:02d}.wav".format(speaker_id)):
        wave_obj = simpleaudio.WaveObject.from_wave_file(wave_path.as_posix())
        play_obj = wave_obj.play()
        play_obj.wait_done()


def run():
    parser = argparse.ArgumentParser()

    parser.add_argument("--speaker_id", type=int, default=0)

    args = parser.parse_args()

    main(args.speaker_id)
