import argparse
import json
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


def main(speaker_id):
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

    with open("q/speech.txt", encoding="utf-8") as f:
        texts = [line.strip() for line in f.readlines()]

    output_dir = Path("a/audio_query")
    output_dir.mkdir(parents=True, exist_ok=True)

    t3 = IntervalTimer()
    for i, text in enumerate(texts):
        response = client.post(
            "/audio_query", params={"text": text, "speaker": speaker_id}
        )
        (output_dir / "text-{:03d}_s{:02d}.json".format(i + 1, speaker_id)).write_text(
            json.dumps(response.json(), ensure_ascii=False), encoding="utf-8"
        )
    print("{:.3f} [sec]".format(t3.elapsed()))

    input_dir = Path("a/audio_query")

    output_dir = Path("a/synthesis")
    output_dir.mkdir(parents=True, exist_ok=True)

    t4 = IntervalTimer()
    for aq_path in input_dir.glob("*_s{:02d}.json".format(speaker_id)):
        response = client.post(
            "/synthesis",
            json=json.loads(aq_path.read_text(encoding="utf-8")),
            params={"speaker": speaker_id},
            headers={"Content-Type": "application/json"},
        )
        (output_dir / (aq_path.stem + ".wav")).write_bytes(response.content)
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
