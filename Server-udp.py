import socket
import os
import hashlib
import time

PORT = socket.gethostbyname(socket.gethostname())
SERVER_ADDRESS = (PORT, 12345)
CHUNK_SIZE = 1024  # Kích thước mỗi gói tin
TIMEOUT = 2        # Timeout khi chờ ACK từ client

FILES_PATH = os.path.join(os.getcwd(), "Files")

def getSize(file):
    filepath = os.path.join(FILES_PATH, file)
    file_size = os.path.getsize(filepath)
    return file_size

def send_list_file(server_socket,client_socket):
    try:
        msg = ""
        with open("server_files.txt", 'r') as file:
            file_list = file.read()
            line = file_list.split("\n")
            for i in line:
                print(i)
                t = i.split(" ")
                t[1] = str(getSize(t[0]))
                msg = msg + t[0] + " " + t[1] + "\n"
            print(msg)
        server_socket.sendto(msg.encode(),client_socket)
        print("Send list file successfully")
    except Exception as e:
        print(f"Error: {e}")

def calculate_checksum(data):
    # Tính checksum (MD5) cho dữ liệu.
    return hashlib.md5(data).hexdigest()

def create_packet(seq_num, payload):
    # Tạo gói tin gồm: seq_num|checksum|payload
    checksum = calculate_checksum(payload)
    header = f"{seq_num}|{checksum}".encode()
    return header + b"\r\n\r\n" + payload

def send_file_chunk(sock,client_addr, file_path, start, chunk_size,sent_bytes,seq_num,last_send,chunk_id):
    # Gửi một chunk của file đến client.
    with open(file_path, 'rb') as file:
        file.seek(start[chunk_id])

        if sent_bytes[chunk_id] < chunk_size:
            # Đọc dữ liệu gói tin
            payload = file.read(min(CHUNK_SIZE, chunk_size - sent_bytes[chunk_id]))
            if not payload:
                return
            last_send[chunk_id] = len(payload)
            # Tạo gói tin
            packet = create_packet(seq_num[chunk_id], payload)
            sock.sendto(packet, client_addr)
            

            

def handle_client(sock):
    # Xử lý yêu cầu từ client.
    seq_num = [0,0,0,0]
    start = [0,0,0,0]
    sent_bytes = [0,0,0,0]
    last_send = [0,0,0,0]
    size = [0,0,0,0]
    end = 0
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
                start[chunk_id] = chunk_id * chunk_size
                end = start[chunk_id] + chunk_size - 1 if chunk_id < 3 else file_size - 1
                size[chunk_id] = end - start[chunk_id] + 1

                print(f"Sending chunk {chunk_id} of {file_name} to {client_addr}...")
                send_file_chunk(sock, client_addr, file_path, start, size[chunk_id],sent_bytes,seq_num,last_send,chunk_id)
            elif command == "SENDLIST":
                send_list_file(sock,client_addr)
            elif command == "NACK":
                chunk_id = int(request[2])
                seq = int(request[1])
                send_file_chunk(sock, client_addr, file_path, start, size[chunk_id] + 1,sent_bytes,seq_num,last_send,chunk_id)
            elif command == "ACK":
                chunk_id = int(request[2])
                seq = int(request[1])
                if seq == seq_num[chunk_id]:
                    seq_num[chunk_id] += 1
                    sent_bytes[chunk_id] += last_send[chunk_id]
                    start[chunk_id] += last_send[chunk_id]
                    send_file_chunk(sock, client_addr, file_path, start, size[chunk_id] + 1,sent_bytes,seq_num,last_send,chunk_id)
                else:
                    send_file_chunk(sock, client_addr, file_path, start, size[chunk_id] + 1,sent_bytes,seq_num,last_send,chunk_id)
            elif command != "NACK" and command != "ACK":
                print(f"Invalid command from {client_addr}: {request}")
            if sum(sent_bytes) >= sum(size):
                seq_num[:] = [0] * len(seq_num)
                start[:] = [0] * len(start)
                sent_bytes[:] = [0] * len(sent_bytes)
                last_send[:] = [0] * len(last_send)
                size[:] = [0] * len(size)
        except socket.timeout:
            continue
        
        
         

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
