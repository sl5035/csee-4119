import socket
import sys
from tcp_packet import TCPPacket


def run_receiver():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", 8080))
    print("Receiver listening on 8080...")

    # Initial Sequence Number for the receiver
    server_seq = 200
    expected_seq = 0  # Will be set upon first SYN

    # State tracking
    connection_established = False

    while True:
        try:
            data, addr = sock.recvfrom(1024 + 16)
            packet = TCPPacket.from_bytes(data)

            if not packet:
                continue

            print(f"Received: {packet} from {addr}")

            # Handshake Step 1: Handle SYN
            if packet.is_syn and not packet.is_ack:
                print(" -> Got SYN. Sending SYN/ACK...")

                # We expect the next packet to have seq + 1
                expected_seq = packet.seq_num + 1

                # Create SYN/ACK
                # Ack Num = Received Seq + 1
                # Seq Num = Server's own sequence number
                # Flags = SYN (2) | ACK (16) = 18
                reply = TCPPacket(
                    seq_num=server_seq, ack_num=packet.seq_num + 1, flags=18
                )

                sock.sendto(reply.to_bytes(), addr)

            # Handshake Step 3: Handle ACK
            elif packet.is_ack and not packet.is_syn:
                if packet.ack_num == server_seq + 1:
                    if not connection_established:
                        print(" -> Got ACK. Connection ESTABLISHED!")
                        connection_established = True
                    else:
                        print(" -> Got duplicate ACK (Already established).")

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    run_receiver()
