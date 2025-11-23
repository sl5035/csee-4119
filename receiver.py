import socket
from tcp_packet import TCPPacket


def run_receiver():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", 8080))
    print("Receiver listening on 8080...")

    server_seq = 200

    # We will write incoming data here
    output_file = open("received.bin", "wb")

    state = 0  # 0=Listen, 1=Established, 2=Closing

    while True:
        try:
            # Buffer increased to accommodate MSS + Header
            data, addr = sock.recvfrom(2048)
            packet = TCPPacket.from_bytes(data)
            if not packet:
                continue

            # --- HANDSHAKE ---
            if state == 0 and packet.is_syn:
                print(" -> Got SYN.")
                reply = TCPPacket(
                    seq_num=server_seq, ack_num=packet.seq_num + 1, flags=18
                )
                sock.sendto(reply.to_bytes(), addr)
                server_seq += 1

            elif state == 0 and packet.is_ack:
                print(" -> Connection ESTABLISHED. Waiting for file...")
                state = 1

            # --- DATA PHASE ---
            elif state == 1 and len(packet.data) > 0:
                # In Step 4 (No ACKs), we just blindly write the data
                # Ideally, we would check packet.seq_num here to ensure order
                output_file.write(packet.data)
                output_file.flush()  # Ensure it hits the disk

                # We do NOT send an ACK here for Step 4

            # --- TEARDOWN ---
            elif state == 1 and packet.is_fin:
                print(f" -> Got FIN. Saving file and closing.")
                output_file.close()  # Close the file

                # Send ACK
                ack_pkt = TCPPacket(
                    seq_num=server_seq, ack_num=packet.seq_num + 1, flags=16
                )
                sock.sendto(ack_pkt.to_bytes(), addr)

                # Send FIN
                fin_pkt = TCPPacket(
                    seq_num=server_seq, ack_num=packet.seq_num + 1, flags=17
                )
                sock.sendto(fin_pkt.to_bytes(), addr)
                server_seq += 1
                state = 2

            elif state == 2 and packet.is_ack:
                print(" -> CLOSED.")
                state = 0
                server_seq = 200
                output_file = open("received.bin", "wb")  # Reset for next run

        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    run_receiver()
