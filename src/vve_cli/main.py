import time
from argparse import ArgumentParser
from pathlib import Path


class IntervalTimer:
    def __init__(self) -> None:
        self.__start = time.perf_counter()

    def elapsed(self) -> float:
        return round(time.perf_counter() - self.__start, 3)


from vve_cli.text_to_speech import set_arguments as set_tts_arguments
from vve_cli.vve_wrapper import set_arguments as set_api_arguments


def run():
    main_parser = ArgumentParser(prog="vve_cli")
    subparsers = main_parser.add_subparsers()

    def set_common_arguments(parser: ArgumentParser):
        parser.add_argument("-s", "--speaker_id", type=int, metavar="ID")
        parser.add_argument("--host", type=str, default="localhost")
        parser.add_argument("--port", type=int, default=50021)
        parser.add_argument("--dump_dir", type=Path)

    tts_parser = subparsers.add_parser("tts", help="see `tts -h`")
    set_common_arguments(tts_parser)
    set_tts_arguments(tts_parser)

    api_parser = subparsers.add_parser("api", help="see `api -h`")
    set_common_arguments(api_parser)
    set_api_arguments(api_parser)

    args = main_parser.parse_args()

    if hasattr(args, "handler"):
        args.handler(args)
    else:
        main_parser.print_help()
