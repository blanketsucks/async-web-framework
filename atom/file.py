from typing import Union
import pathlib
import io

class File:
    def __init__(self, fp: Union[str, pathlib.Path, io.BytesIO], *, filename: str=None) -> None:
        if isinstance(fp, io.BytesIO):
            self.fp = fp

        if isinstance(fp, pathlib.Path):
            if not filename:
                filename = fp.name

            self.fp = fp.open('r')

        if isinstance(fp, str):
            if not filename:
                filename = fp

            self.fp = open(fp, 'r')

        self.filename = filename

    def read(self):
        return self.fp.read()

    def close(self):
        self.fp.close()