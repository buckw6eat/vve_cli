from pathlib import Path
from typing import Union


class TaggedDumper:
    def __init__(
        self, dump_dir: Path, extention: str, is_indexed: bool = False
    ) -> None:
        self.__dump_dir = dump_dir
        if is_indexed:
            self.__index = 1
        else:
            self.__index = 0
        self.__format = f"{{}}.{extention.strip()}"

    def dump(
        self, content: Union[str, bytes], tag: str = "dump", encoding: str = "utf-8"
    ):
        if not self.__dump_dir.exists():
            self.__dump_dir.mkdir(parents=True)

        if self.__index > 0:
            dump_name = self.__format.format(tag + f"_{self.__index:03d}")
            self.__index += 1
        else:
            dump_name = self.__format.format(tag)
        dump_path = self.__dump_dir / dump_name

        if type(content) is str:
            dump_path.write_text(content, encoding=encoding)
        else:
            dump_path.write_bytes(content)
