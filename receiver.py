import socket
import sys
from tcp_packet import TCPPacket


def main():
    if len(sys.argv) != 2:
        print("Usage: python receiver.py <filename>")
        return

    filename = sys.argv[1]
    ip = "0.0.0.0"
    port = 8080

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((ip, port))
    print(f"Listening on {port}.")

    # Initial Sequence Numbers
    server_seq = 200
    expected_seq = 0

    # State: 0=Wait for SYN, 1=Connected, 2=Closing
    state = 0

    # Prepare file handle
    try:
        outfile = open(filename, "wb")
    except IOError:
        print(f"Error: cannot open {filename} for writing")
        return

    while True:
        try:
            data, addr = sock.recvfrom(4096)
            pkt = TCPPacket.unpack(data)
            if not pkt:
                continue

            # 1. Handle Handshake (SYN)
            if state == 0 and pkt.is_syn:
                print(f"Received connection request from {addr}")
                expected_seq = pkt.seq + 1

                # Send SYN-ACK
                reply = TCPPacket(server_seq, expected_seq, 18)  # 18 = SYN|ACK
                sock.sendto(reply.pack(), addr)
                server_seq += 1

            elif state == 0 and pkt.is_ack and pkt.ack == server_seq:
                print("Connection established.")
                state = 1

            # 2. Handle Data
            elif state == 1 and len(pkt.data) > 0:
                if pkt.seq == expected_seq:
                    # Correct packet, write to disk
                    outfile.write(pkt.data)
                    outfile.flush()  # make sure it saves
                    expected_seq += len(pkt.data)
                else:
                    # Out of order or duplicate
                    # print(f"Gap detected: got {pkt.seq}, need {expected_seq}")
                    pass

                # Always send ACK for what we expect next (Cumulative ACK)
                ack = TCPPacket(server_seq, expected_seq, 16)  # 16 = ACK
                sock.sendto(ack.pack(), addr)

            # 3. Handle Teardown (FIN)
            elif state == 1 and pkt.is_fin:
                print("Received FIN. Closing connection.")
                outfile.close()

                expected_seq = pkt.seq + 1

                # Send ACK for the FIN
                ack = TCPPacket(server_seq, expected_seq, 16)
                sock.sendto(ack.pack(), addr)

                # Send our own FIN
                fin = TCPPacket(server_seq, expected_seq, 17)  # FIN|ACK
                sock.sendto(fin.pack(), addr)
                server_seq += 1
                state = 2

            # Final ACK wait
            elif state == 2 and pkt.is_ack:
                print("Connection closed cleanly.")
                # Reset for next client? Or just exit.
                # For this assignment, we can probably just exit or reset.
                state = 0
                server_seq = 200
                # Re-open file for next run if needed, or just break
                break

        except Exception as e:
            print(f"Error: {e}")
            break

    sock.close()


if __name__ == "__main__":
    main()
