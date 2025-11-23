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

    # State -> Wait for SYN: 0, Connected: 1, Closing: 2
    state = 0

    # File handling
    try:
        outfile = open(filename, "wb")
    except IOError:
        print(f"Error: cannot open {filename} for writing.")
        return

    while True:
        try:
            data, addr = sock.recvfrom(4096)
            pkt = TCPPacket.unpack(data)
            if not pkt:
                continue

            # 1. Handle Handshake (SYN)
            if state == 0 and pkt.is_syn:
                print(f"Received connection request from {addr}.")
                expected_seq = pkt.seq + 1

                # Send SYN-ACK
                reply = TCPPacket(server_seq, expected_seq, 18)  # SYN | ACK = 18
                sock.sendto(reply.pack(), addr)
                server_seq += 1

            elif state == 0 and pkt.is_ack and pkt.ack == server_seq:
                print("Connection established.")
                state = 1

            # 2. Handle Data
            elif state == 1 and len(pkt.data) > 0:
                if pkt.seq == expected_seq:  # Correct packet -> write to disk
                    outfile.write(pkt.data)
                    outfile.flush()
                    expected_seq += len(pkt.data)
                else:
                    print(f"Gap detected: got {pkt.seq}, need {expected_seq}.")
                    pass

                # Always send ACK (Cumulative ACK)
                ack = TCPPacket(server_seq, expected_seq, 16)  # ACK flag is 16
                sock.sendto(ack.pack(), addr)

            # 3. Handle Teardown (FIN)
            elif state == 1 and pkt.is_fin:
                print("Received FIN. Closing connection.")
                outfile.close()

                expected_seq = pkt.seq + 1

                # Send ACK for the FIN
                ack = TCPPacket(server_seq, expected_seq, 16)  # ACK flag is 16
                sock.sendto(ack.pack(), addr)

                # Send FIN
                fin = TCPPacket(server_seq, expected_seq, 17)  # FIN | ACK = 17
                sock.sendto(fin.pack(), addr)
                server_seq += 1
                state = 2

            # Final ACK wait
            elif state == 2 and pkt.is_ack:
                print("Connection closed cleanly.")

                state = 0
                server_seq = 200

                break  # TODO: handle this break?

        except Exception as e:
            print(f"Error: {e}")
            break

    sock.close()


if __name__ == "__main__":
    main()
