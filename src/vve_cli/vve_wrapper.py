import json
import re
import sys
from argparse import ArgumentParser, Namespace
from base64 import standard_b64encode
from inspect import getmembers, isfunction
from pathlib import Path
from typing import Any, Dict, List

from vve_cli.vve_service import VveClient, VveService


def set_arguments(parser: ArgumentParser):
    parser.add_argument("api_name", nargs="?")
    parser.add_argument("-f", "--file_path", type=Path)
    parser.add_argument("--text", type=str)
    parser.add_argument("--kana", action="store_true")
    parser.add_argument("-l", "--line_number", type=int)
    parser.add_argument("-p", "--preset_id", type=int)
    parser.set_defaults(handler=main)


def main(args: Namespace) -> None:
    dump_dir = args.dump_dir or Path("dump")
    service = VveService(VveClient(args.host, args.port), dump_dir)

    kwargs = {
        "file_path": args.file_path,
        "speaker_id": args.speaker_id,
        "text": args.text,
        "is_kana": args.kana or None,
        "line_number": args.line_number,
        "preset_id": args.preset_id,
    }
    kwargs = {k: v for k, v in kwargs.items() if v is not None}

    try:
        for name, target_api in getmembers(sys.modules[__name__], isfunction):
            if name == "call_" + args.api_name:
                target_api(service, **kwargs)
                break
        else:
            raise ValueError("[Error] Invalied api name or not implemented")
    except (TypeError, ValueError) as e:
        print(type(e), e, file=sys.stderr)


def call_version(service: VveService) -> None:
    _ = service.version()


def call_speakers(service: VveService) -> None:
    _ = service.speakers()


def call_audio_query(
    service: VveService,
    speaker_id: int,
    text: str = "",
    file_path: Path = None,
    line_number: int = 0,
) -> None:
    if text:
        _ = service.audio_query(text, speaker_id)
    elif file_path and file_path.exists() and file_path.is_file():
        texts = file_path.read_text(encoding="utf-8").splitlines()
        text = texts[line_number if len(texts) > line_number else 0]
        _ = service.audio_query(text, speaker_id)
    else:
        raise ValueError("[Error] Less or Invalied argument(s)")


def call_synthesis(service: VveService, file_path: Path, speaker_id: int) -> None:
    if file_path.exists() and file_path.is_file():
        audio_query = json.loads(file_path.read_text(encoding="utf-8"))
        _ = service.synthesis(audio_query, speaker_id)
    else:
        raise ValueError("[Error] Invalied Path: File not found")


def call_accent_phrases(
    service: VveService,
    file_path: Path,
    speaker_id: int,
    is_kana: bool = False,
    text: str = "",
    line_number: int = 0,
) -> None:
    if text:
        _ = service.accent_phrases(text, speaker_id, is_kana)
    elif file_path.exists() and file_path.is_file():
        texts = file_path.read_text(encoding="utf-8").splitlines()
        text = texts[line_number if len(texts) > line_number else 0]
        _ = service.accent_phrases(text, speaker_id, is_kana)
    else:
        raise ValueError("[Error] Less or Invalied argument(s)")


def load_accent_phrases(file_path: Path) -> List[Dict[str, Any]]:
    loaded_json = json.loads(file_path.read_text(encoding="utf-8"))
    if type(loaded_json) is dict:
        if "accent_phrases" in loaded_json:
            return loaded_json["accent_phrases"]
        else:
            return [loaded_json]
    elif type(loaded_json) is list:
        return loaded_json
    else:
        return []


def call_mora_data(service: VveService, file_path: Path, speaker_id: int) -> None:
    if file_path.exists() and file_path.is_file():
        accent_phrases = load_accent_phrases(file_path)
        _ = service.mora_data(accent_phrases, speaker_id)
    else:
        raise ValueError("[Error] Invalied Path: File not found")


def call_mora_length(service: VveService, file_path: Path, speaker_id: int) -> None:
    if file_path.exists() and file_path.is_file():
        accent_phrases = load_accent_phrases(file_path)
        _ = service.mora_length(accent_phrases, speaker_id)
    else:
        raise ValueError("[Error] Invalied Path: File not found")


def call_mora_pitch(service: VveService, file_path: Path, speaker_id: int) -> None:
    if file_path.exists() and file_path.is_file():
        accent_phrases = load_accent_phrases(file_path)
        _ = service.mora_pitch(accent_phrases, speaker_id)
    else:
        raise ValueError("[Error] Invalied Path: File not found")


def call_multi_synthesis(service: VveService, file_path: Path, speaker_id: int) -> None:
    if file_path.exists() and file_path.is_file():
        audio_queries = json.loads(file_path.read_text(encoding="utf-8"))
        if type(audio_queries) is dict:
            audio_queries = [audio_queries]
        _ = service.multi_synthesis(audio_queries, speaker_id)
    else:
        raise ValueError("[Error] Invalied Path: File not found")


def call_connect_waves(service: VveService, file_path: Path) -> None:
    def naturalize(key: Path):
        return [
            int(text) if text.isdisit() else text
            for text in re.split(r"(\d+)", key.name)
        ]

    if file_path.exists() and file_path.is_dir():
        wava_b64_list = []
        wave_pathes = sorted(file_path.glob("*.wav"), key=naturalize)

        if wave_pathes:
            for wave_path in wave_pathes:
                wava_b64_list.append(
                    standard_b64encode(wave_path.read_bytes()).decode("utf-8")
                )
            _ = service.connect_waves(wava_b64_list)
        else:
            raise ValueError("[Error] Wave file not found in specified directory")
    else:
        raise ValueError("[Error] Invalied Path: Directory required")


def call_audio_query_from_preset(
    service: VveService,
    preset_id: int,
    text: str = "",
    file_path: Path = None,
    line_number: int = 0,
) -> None:
    if text:
        _ = service.audio_query_from_preset(text, preset_id)
    elif file_path and file_path.exists() and file_path.is_file():
        texts = file_path.read_text(encoding="utf-8").splitlines()
        text = texts[line_number if len(texts) > line_number else 0]
        _ = service.audio_query_from_preset(text, preset_id)
    else:
        raise ValueError("[Error] Less or Invalied argument(s)")


def call_presets(service: VveService) -> None:
    _ = service.presets()
