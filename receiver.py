import socket


def run_receiver():
    # Standard UDP setup
    # AF_INET = IPv4, SOCK_DGRAM = UDP
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Bind to all interfaces on port 8080
    # In Mininet, h2 usually has IP 10.0.0.2
    server_address = ("0.0.0.0", 8080)
    print(f"Receiver listening on port 8080...")
    sock.bind(server_address)

    while True:
        try:
            # Receive data (buffer size 4096 is plenty for this test)
            data, address = sock.recvfrom(4096)

            if data:
                message = data.decode("utf-8")
                print(f"Received: '{message}' from {address}")

                # Echo the data back to the sender to test bidirectional traffic
                reply = f"ACK: {message}"
                sock.sendto(reply.encode("utf-8"), address)

        except KeyboardInterrupt:
            print("\nShutting down receiver.")
            break
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    run_receiver()
