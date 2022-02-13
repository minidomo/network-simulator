import struct


def pack(command, seq, sessionID):
    return struct.pack('!HBBII', 0xC356, 1, command, seq, sessionID)


def unpack(data):
    return struct.unpack('!HBBII', data)


# todo
# data="abcdefg"
# header = pack(1, seq, sessionID)
# data_msg= header + data.encode('utf-8')
# socket.sendto(data_msg, server_addr)
