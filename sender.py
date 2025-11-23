import socket
import sys
import time
import os
from tcp_packet import TCPPacket


# GBN Constants
MSS = 1024
WINDOW_SIZE = 4 * MSS
TIMEOUT = 1.5


def main():
    if len(sys.argv) != 3:
        print("Usage: python sender.py <destination_ip> <filename>")
        return

    dest_ip = sys.argv[1]
    filename = sys.argv[2]
    dest_port = 8080

    # Setup socket with a short timeout for non-blocking checks
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(0.05)

    # Check file
    if not os.path.exists(filename):
        print(f"File {filename} does not exist.")
        return

    with open(filename, "rb") as f:
        file_data = f.read()

    total_bytes = len(file_data)
    print(f"Sending {filename} ({total_bytes} bytes) to {dest_ip}...")

    # Sequence tracking
    seq = 0  # My sequence number
    server_seq = 0  # What the server is at

    # --- Handshake ---
    connected = False
    while not connected:
        try:
            # Send SYN
            syn = TCPPacket(seq, 0, 2)  # 2 = SYN
            sock.sendto(syn.pack(), (dest_ip, dest_port))

            # Wait for SYN-ACK (longer timeout for handshake)
            sock.settimeout(1.0)
            raw, addr = sock.recvfrom(1024)
            resp = TCPPacket.unpack(raw)

            if resp and resp.is_syn and resp.is_ack:
                seq += 1
                server_seq = resp.seq + 1

                # Send ACK
                ack = TCPPacket(seq, server_seq, 16)  # 16 = ACK
                sock.sendto(ack.pack(), (dest_ip, dest_port))
                print("Connected!")
                connected = True
                sock.settimeout(0.01)  # Restore short timeout

        except socket.timeout:
            print("Handshake timeout, retrying...")

    # --- Transfer Loop (GBN) ---
    base = seq  # oldest unacked byte
    next_seq = seq  # next byte to send
    initial_seq = seq  # kept purely for offset calculation

    start_time = None  # Timer for the base packet

    while base < (initial_seq + total_bytes):

        # 1. Send packets if window allows
        while next_seq < base + WINDOW_SIZE and next_seq < initial_seq + total_bytes:
            offset = next_seq - initial_seq
            chunk = file_data[offset : offset + MSS]

            pkt = TCPPacket(next_seq, server_seq, 0, chunk)
            sock.sendto(pkt.pack(), (dest_ip, dest_port))

            if base == next_seq:
                start_time = time.time()

            next_seq += len(chunk)

        # 2. Receive ACKs
        try:
            raw, addr = sock.recvfrom(1024)
            ack_pkt = TCPPacket.unpack(raw)

            if ack_pkt and ack_pkt.is_ack:
                if ack_pkt.ack > base:
                    # Cumulative ACK - slide window
                    base = ack_pkt.ack

                    if base == next_seq:
                        start_time = None  # Window empty
                    else:
                        start_time = time.time()  # Restart timer

        except socket.timeout:
            pass  # Just checking the timer

        # 3. Check Timeout
        if start_time and (time.time() - start_time > TIMEOUT):
            print(f"Timeout on seq {base}. Retransmitting window.")
            start_time = time.time()

            # GBN: Go back to base and resend everything up to next_seq
            curr = base
            while curr < next_seq:
                offset = curr - initial_seq
                chunk = file_data[offset : offset + MSS]

                pkt = TCPPacket(curr, server_seq, 0, chunk)
                sock.sendto(pkt.pack(), (dest_ip, dest_port))
                curr += len(chunk)

    print("File data sent.")

    # --- Teardown ---
    fin_acked = False
    attempts = 0
    sock.settimeout(1.0)  # Relaxed timeout for FINs

    while not fin_acked and attempts < 10:
        try:
            # Send FIN
            fin = TCPPacket(base, server_seq, 1)  # 1 = FIN
            sock.sendto(fin.pack(), (dest_ip, dest_port))

            raw, addr = sock.recvfrom(1024)
            resp = TCPPacket.unpack(raw)

            if resp.is_ack and resp.ack == base + 1:
                fin_acked = True

            if resp.is_fin:
                # Ack the server's FIN
                server_seq = resp.seq + 1
                final_ack = TCPPacket(base + 1, server_seq, 16)
                sock.sendto(final_ack.pack(), (dest_ip, dest_port))
                print("Connection closed.")

        except socket.timeout:
            attempts += 1
            print("Closing...")

    sock.close()


if __name__ == "__main__":
    main()
