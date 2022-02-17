from enum import Enum as _Enum

MAGIC_NUMBER = 0xC356
HEADER_SIZE = 12
VERSION = 1


class Command(_Enum):
    HELLO = 0
    DATA = 1
    ALIVE = 2
    GOODBYE = 3
