import struct


class TCPPacket:
    def __init__(self, seq_num=0, ack_num=0, flags=0, data=b""):
        self.seq_num = seq_num
        self.ack_num = ack_num
        self.flags = flags
        self.window = 1024 * 4
        self.checksum = 0
        self.urg_ptr = 0
        self.data = data

    @staticmethod
    def create_header(seq_num, ack_num, flags):
        # Header Length (Data Offset) is 4 words (16 bytes)
        # Shift 12 bits left
        data_offset = 4 << 12
        flags_field = data_offset | flags

        # Pack !IIHHHH (Network byte order)
        header = struct.pack("!IIHHHH", seq_num, ack_num, flags_field, 4096, 0, 0)
        return header

    def to_bytes(self):
        header = self.create_header(self.seq_num, self.ack_num, self.flags)
        return header + self.data

    @staticmethod
    def from_bytes(packet_data):
        if len(packet_data) < 16:
            return None

        header_data = packet_data[:16]
        payload = packet_data[16:]

        unpacked = struct.unpack("!IIHHHH", header_data)

        seq_num = unpacked[0]
        ack_num = unpacked[1]
        flags_field = unpacked[2]
        flags = flags_field & 0x3F

        return TCPPacket(seq_num, ack_num, flags, payload)

    # Flag Helpers
    @property
    def is_syn(self):
        return (self.flags & 0x02) != 0

    @property
    def is_ack(self):
        return (self.flags & 0x10) != 0

    @property
    def is_fin(self):
        return (self.flags & 0x01) != 0

    def __str__(self):
        flags_str = []
        if self.is_syn:
            flags_str.append("SYN")
        if self.is_ack:
            flags_str.append("ACK")
        if self.is_fin:
            flags_str.append("FIN")
        return f"Seq={self.seq_num} Ack={self.ack_num} Flags={','.join(flags_str)}"
