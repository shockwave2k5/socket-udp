import socket
import os
import hashlib
import time

SERVER_ADDRESS = ('127.0.0.1', 12345)
CHUNK_SIZE = 1024  # Kích thước mỗi gói tin
TIMEOUT = 2        # Timeout khi chờ ACK từ client

FILES_PATH = os.path.join(os.getcwd(), "Files")

def calculate_checksum(data):
    # Tính checksum (MD5) cho dữ liệu.
    return hashlib.md5(data).hexdigest()

def create_packet(seq_num, payload):
    # Tạo gói tin gồm: seq_num|checksum|payload
    checksum = calculate_checksum(payload)
    header = f"{seq_num}|{checksum}".encode()
    return header + b"|" + payload

def send_file_chunk(sock, client_addr, file_path, start, chunk_size):
    # Gửi một chunk của file đến client.
    with open(file_path, 'rb') as file:
        file.seek(start)
        sent_bytes = 0
        seq_num = 0

        while sent_bytes < chunk_size:
            # Đọc dữ liệu gói tin
            payload = file.read(min(CHUNK_SIZE, chunk_size - sent_bytes))
            if not payload:
                break

            # Tạo gói tin
            packet = create_packet(seq_num, payload)
            ack_received = False

            while not ack_received:
                try:
                    # Gửi gói tin đến client
                    sock.sendto(packet, client_addr)
                    sock.settimeout(TIMEOUT)

                    # Chờ phản hồi từ client
                    response, _ = sock.recvfrom(1024)
                    if response.decode().startswith(f"ACK {seq_num}"):
                        ack_received = True  # Đã nhận ACK
                    elif response.decode().startswith(f"NACK {seq_num}"):
                        print(f"Resending packet {seq_num}...")
                except socket.timeout:
                    print(f"Timeout for packet {seq_num}, resending...")
            
            # Chuyển sang gói tin tiếp theo
            sent_bytes += len(payload)
            seq_num += 1

def handle_client(sock):
    # Xử lý yêu cầu từ client.
    while True:
        try:
            # Nhận yêu cầu từ client
            data, client_addr = sock.recvfrom(1024)
            request = data.decode().split()
            command = request[0]

            if command == "DOWNLOAD":
                file_name = request[1]
                chunk_id = int(request[2])
                file_path = os.path.join(FILES_PATH, file_name)

                if not os.path.exists(file_path):
                    print(f"File {file_name} does not exist.")
                    sock.sendto(b"ERROR", client_addr)
                    continue

                # Tính toán vị trí chunk
                file_size = os.path.getsize(file_path)
                chunk_size = file_size // 4
                start = chunk_id * chunk_size
                end = start + chunk_size - 1 if chunk_id < 3 else file_size - 1

                print(f"Sending chunk {chunk_id} of {file_name} to {client_addr}...")
                send_file_chunk(sock, client_addr, file_path, start, end - start + 1)

            else:
                print(f"Invalid command from {client_addr}: {request}")
        except Exception as e:
            print(f"Error handling client: {e}")

def main():
    os.makedirs(FILES_PATH, exist_ok=True)

    # Tạo socket UDP
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind(SERVER_ADDRESS)
    print(f"Server is running on {SERVER_ADDRESS}...")

    try:
        handle_client(server_socket)
    except KeyboardInterrupt:
        print("Server is shutting down.")
    finally:
        server_socket.close()

if __name__ == "__main__":
    main()
