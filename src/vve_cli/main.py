import argparse
import json
import pprint
import sys
import time
import traceback
import wave
from base64 import standard_b64encode
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import simpleaudio


class IntervalTimer:
    def __init__(self) -> None:
        self.__start = time.perf_counter()

    def elapsed(self) -> float:
        return round(time.perf_counter() - self.__start, 3)


from vve_cli.vve_service import VveClient, VveService


class IndexedDumper:
    def __init__(
        self,
        dump_dir: Path,
        prefix: str,
        postfix: str,
        extention: str,
    ) -> None:
        self.__dump_dir = dump_dir
        self.__dump_dir.mkdir(parents=True, exist_ok=True)
        self.__format = f"{prefix}_{{}}_{postfix}.{extention}"

    def remove_dumps(self):
        for dump_path in self.__dump_dir.glob(self.__format.format("*")):
            dump_path.unlink()

    def dump_text(self, index: int, content: str, encoding: str = "utf-8"):
        (self.__dump_dir / self.__format.format(f"{index:03d}")).write_text(
            content, encoding=encoding
        )

    def dump_bytes(self, index: int, content: bytes):
        (self.__dump_dir / self.__format.format(f"{index:03d}")).write_bytes(content)


def main(texts, text_src_name, speaker_id, is_batch=False):
    client = VveClient("localhost", 50021)

    service = VveService(client)
    pprint.pprint(service.speakers())

    dump_root_dir = Path("a")

    audio_query_dumper = IndexedDumper(
        dump_root_dir / "audio_query", text_src_name, f"s{speaker_id:02d}", "json"
    )
    audio_query_dumper.remove_dumps()

    if not is_batch:

        accent_phrases_dumper = IndexedDumper(
            dump_root_dir / "accent_phrases",
            text_src_name,
            f"s{speaker_id:02d}",
            "json",
        )
        accent_phrases_dumper.remove_dumps()

        synthesis_dumper = IndexedDumper(
            dump_root_dir / "synthesis", text_src_name, f"s{speaker_id:02d}", "wav"
        )
        synthesis_dumper.remove_dumps()

        play_obj = None

        t = IntervalTimer()

        autio_query_response = service.audio_query("", speaker_id)
        audio_query_dumper.dump_text(
            0, json.dumps(autio_query_response, ensure_ascii=False)
        )

        for i, text in enumerate(texts):
            accent_phrases_response = service.accent_phrases(text, speaker_id)
            accent_phrases_dumper.dump_text(
                i + 1, json.dumps(accent_phrases_response, ensure_ascii=False)
            )
            autio_query_response["accent_phrases"] = accent_phrases_response

            wave_response = service.synthesis(autio_query_response, speaker_id)
            synthesis_dumper.dump_bytes(i + 1, wave_response)

            if play_obj is not None:
                play_obj.wait_done()
            wave_obj = simpleaudio.WaveObject.from_wave_read(
                wave.open(BytesIO(wave_response), mode="rb")
            )
            play_obj = wave_obj.play()
        print("{:.3f} [sec]".format(t.elapsed()))

        play_obj.wait_done()

    else:

        multi_synthesis_dumper = IndexedDumper(
            dump_root_dir / "multi_synthesis",
            text_src_name,
            f"s{speaker_id:02d}",
            "zip",
        )
        multi_synthesis_dumper.remove_dumps()

        connect_waves_dumper = IndexedDumper(
            dump_root_dir / "connect_waves", text_src_name, f"s{speaker_id:02d}", "wav"
        )
        connect_waves_dumper.remove_dumps()

        t = IntervalTimer()

        audio_query_list = []
        for i, text in enumerate(texts):
            autio_query_response = service.audio_query(text, speaker_id)
            audio_query_dumper.dump_text(
                i + 1, json.dumps(autio_query_response, ensure_ascii=False)
            )
            audio_query_list.append(autio_query_response)

        zip_response = service.multi_synthesis(audio_query_list, speaker_id)
        multi_synthesis_dumper.dump_bytes(0, zip_response)

        wava_b64_list = []
        with ZipFile(BytesIO(zip_response)) as waves_zip:
            for wave_name in waves_zip.namelist():
                with waves_zip.open(wave_name) as wave_file:
                    wava_b64_list.append(
                        standard_b64encode(wave_file.read()).decode("utf-8")
                    )

        wave_response = service.connect_waves(wava_b64_list)
        connect_waves_dumper.dump_bytes(0, wave_response)

        print("{:.3f} [sec]".format(t.elapsed()))


def run():
    parser = argparse.ArgumentParser(prog="vve_cli")

    parser.add_argument(
        "speech_file", nargs="?", type=argparse.FileType(mode="rb"), default=sys.stdin
    )
    parser.add_argument("-s", "--speaker_id", type=int, default=0, metavar="ID")

    args = parser.parse_args()

    byte_strings = args.speech_file.readlines()
    if not byte_strings:
        print("[Error] No input.")
        exit(1)
    elif byte_strings[0] == "\ufeff":
        texts = [line.decode("utf-8-sig").strip() for line in byte_strings]
    elif type(byte_strings[0]) == str:
        try:
            texts = [
                line.encode("cp932", "surrogateescape").decode("utf-8").strip()
                for line in byte_strings
            ]
        except UnicodeDecodeError:
            texts = [line.strip() for line in byte_strings]
        except UnicodeEncodeError:
            if args.speech_file == sys.stdin:
                print("[Error] Unreadable string(s) came from stdin.")
            else:
                print("[Error] Unreadable string(s) appeared in file.")
            traceback.print_exc()
            exit(1)
    else:
        texts = [line.decode("utf-8").strip() for line in byte_strings]

    if args.speech_file == sys.stdin:
        text_src_name = "stdin"
    else:
        text_src_name = Path(args.speech_file.name).stem

    main(texts, text_src_name, args.speaker_id)
