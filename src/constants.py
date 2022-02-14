from enum import Enum as _Enum

MAGIC_NUMBER = 0xC356
MAGIC_CHARACTER = "|"


class Command(_Enum):
    HELLO = 0
    DATA = 1
    ALIVE = 2
    GOODBYE = 3
