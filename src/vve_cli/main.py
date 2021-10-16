import argparse
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


def main(texts, text_src_name, speaker_id, is_batch=False):
    client = VveClient("localhost", 50021)

    dump_root_dir = Path("a")
    service = VveService(client, dump_root_dir)
    version = service.version()
    print("{:>18}:  {}".format("ENGINE version", version))
    pprint.pprint(service.speakers())

    tag = text_src_name

    if not is_batch:

        play_obj = None

        t = IntervalTimer()

        autio_query_response = service.audio_query("", speaker_id)

        for text in texts:
            accent_phrases_response = service.accent_phrases(text, speaker_id, tag=tag)
            autio_query_response["accent_phrases"] = accent_phrases_response

            wave_response = service.synthesis(autio_query_response, speaker_id, tag=tag)

            if play_obj is not None:
                play_obj.wait_done()
            wave_obj = simpleaudio.WaveObject.from_wave_read(
                wave.open(BytesIO(wave_response), mode="rb")
            )
            play_obj = wave_obj.play()
        print("{:.3f} [sec]".format(t.elapsed()))

        play_obj.wait_done()

    else:

        t = IntervalTimer()

        audio_query_list = []
        for text in texts:
            autio_query_response = service.audio_query(text, speaker_id, tag=tag)
            audio_query_list.append(autio_query_response)

        zip_response = service.multi_synthesis(audio_query_list, speaker_id, tag=tag)

        wava_b64_list = []
        with ZipFile(BytesIO(zip_response)) as waves_zip:
            for wave_name in waves_zip.namelist():
                with waves_zip.open(wave_name) as wave_file:
                    wava_b64_list.append(
                        standard_b64encode(wave_file.read()).decode("utf-8")
                    )

        wave_response = service.connect_waves(wava_b64_list, tag=tag)

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
