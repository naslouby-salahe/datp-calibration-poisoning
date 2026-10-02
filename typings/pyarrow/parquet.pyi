from pathlib import Path

from pyarrow import Schema

class FileMetaData:
    num_rows: int

def read_schema(where: str | Path) -> Schema: ...
def read_metadata(where: str | Path) -> FileMetaData: ...
