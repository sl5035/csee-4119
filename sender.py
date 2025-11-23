import socket
import sys
import time
import os
from tcp_packet import TCPPacket


def run_sender():
    target_ip = sys.argv[1] if len(sys.argv) > 1 else "10.0.0.2"
    target_port = 8080
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Short timeout allows us to check for ACKs frequently without blocking sending
    sock.settimeout(0.1)

    # Constants
    MSS = 1024
    WINDOW_SIZE = 4 * MSS  # 4 KB Window

    # Initial Sequence Numbers
    client_seq = 100
    server_response_seq = 0

    # --- 1. HANDSHAKE (Standard) ---
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

    # --- 2. DATA TRANSFER (SLIDING WINDOW) ---
    filename = "tosend.bin"
    if not os.path.exists(filename):
        print(f"Error: {filename} not found.")
        return

    # Read entire file into memory
    with open(filename, "rb") as f:
        file_data = f.read()

    total_bytes = len(file_data)
    print(f"\n--- Sending file: {filename} ({total_bytes} bytes) ---")

    # State Variables
    # send_base: The oldest unacknowledged sequence number
    # next_seq_num: The sequence number of the next packet to be sent
    base_seq_initial = client_seq
    send_base = client_seq
    next_seq_num = client_seq

    # Loop until all data is ACKed
    while send_base < (base_seq_initial + total_bytes):

        # A. SEND LOOP: Fill the window
        # While we have room in the window AND valid data to send
        while (next_seq_num < send_base + WINDOW_SIZE) and (
            next_seq_num < base_seq_initial + total_bytes
        ):

            # Calculate offset in the file
            offset = next_seq_num - base_seq_initial

            # Slice the data (up to MSS)
            chunk = file_data[offset : offset + MSS]

            # Create Packet
            pkt = TCPPacket(
                seq_num=next_seq_num, ack_num=server_response_seq, flags=0, data=chunk
            )

            sock.sendto(pkt.to_bytes(), (target_ip, target_port))
            # print(f"Sent Seq={next_seq_num} Len={len(chunk)}")

            # Advance next_seq_num
            next_seq_num += len(chunk)

        # B. RECEIVE LOOP: Process ACKs
        # We try to receive ACKs. If we get one, we slide send_base.
        # If we time out, we loop back (and potentially retransmit later, but for Step 5 no loss assumed)
        try:
            data, addr = sock.recvfrom(1024)
            ack_pkt = TCPPacket.from_bytes(data)

            if ack_pkt.is_ack:
                # Cumulative ACK check
                if ack_pkt.ack_num > send_base:
                    # print(f"Got ACK={ack_pkt.ack_num}. Sliding Window.")
                    send_base = ack_pkt.ack_num

        except socket.timeout:
            # No ACK received recently, just loop back
            pass

    print(f"File sending complete.")

    # --- 3. TEARDOWN (Modified sequence numbers) ---
    print("\n--- Initiating Connection Teardown ---")
    # Update client_seq to match where we left off
    client_seq = send_base

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

            if resp.is_fin:
                server_response_seq = resp.seq_num + 1
                last_ack = TCPPacket(
                    seq_num=client_seq + 1, ack_num=server_response_seq, flags=16
                )
                sock.sendto(last_ack.to_bytes(), (target_ip, target_port))
                print("Sent Final ACK. CLOSED.")

        except socket.timeout:
            print("Timeout waiting for FIN-ACK.")

    sock.close()


if __name__ == "__main__":
    run_sender()
