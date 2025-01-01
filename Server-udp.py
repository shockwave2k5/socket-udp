import socket
import os
import struct
import hashlib

# Constants
CHUNK_SIZE = 1024  # Size of each chunk in bytes
SERVER_IP = '127.0.0.1'
SERVER_PORT = 9000
FILE_LIST = "file_list.txt"  # File containing list of available files
SERVERFILES_DIR = "Serverfiles"  # Thư mục chứa các tệp tin zip

def calculate_checksum(data):
    """Calculate a simple checksum for the given data."""
    return hashlib.md5(data).hexdigest()

def send_chunk(server_socket, client_address, file_name, offset):
    """Send a chunk of the file to the client."""
    try:
        with open(os.path.join(SERVERFILES_DIR, file_name), 'rb') as file:
            file.seek(offset)
            chunk = file.read(CHUNK_SIZE)
            checksum = calculate_checksum(chunk)
            sequence_number = offset // CHUNK_SIZE
            # Create packet: [sequence_number|checksum|chunk_data]
            packet = struct.pack(f"!I32s{len(chunk)}s", sequence_number, checksum.encode(), chunk)
            server_socket.sendto(packet, client_address)
    except Exception as e:
        print(f"Error sending chunk: {e}")

def main():
    # Initialize server
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((SERVER_IP, SERVER_PORT))
    print(f"Server listening on {SERVER_IP}:{SERVER_PORT}")

    while True:
        try:
            # Receive request from client
            data, client_address = server_socket.recvfrom(1024)
            command = data.decode().strip()

            if command == "LIST":
                # Send list of files
                if os.path.exists(FILE_LIST):
                    with open(FILE_LIST, 'r') as f:
                        file_data = f.read().encode()
                        server_socket.sendto(file_data, client_address)
                else:
                    server_socket.sendto(b"ERROR: File list not found", client_address)

            elif command.startswith("DOWNLOAD"):
                _, file_name, offset = command.split()
                offset = int(offset)

                if os.path.exists(os.path.join(SERVERFILES_DIR, file_name)):
                    send_chunk(server_socket, client_address, file_name, offset)
                else:
                    server_socket.sendto(b"ERROR: File not found", client_address)

        except KeyboardInterrupt:
            print("Server shutting down...")
            break
        except Exception as e:
            print(f"Error: {e}")

    server_socket.close()

if __name__ == "__main__":
    main()
