import socket
import struct
import hashlib
import os
import time

# Constants
SERVER_IP = '127.0.0.1'
SERVER_PORT = 9000
CHUNK_SIZE = 1024  # Size of each chunk in bytes
OUTPUT_DIR = "downloads"  # Directory to save downloaded files

# Ensure the output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

def calculate_checksum(data):
    """Calculate a simple checksum for the given data."""
    return hashlib.md5(data).hexdigest()

def request_file_list(client_socket):
    """Request and display the list of available files from the server."""
    client_socket.sendto(b"LIST", (SERVER_IP, SERVER_PORT))
    file_list, _ = client_socket.recvfrom(4096)
    print("Available files:")
    for line in file_list.decode().splitlines():
        file_name = line.split()[0]  # Extract only the file name, ignore size
        print(file_name)

def download_file(client_socket, file_name):
    """Download a file from the server in chunks."""
    output_file = os.path.join(OUTPUT_DIR, file_name)

    with open(output_file, 'wb') as f:
        offset = 0
        while True:
            # Send download request for the current chunk
            command = f"DOWNLOAD {file_name} {offset}"
            client_socket.sendto(command.encode(), (SERVER_IP, SERVER_PORT))

            # Receive the chunk from the server
            packet, _ = client_socket.recvfrom(4096)

            # Kiểm tra độ dài gói tin
            if len(packet) < 36:
                print(f"Error: received packet is too small ({len(packet)} bytes).")
                break

            # Unpack the packet to get sequence_number and checksum
            sequence_number, checksum = struct.unpack("!I32s", packet[:36])

            # Extract the chunk data (phần còn lại sau checksum)
            chunk_data = packet[36:]

            # Verify the checksum
            received_checksum = checksum.decode()
            if calculate_checksum(chunk_data) != received_checksum:
                print(f"Checksum mismatch for chunk {sequence_number}. Retrying...")
                continue

            # Write the chunk to the file
            f.write(chunk_data)
            print(f"Downloaded chunk {sequence_number}")

            # Check if the chunk size is less than the CHUNK_SIZE (indicating EOF)
            if len(chunk_data) < CHUNK_SIZE:
                print("File download complete.")
                break

            # Update offset for next chunk
            offset += CHUNK_SIZE

def main():
    # Initialize client
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.settimeout(5)  # Set timeout for responses

    try:
        while True:
            print("\nOptions:")
            print("1. List available files")
            print("2. Download a file")
            print("3. Exit")
            choice = input("Enter your choice: ")

            if choice == "1":
                request_file_list(client_socket)
            elif choice == "2":
                file_name = input("Enter the name of the file to download: ")
                download_file(client_socket, file_name)
            elif choice == "3":
                print("Exiting...")
                break
            else:
                print("Invalid choice. Please try again.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        client_socket.close()

if __name__ == "__main__":
    main()
