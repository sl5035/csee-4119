import socket
import sys
import time
import os
from tcp_packet import TCPPacket


def run_sender():
    target_ip = sys.argv[1] if len(sys.argv) > 1 else "10.0.0.2"
    target_port = 8080
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(3.0)  # Lower timeout since no loss

    client_seq = 100
    server_response_seq = 0
    mss = 1024  # Maximum Segment Size

    # --- 1. HANDSHAKE ---
    handshake_done = False
    print(f"--- Starting 3-Way Handshake ---")

    while not handshake_done:
        try:
            syn_pkt = TCPPacket(seq_num=client_seq, ack_num=0, flags=2)
            sock.sendto(syn_pkt.to_bytes(), (target_ip, target_port))
            data, addr = sock.recvfrom(1024)
            resp = TCPPacket.from_bytes(data)
            if resp.is_syn and resp.is_ack:
                client_seq += 1
                server_response_seq = resp.seq_num + 1
                ack_pkt = TCPPacket(
                    seq_num=client_seq, ack_num=server_response_seq, flags=16
                )
                sock.sendto(ack_pkt.to_bytes(), (target_ip, target_port))
                print("Connection ESTABLISHED!")
                handshake_done = True
        except socket.timeout:
            print("Timeout (Handshake). Retrying...")

    # --- 2. DATA TRANSFER (BLASTING) ---
    filename = "tosend.bin"
    print(f"\n--- Sending file: {filename} ---")

    if not os.path.exists(filename):
        print(f"Error: {filename} not found. Run the create file command first!")
        return

    with open(filename, "rb") as f:
        while True:
            # Read MSS bytes
            chunk = f.read(mss)
            if not chunk:
                break  # End of file

            # Create Packet
            # Note: No Flags set for data packets (usually PSH is used, but 0 is fine)
            pkt = TCPPacket(
                seq_num=client_seq, ack_num=server_response_seq, flags=0, data=chunk
            )

            # Send (No waiting for ACK per instructions)
            sock.sendto(pkt.to_bytes(), (target_ip, target_port))

            # Update Sequence Number
            client_seq += len(chunk)

    print(f"File sending complete. Final Seq={client_seq}")

    # --- 3. TEARDOWN ---
    print("\n--- Initiating Connection Teardown ---")
    fin_acked = False

    while not fin_acked:
        try:
            fin_pkt = TCPPacket(
                seq_num=client_seq, ack_num=server_response_seq, flags=1
            )
            sock.sendto(fin_pkt.to_bytes(), (target_ip, target_port))

            data, addr = sock.recvfrom(1024)
            resp = TCPPacket.from_bytes(data)

            if resp.is_ack and resp.ack_num == client_seq + 1:
                fin_acked = True
                client_seq += 1

            if resp.is_fin:
                server_response_seq = resp.seq_num + 1
                last_ack = TCPPacket(
                    seq_num=client_seq, ack_num=server_response_seq, flags=16
                )
                sock.sendto(last_ack.to_bytes(), (target_ip, target_port))
                print("Sent Final ACK. CLOSED.")

        except socket.timeout:
            print("Timeout waiting for FIN-ACK. Retrying FIN...")

    sock.close()


if __name__ == "__main__":
    run_sender()
