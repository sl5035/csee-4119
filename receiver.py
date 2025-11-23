import socket
from tcp_packet import TCPPacket


def run_receiver():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", 8080))
    print("Receiver listening on 8080...")

    server_seq = 200
    expected_seq = 0

    # State: 0=Listen, 1=Established, 2=Closing
    state = 0

    while True:
        try:
            data, addr = sock.recvfrom(1024 + 16)
            packet = TCPPacket.from_bytes(data)
            if not packet:
                continue

            print(f"Received: {packet} from {addr}")

            # --- HANDSHAKE PHASE ---
            if state == 0 and packet.is_syn:
                print(" -> Got SYN. Sending SYN/ACK...")
                expected_seq = packet.seq_num + 1

                reply = TCPPacket(
                    seq_num=server_seq, ack_num=expected_seq, flags=18
                )  # SYN | ACK
                sock.sendto(reply.to_bytes(), addr)
                # Increment server seq because SYN consumes 1
                server_seq += 1

            elif state == 0 and packet.is_ack and packet.ack_num == server_seq:
                print(" -> Got ACK. Connection ESTABLISHED!")
                state = 1

            # --- DATA PHASE (Skipped for now) ---

            # --- TEARDOWN PHASE ---
            elif state == 1 and packet.is_fin:
                print(" -> Got FIN. Beginning Teardown.")
                # 1. Send ACK for the Client's FIN
                # FIN consumes 1 sequence number
                expected_seq = packet.seq_num + 1

                ack_pkt = TCPPacket(
                    seq_num=server_seq, ack_num=expected_seq, flags=16
                )  # ACK
                sock.sendto(ack_pkt.to_bytes(), addr)
                print(f"    Sent ACK (Ack={expected_seq})")

                # 2. Send Server's FIN
                # (In real TCP, app would trigger this, but we do it immediately)
                fin_pkt = TCPPacket(
                    seq_num=server_seq, ack_num=expected_seq, flags=17
                )  # FIN | ACK (Usually carries ACK info too)
                sock.sendto(fin_pkt.to_bytes(), addr)
                print(f"    Sent FIN (Seq={server_seq})")
                server_seq += 1
                state = 2  # Last ACK Wait

            elif state == 2 and packet.is_ack and packet.ack_num == server_seq:
                print(" -> Got Final ACK. Connection CLOSED cleanly.")
                # Reset for next test or exit
                state = 0
                server_seq = 200

        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    run_receiver()
