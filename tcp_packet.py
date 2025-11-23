import struct


class TCPPacket:
    def __init__(self, seq_num=0, ack_num=0, flags=0, data=b""):
        self.seq_num = seq_num
        self.ack_num = ack_num
        self.flags = flags
        self.window = 1024 * 4  # Fixed window size as per spec
        self.checksum = 0  # Not used
        self.urg_ptr = 0  # Not used
        self.data = data

    @staticmethod
    def create_header(seq_num, ack_num, flags):
        # Flags constants
        # FIN=1, SYN=2, RST=4, PSH=8, ACK=16, URG=32

        # Standard TCP Data Offset is 5 (5 * 4 bytes = 20 bytes header)
        # We shift it 12 bits to the left to put it in the top 4 bits of the 16-bit field
        data_offset = 5 << 12
        flags_field = data_offset | flags

        # Pack into 16 bytes (Network byte order !)
        # I = 4 bytes (Seq)
        # I = 4 bytes (Ack)
        # H = 2 bytes (Flags/Offset)
        # H = 2 bytes (Window)
        # H = 2 bytes (Checksum)
        # H = 2 bytes (Urgent)
        header = struct.pack(
            "!IIHHHH", seq_num, ack_num, flags_field, 4096, 0, 0  # Window  # Checksum
        )  # Urgent
        return header

    def to_bytes(self):
        header = self.create_header(self.seq_num, self.ack_num, self.flags)
        return header + self.data

    @staticmethod
    def from_bytes(packet_data):
        # Header is 16 bytes long (since we removed the 4-byte ports)
        if len(packet_data) < 16:
            return None

        header_data = packet_data[:16]
        payload = packet_data[16:]

        # Unpack
        unpacked = struct.unpack("!IIHHHH", header_data)

        seq_num = unpacked[0]
        ack_num = unpacked[1]
        flags_field = unpacked[2]

        # Extract flags (lower 6 bits)
        flags = flags_field & 0x3F

        return TCPPacket(seq_num, ack_num, flags, payload)

    # Helper properties for flags
    @property
    def is_syn(self):
        return (self.flags & 0x02) != 0

    @property
    def is_ack(self):
        return (self.flags & 0x10) != 0

    def __str__(self):
        flags_str = []
        if self.is_syn:
            flags_str.append("SYN")
        if self.is_ack:
            flags_str.append("ACK")
        return f"Seq={self.seq_num} Ack={self.ack_num} Flags={','.join(flags_str)}"
