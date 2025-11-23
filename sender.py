import socket
import sys
import time
from tcp_packet import TCPPacket


def run_sender():
    target_ip = sys.argv[1] if len(sys.argv) > 1 else "10.0.0.2"
    target_port = 8080
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(2.0)  # 2s timeout (just above RTT)

    # Initial Sequence Number
    client_seq = 100

    # Handshake State
    handshake_done = False

    print(f"Starting 3-Way Handshake with {target_ip}...")

    while not handshake_done:
        try:
            # 1. Send SYN
            # Flags = SYN (2)
            syn_pkt = TCPPacket(seq_num=client_seq, ack_num=0, flags=2)
            print(f"Sending SYN (Seq={client_seq})...")
            sock.sendto(syn_pkt.to_bytes(), (target_ip, target_port))

            # 2. Wait for SYN/ACK
            data, addr = sock.recvfrom(1024)
            response = TCPPacket.from_bytes(data)

            if response.is_syn and response.is_ack:
                print(f"Received SYN/ACK: {response}")

                if response.ack_num == client_seq + 1:
                    # 3. Send ACK
                    # Seq = client_seq + 1 (technically we consumed the SYN)
                    # Ack = received_seq + 1
                    # Flags = ACK (16)
                    ack_pkt = TCPPacket(
                        seq_num=client_seq + 1, ack_num=response.seq_num + 1, flags=16
                    )

                    print(
                        f"Sending ACK (Seq={ack_pkt.seq_num}, Ack={ack_pkt.ack_num})..."
                    )
                    sock.sendto(ack_pkt.to_bytes(), (target_ip, target_port))

                    print("\nConnection ESTABLISHED!")
                    handshake_done = True
                else:
                    print("Error: Invalid Ack Number received.")

        except socket.timeout:
            print("Timeout! Retrying handshake...")
        except Exception as e:
            print(f"Error: {e}")

    sock.close()


if __name__ == "__main__":
    run_sender()
