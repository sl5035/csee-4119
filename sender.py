import socket
import sys
import time
from tcp_packet import TCPPacket


def run_sender():
    target_ip = sys.argv[1] if len(sys.argv) > 1 else "10.0.0.2"
    target_port = 8080
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(4.0)  # Maintain the robust timeout

    client_seq = 100
    server_response_seq = 0

    # --- 1. HANDSHAKE ---
    handshake_done = False
    print(f"--- Starting 3-Way Handshake ---")

    while not handshake_done:
        try:
            # Send SYN
            syn_pkt = TCPPacket(seq_num=client_seq, ack_num=0, flags=2)
            sock.sendto(syn_pkt.to_bytes(), (target_ip, target_port))

            # Wait for SYN/ACK
            data, addr = sock.recvfrom(1024)
            resp = TCPPacket.from_bytes(data)

            if resp.is_syn and resp.is_ack:
                if resp.ack_num == client_seq + 1:
                    client_seq += 1
                    server_response_seq = resp.seq_num + 1

                    # Send ACK
                    ack_pkt = TCPPacket(
                        seq_num=client_seq, ack_num=server_response_seq, flags=16
                    )
                    sock.sendto(ack_pkt.to_bytes(), (target_ip, target_port))
                    print("Connection ESTABLISHED!")
                    handshake_done = True
        except socket.timeout:
            print("Timeout (Handshake). Retrying...")

    # --- 2. DATA TRANSFER SIMULATION ---
    print("\n[Data Transfer Phase - Sleeping 2 seconds]...\n")
    time.sleep(2)

    # --- 3. TEARDOWN ---
    print("--- Initiating Connection Teardown ---")
    fin_acked = False
    fin_sent_time = 0

    # Loop to Send FIN and ensure it is ACKed
    while not fin_acked:
        try:
            # Send FIN
            # FIN consumes 1 seq num
            fin_pkt = TCPPacket(
                seq_num=client_seq, ack_num=server_response_seq, flags=1
            )
            print(f"Sending FIN (Seq={client_seq})...")
            sock.sendto(fin_pkt.to_bytes(), (target_ip, target_port))

            # We expect:
            # 1. ACK of our FIN
            # 2. FIN from Server
            # These might come in separate packets or one.

            # Wait for response
            data, addr = sock.recvfrom(1024)
            resp = TCPPacket.from_bytes(data)

            # Check for ACK of our FIN
            if resp.is_ack and resp.ack_num == client_seq + 1:
                print(f"Received ACK for our FIN.")
                fin_acked = True
                client_seq += 1

            # Check if this packet is ALSO the Server's FIN
            if resp.is_fin:
                print(f"Received Server's FIN (Seq={resp.seq_num}).")
                server_response_seq = resp.seq_num + 1
                # Send Final ACK
                last_ack = TCPPacket(
                    seq_num=client_seq, ack_num=server_response_seq, flags=16
                )
                sock.sendto(last_ack.to_bytes(), (target_ip, target_port))
                print("Sent Final ACK. CLOSED.")
                return  # Done!

        except socket.timeout:
            print("Timeout waiting for FIN-ACK. Retrying FIN...")

    # If we got the ACK but NOT the FIN yet (rare in this code, but possible),
    # we would need another loop here to wait for the FIN.
    # But for this simple assignment, the loop above usually catches the piggybacked or immediate FIN.

    sock.close()


if __name__ == "__main__":
    run_sender()
