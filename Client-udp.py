import socket
import hashlib
import os
import threading
import time

HOST = input("Nhap IP: ")
PORT = int(input("Nhap port: "))

SERVER_ADDRESS = (HOST,PORT)  
CHUNK_SIZE = 1024                      
TIMEOUT = 2                            
close_flag = False
barrier = threading.Barrier(4)
file_list = []

def getServerFile():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(b'SENDLIST - -',SERVER_ADDRESS)
    chunk_sizes = {}
    data, s = sock.recvfrom(1024)
    temp = data.decode().split("\n")
    if "" in temp:
        temp.remove("")
    for line in temp:
        t = line.split(" ")
        if chunk_sizes.get(t[0]) == None:
            chunk_sizes[t[0]] = int(t[1])
    sock.close()
    return chunk_sizes

def calculate_checksum(data):

    # Tính checksum cho dữ liệu.
    return hashlib.md5(data).hexdigest()

def parse_packet(packet):

    # Phân tích gói tin nhận được từ server.
    try:
        header, payload = packet.split(b'\r\n\r\n',2)
        seq_num, checksum = header.decode().split('|')
        return int(seq_num), checksum, payload
    except Exception as e:
        print(f"Error parsing packet: {e}")
        return None, None, None

def request_file_chunk(sock, file_name, chunk_id):

    # Yêu cầu tải một chunk từ server.
    request = f"DOWNLOAD {file_name} {chunk_id}".encode()
    sock.sendto(request, SERVER_ADDRESS)

def reliable_receive(sock, expected_seq,chunk_id):

    # Nhận dữ liệu tin cậy từ server.Kiểm tra thứ tự gói tin và checksum.
    while True:
        try:
            sock.settimeout(TIMEOUT)
            data, addr = sock.recvfrom(CHUNK_SIZE + 50)  # Dự phòng cho header
            seq_num, checksum, payload = parse_packet(data)

            # Kiểm tra thứ tự gói tin và checksum
            if seq_num == expected_seq and checksum == calculate_checksum(payload):
                # Gửi ACK cho server
                ack = f"ACK {seq_num} {chunk_id}".encode()
                sock.sendto(ack, addr)
                return payload
            else:
                # Gửi NACK nếu gói tin sai
                nack = f"NACK {expected_seq} {chunk_id}".encode()
                sock.sendto(nack, addr)
        except socket.timeout:
            # Timeout, gửi lại NACK
            nack = f"NACK {expected_seq} {chunk_id}".encode()
            sock.sendto(nack, SERVER_ADDRESS)

def download_chunk(sock,file_name, chunk_id, chunk_size, output_file):

    # Tải một chunk của file và lưu vào output_file.

    request_file_chunk(sock, file_name, chunk_id)
    received_bytes = 0
    with open(output_file, 'r+b') as f:
        f.seek(chunk_id * chunk_size)
        expected_seq = 0
        while received_bytes < chunk_size:
            payload = reliable_receive(sock, expected_seq,chunk_id)
            f.write(payload)
            received_bytes += len(payload)
            expected_seq += 1
        print(chunk_id)
    barrier.wait() #Đợi tất cả socket hoàn thành
    

def read_input_file(file_name):
    try:
        with open(file_name, 'r') as f:
            for line in f:
                if line.strip():  # Bỏ qua dòng trống
                    file_name = line  # Tên file
                    file_name = file_name.replace('\n', '')
                    file_list.append(file_name)
    finally:
        return file_list

def init_socket(num):
    sockets = []
    for i in range(num):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sockets.append(sock)
    return sockets

def handling():
    downloaded_files = []
    sockets = init_socket(4)
    input_file = "input.txt"
    num_chunks = 4
    server_files = getServerFile()
    print(server_files)
    start = time.time()
    file_list = read_input_file(input_file)
    while True:
        end = time.time()
        if end - start >= 5:
            start = end
            file_list = read_input_file(input_file)
        global close_flag
        try:
            for file_name in file_list:
                if server_files.get(file_name) == None:#check xem file co tren server ko, neu khong ti bo qua file do
                    continue
                if file_name in downloaded_files:
                    continue
                print(f"Downloading {file_name}...")
                chunk_size = server_files[file_name] // num_chunks
                output_file = os.path.join(os.getcwd(), file_name)
                print(chunk_size)
                # Tạo file rỗng
                with open(output_file, 'wb') as f:
                    f.close()

                threads = []
                for chunk_id in range(num_chunks):
                    thread = threading.Thread(target=download_chunk, args=(sockets[chunk_id],file_name, chunk_id, chunk_size, output_file))
                    threads.append(thread)
                    thread.start()

                # Chờ tất cả các thread hoàn thành

                for thread in threads:
                    thread.join()
                threads.clear()

                print(f"{file_name} downloaded successfully.")
                downloaded_files.append(file_name)
        except KeyboardInterrupt:
            close_flag = True
            for sock in sockets:
                sock.close()

def main():
    downloaded_files = []
    server_files = getServerFile()
    num_chunks = 4  # Số phần chia file
    for file_name in file_list:
        if server_files.get(file_name) == None:#check xem file co tren server ko, neu khong ti bo qua file do
            continue
        if file_name in downloaded_files:
            continue
        print(f"Downloading {file_name}...")
        chunk_size = server_files[file_name] // num_chunks
        output_file = os.path.join(os.getcwd(), file_name)
        print(chunk_size)
        # Tạo file rỗng
        with open(output_file, 'wb') as f:
            f.close()

        threads = []
        for chunk_id in range(num_chunks):
            thread = threading.Thread(target=download_chunk, args=(file_name, chunk_id, chunk_size, output_file))
            threads.append(thread)
            thread.start()

        # Chờ tất cả các thread hoàn thành

        for thread in threads:
            thread.join()
        threads.clear()

        print(f"{file_name} downloaded successfully.")
        downloaded_files.append(file_name)
if __name__ == "__main__":
    handling()
