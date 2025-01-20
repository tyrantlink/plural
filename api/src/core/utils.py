

from bson import ObjectId
B36CHARS = '0123456789abcdefghijklmnopqrstuvwxyz'


def b36encode(value: int | bytes) -> str:
    if isinstance(value, bytes):
        value = int.from_bytes(value)

    result = ''
    while value:
        value, i = divmod(value, 36)
        result = B36CHARS[i] + result

    return result


def b36decode(value: str) -> int:
    return int(value, 36)


ObjectId().binary
