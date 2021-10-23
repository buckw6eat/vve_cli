import pprint
import re
import sys
import traceback
import wave
from argparse import ArgumentParser, FileType, Namespace
from base64 import standard_b64encode
from io import BytesIO
from operator import itemgetter
from pathlib import Path
from zipfile import ZipFile

import simpleaudio

from vve_cli.main import IntervalTimer
from vve_cli.vve_service import VveClient, VveService


def set_arguments(parser: ArgumentParser):
    parser.add_argument(
        "speech_file", nargs="?", type=FileType(mode="rb"), default=sys.stdin
    )
    parser.add_argument("--batch", action="store_true")
    parser.add_argument(
        "-n",
        "--line_numbers",
        type=range_tuple,
        metavar="N",
        help=(
            "Specify line number of input texts."
            ' Range (from n to m means "n-m" or "n:m", both numbers are optional)'
            ' , multiple line numbers as comma-separated list ("n,m")'
            ' and mixture them are allowed. e.g. "n-m,i,j"'
        ),
    )
    parser.set_defaults(handler=main)


def range_tuple(arg: str):
    line_numbers = []

    for number in arg.split(","):
        pattern = r"(\d*)[-:](\d*)"
        result = re.match(pattern, number)
        if result:
            start = int(result.group(1)) - 1 if result.group(1) else None
            stop = int(result.group(2)) if result.group(2) else None

            if start and stop and not stop >= start:
                print("[Warn] start:stop form should be stop >= start, Ignored.")
            else:
                line_numbers.append(slice(start, stop))
        else:
            line_numbers.append(int(number) - 1)

    return tuple(line_numbers)


def main(args: Namespace):
    service = VveService(VveClient(args.host, args.port), args.dump_dir)

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

    if args.line_numbers:
        try:
            items = itemgetter(*args.line_numbers)(texts)
            if type(items) is tuple:
                texts = []
                for item in items:
                    if type(item) is list:
                        texts.extend(item)
                    else:
                        texts.append(item)
            elif type(items) is list:
                texts = items
            else:
                texts = [items]

        except IndexError:
            print("[Error] -n/--line_numbers has invalid index.")
            exit(1)

    if args.speech_file == sys.stdin:
        text_src_name = "stdin"
    else:
        text_src_name = Path(args.speech_file.name).stem

    if args.speaker_id:
        speaker_id = args.speaker_id if args.speaker_id > 0 else 0
    else:
        speaker_id = 0

    version = service.version()
    print("{:>18}:  {}".format("ENGINE version", version))
    pprint.pprint(service.speakers())

    if args.batch:
        tts_batch(service, texts, text_src_name, speaker_id)
    else:
        tts_stream(service, texts, text_src_name, speaker_id)


def tts_stream(service: VveService, texts, text_src_name, speaker_id) -> None:
    tag = text_src_name

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


def tts_batch(service: VveService, texts, text_src_name, speaker_id) -> None:
    tag = text_src_name

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

    simpleaudio.WaveObject.from_wave_read(
        wave.open(BytesIO(wave_response), mode="rb")
    ).play().wait_done()
