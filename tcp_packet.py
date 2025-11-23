import struct


class TCPPacket:
    def __init__(self, seq=0, ack=0, flags=0, data=b""):
        self.seq = seq
        self.ack = ack
        self.flags = flags
        self.data = data

    def pack(self):
        # header is 16 bytes: seq(4), ack(4), flags(2), win(2), check(2), urg(2)
        # flags field also includes the data offset (4 words = 16 bytes)
        # offset 4 shifted left by 12 bits
        offset_flags = (4 << 12) | self.flags

        header = struct.pack(
            "!IIHHHH",
            self.seq,
            self.ack,
            offset_flags,
            4096,  # window
            0,  # checksum
            0,
        )  # urgent pointer
        return header + self.data

    @staticmethod
    def unpack(data):
        if len(data) < 16:
            return None

        header = data[:16]
        payload = data[16:]

        # ignore the last 3 values (window, check, urg)
        seq, ack, flags_raw, _, _, _ = struct.unpack("!IIHHHH", header)

        # mask out the offset to get just the flags
        flags = flags_raw & 0x3F

        return TCPPacket(seq, ack, flags, payload)

    # Helper checks
    @property
    def is_syn(self):
        return (self.flags & 0x02) != 0

    @property
    def is_ack(self):
        return (self.flags & 0x10) != 0

    @property
    def is_fin(self):
        return (self.flags & 0x01) != 0
