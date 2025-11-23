import socket
from tcp_packet import TCPPacket


def run_receiver():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", 8080))
    print("Receiver listening on 8080...")

    server_seq = 200
    output_file = open("received.bin", "wb")

    state = 0  # 0=Listen, 1=Established, 2=Closing
    expected_seq = 0

    while True:
        try:
            data, addr = sock.recvfrom(2048)
            packet = TCPPacket.from_bytes(data)
            if not packet:
                continue

            # --- HANDSHAKE ---
            if state == 0 and packet.is_syn:
                print(" -> Got SYN.")
                expected_seq = packet.seq_num + 1
                reply = TCPPacket(seq_num=server_seq, ack_num=expected_seq, flags=18)
                sock.sendto(reply.to_bytes(), addr)
                server_seq += 1

            elif state == 0 and packet.is_ack:
                print(" -> Connection ESTABLISHED.")
                state = 1

            # --- DATA PHASE (GBN) ---
            elif state == 1 and len(packet.data) > 0:

                if packet.seq_num == expected_seq:
                    # Correct Packet: Write and Advance
                    output_file.write(packet.data)
                    output_file.flush()
                    expected_seq += len(packet.data)

                    # ACK the next expected byte
                    ack_reply = TCPPacket(
                        seq_num=server_seq, ack_num=expected_seq, flags=16
                    )
                    sock.sendto(ack_reply.to_bytes(), addr)

                elif packet.seq_num < expected_seq:
                    # Duplicate (Old) Packet: Just ACK expected_seq again
                    ack_reply = TCPPacket(
                        seq_num=server_seq, ack_num=expected_seq, flags=16
                    )
                    sock.sendto(ack_reply.to_bytes(), addr)

                else:
                    # Out-of-Order Packet (Gap detected)
                    # GBN logic: Discard packet, re-send ACK for expected_seq
                    print(
                        f"Gap! Got {packet.seq_num}, Need {expected_seq}. Discarding."
                    )
                    ack_reply = TCPPacket(
                        seq_num=server_seq, ack_num=expected_seq, flags=16
                    )
                    sock.sendto(ack_reply.to_bytes(), addr)

            # --- TEARDOWN ---
            elif state == 1 and packet.is_fin:
                print(f" -> Got FIN. Saving and closing.")
                output_file.close()
                expected_seq = packet.seq_num + 1

                ack_pkt = TCPPacket(seq_num=server_seq, ack_num=expected_seq, flags=16)
                sock.sendto(ack_pkt.to_bytes(), addr)

                fin_pkt = TCPPacket(seq_num=server_seq, ack_num=expected_seq, flags=17)
                sock.sendto(fin_pkt.to_bytes(), addr)
                state = 2

            elif state == 2 and packet.is_ack:
                print(" -> CLOSED.")
                state = 0
                server_seq = 200
                output_file = open("received.bin", "wb")

        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    run_receiver()
