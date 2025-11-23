import socket
import time
import sys


def run_sender():
    # Usage: python3 sender.py [target_ip]
    # Default to 10.0.0.2 (h2) if not provided
    target_ip = sys.argv[1] if len(sys.argv) > 1 else "10.0.0.2"
    target_port = 8080

    # Create UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # CRITICAL: Set a timeout.
    # Your link delay is 800ms one-way, so Round Trip Time (RTT) is ~1.6 seconds.
    # We set timeout to 3.0 seconds. If we don't get a reply by then,
    # we assume the packet was lost due to the 'loss=15' parameter.
    sock.settimeout(3.0)

    print(f"Sending to {target_ip}:{target_port}")
    print("Press Ctrl+C to stop manually.\n")

    seq_num = 0

    try:
        while True:
            message = f"Ping {seq_num}"
            start_time = time.time()

            try:
                # Send data
                print(f"Sending '{message}'...")
                sock.sendto(message.encode("utf-8"), (target_ip, target_port))

                # Wait for response (Blocking call with timeout)
                data, server = sock.recvfrom(4096)
                end_time = time.time()

                # Calculate RTT
                rtt = end_time - start_time
                print(f"Success! Got '{data.decode('utf-8')}' | RTT: {rtt:.4f} seconds")

            except socket.timeout:
                # This block runs if the packet was dropped (15% chance)
                print(f"TIMEOUT! Packet '{message}' lost or delayed too long.")

            seq_num += 1

            # Wait a bit before sending the next one
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nStopping sender.")
    finally:
        sock.close()


if __name__ == "__main__":
    run_sender()
