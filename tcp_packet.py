import struct


class TCPPacket:
    def __init__(self, seq=0, ack=0, flags=0, data=b""):
        self.seq = seq
        self.ack = ack
        self.flags = flags
        self.data = data

    def pack(self):
        # Header consists of 16 bytes: seq(4), ack(4), flags(2), win(2), check(2), urg(2) (20 bytes - 32 bits from the instruction assignment)
        offset_flags = (4 << 12) | self.flags  # offset 4 shifted left by 12 bits

        header = struct.pack(
            "!IIHHHH",
            self.seq,
            self.ack,
            offset_flags,
            4096,
            0,
            0,
        )
        return header + self.data

    @staticmethod
    def unpack(data):
        if len(data) < 16:
            return None

        header = data[:16]
        payload = data[16:]

        # Ignore the last 3 values
        seq, ack, flags_raw, _, _, _ = struct.unpack("!IIHHHH", header)

        # Mask out the offset -> from the pack method
        flags = flags_raw & 0x3F

        return TCPPacket(seq, ack, flags, payload)

    # Helpers
    @property
    def is_syn(self):
        return (self.flags & 0x02) != 0

    @property
    def is_ack(self):
        return (self.flags & 0x10) != 0

    @property
    def is_fin(self):
        return (self.flags & 0x01) != 0
