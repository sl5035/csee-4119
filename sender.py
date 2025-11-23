import socket
import sys
import time
import os
from tcp_packet import TCPPacket


def run_sender():
    target_ip = sys.argv[1] if len(sys.argv) > 1 else "10.0.0.2"
    target_port = 8080
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Socket timeout must be much smaller than the GBN timeout
    # to allow the loop to constantly check the timer status.
    sock.settimeout(0.05)

    # --- CONSTANTS ---
    MSS = 1024
    WINDOW_SIZE = 4 * MSS
    GBN_TIMEOUT = 1.5  # 1,500 ms as requested

    # Sequence Numbers
    client_seq = 100
    server_response_seq = 0

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

    # --- 2. DATA TRANSFER (Go-Back-N) ---
    filename = "tosend.bin"
    if not os.path.exists(filename):
        # Create a dummy file if it doesn't exist
        with open(filename, "wb") as f:
            f.write(os.urandom(50000))
        print(f"Created {filename} with random data.")

    with open(filename, "rb") as f:
        file_data = f.read()

    total_bytes = len(file_data)
    print(f"\n--- Sending file: {filename} ({total_bytes} bytes) ---")

    base_seq_initial = client_seq
    send_base = client_seq
    next_seq_num = client_seq

    timer_start_time = None

    while send_base < (base_seq_initial + total_bytes):

        # A. SEND LOOP: Fill the window
        while (next_seq_num < send_base + WINDOW_SIZE) and (
            next_seq_num < base_seq_initial + total_bytes
        ):

            offset = next_seq_num - base_seq_initial
            chunk = file_data[offset : offset + MSS]

            pkt = TCPPacket(
                seq_num=next_seq_num, ack_num=server_response_seq, flags=0, data=chunk
            )
            sock.sendto(pkt.to_bytes(), (target_ip, target_port))

            # Start timer if send_base is sent (i.e., this is the oldest unacked packet)
            if send_base == next_seq_num:
                timer_start_time = time.time()

            next_seq_num += len(chunk)

        # B. RECEIVE ACKS
        try:
            data, addr = sock.recvfrom(1024)
            ack_pkt = TCPPacket.from_bytes(data)

            if ack_pkt.is_ack:
                # GBN Cumulative ACK Logic
                if ack_pkt.ack_num > send_base:
                    # Slide window
                    send_base = ack_pkt.ack_num

                    if send_base == next_seq_num:
                        # Window is empty (all acked)
                        timer_start_time = None
                    else:
                        # Window not empty, restart timer for the NEW oldest unacked
                        timer_start_time = time.time()

        except socket.timeout:
            # Just socket silence, move to timer check
            pass

        # C. TIMEOUT & RETRANSMISSION
        if timer_start_time is not None:
            time_elapsed = time.time() - timer_start_time

            if time_elapsed > GBN_TIMEOUT:
                print(f"[TIMEOUT] No ACK for {send_base}. Retransmitting Window...")

                # Restart Timer immediately
                timer_start_time = time.time()

                # Retransmit Loop: Resend from send_base up to next_seq_num
                retransmit_seq = send_base
                while retransmit_seq < next_seq_num:
                    offset = retransmit_seq - base_seq_initial
                    chunk = file_data[offset : offset + MSS]

                    pkt = TCPPacket(
                        seq_num=retransmit_seq,
                        ack_num=server_response_seq,
                        flags=0,
                        data=chunk,
                    )

                    sock.sendto(pkt.to_bytes(), (target_ip, target_port))
                    # print(f" -> Resent {retransmit_seq}")

                    retransmit_seq += len(chunk)

    print(f"File sending complete.")

    # --- 3. TEARDOWN ---
    print("\n--- Initiating Teardown ---")
    client_seq = send_base
    fin_acked = False
    attempts = 0
    while not fin_acked and attempts < 10:
        try:
            fin_pkt = TCPPacket(
                seq_num=client_seq, ack_num=server_response_seq, flags=1
            )
            sock.sendto(fin_pkt.to_bytes(), (target_ip, target_port))

            # Wait longer for FIN ACK
            sock.settimeout(1.0)
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
            attempts += 1
            print("Timeout waiting for FIN-ACK.")

    sock.close()


if __name__ == "__main__":
    run_sender()
