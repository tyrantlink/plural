TOKEN_EPOCH = 1727988244890
BASE66CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789=-_~'


def encode_b66(b10: int) -> str:
    b66 = ''
    while b10:
        b66 = BASE66CHARS[b10 % 66]+b66
        b10 //= 66
    return b66


def decode_b66(b66: str) -> int:
    b10 = 0
    for i in range(len(b66)):
        b10 += BASE66CHARS.index(b66[i])*(66**(len(b66)-i-1))
    return b10
