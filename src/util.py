import struct as _struct
from . import constants as _Constants


def pack(command: int, seq: int, session_id: int, data: str = None) -> bytes:
    header = _struct.pack("!HBBII", _Constants.MAGIC_NUMBER, _Constants.VERSION, command, seq, session_id)
    if data == None:
        return header
    return header + data.encode("utf-8", "replace")


def unpack(data: bytes) -> "tuple[int, int, int, int, int]":
    return _struct.unpack("!HBBII", data)