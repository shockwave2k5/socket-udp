import socket
import hashlib
import os
import threading

SERVER_ADDRESS = ('127.0.0.1', 12345)  
CHUNK_SIZE = 1024                      
TIMEOUT = 2                            

def calculate_checksum(data):

    # Tính checksum cho dữ liệu.
    return hashlib.md5(data).hexdigest()

def parse_packet(packet):

    # Phân tích gói tin nhận được từ server.
    try:
        header, payload = packet.split(b'|', 2)
        seq_num, checksum = header.decode().split('|')
        return int(seq_num), checksum, payload
    except Exception as e:
        print(f"Error parsing packet: {e}")
        return None, None, None

def request_file_chunk(sock, file_name, chunk_id):

    # Yêu cầu tải một chunk từ server.
    request = f"DOWNLOAD {file_name} {chunk_id}".encode()
    sock.sendto(request, SERVER_ADDRESS)

def reliable_receive(sock, expected_seq):

    # Nhận dữ liệu tin cậy từ server.Kiểm tra thứ tự gói tin và checksum.
    while True:
        try:
            sock.settimeout(TIMEOUT)
            data, addr = sock.recvfrom(CHUNK_SIZE + 50)  # Dự phòng cho header
            seq_num, checksum, payload = parse_packet(data)

            # Kiểm tra thứ tự gói tin và checksum
            if seq_num == expected_seq and checksum == calculate_checksum(payload):
                # Gửi ACK cho server
                ack = f"ACK {seq_num}".encode()
                sock.sendto(ack, addr)
                return payload
            else:
                # Gửi NACK nếu gói tin sai
                nack = f"NACK {expected_seq}".encode()
                sock.sendto(nack, addr)
        except socket.timeout:
            # Timeout, gửi lại NACK
            nack = f"NACK {expected_seq}".encode()
            sock.sendto(nack, SERVER_ADDRESS)

def download_chunk(file_name, chunk_id, chunk_size, output_file):

    # Tải một chunk của file và lưu vào output_file.
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    request_file_chunk(sock, file_name, chunk_id)

    received_bytes = 0
    with open(output_file, 'r+b') as f:
        f.seek(chunk_id * chunk_size)
        expected_seq = 0

        while received_bytes < chunk_size:
            payload = reliable_receive(sock, expected_seq)
            f.write(payload)
            received_bytes += len(payload)
            expected_seq += 1

    sock.close()

def read_input_file(file_name):
    file_list = []
    chunk_sizes = []
    try:
        with open(file_name, 'r') as f:
            for line in f:
                if line.strip():  # Bỏ qua dòng trống
                    parts = line.split()
                    file_name = parts[0]  # Tên file
                    size_in_mb = int(parts[1].replace('MB', ''))  # Dung lượng file
                    file_list.append(file_name)
                    chunk_sizes.append(size_in_mb * 1024 * 1024)  # Chuyển MB -> Byte
    except Exception as e:
        print(f"Error reading file input.txt: {e}")
    return file_list, chunk_sizes

def main():
    input_file = "input.txt"
    file_list, chunk_sizes = read_input_file(input_file)
    num_chunks = 4  # Số phần chia file

    for file_name, total_size in zip(file_list, chunk_sizes):
        print(f"Downloading {file_name}...")
        chunk_size = total_size // num_chunks
        output_file = os.path.join(os.getcwd(), file_name)

        # Tạo file rỗng
        with open(output_file, 'wb') as f:
            f.truncate(total_size)

        threads = []
        for chunk_id in range(num_chunks):
            thread = threading.Thread(target=download_chunk, args=(file_name, chunk_id, chunk_size, output_file))
            threads.append(thread)
            thread.start()

        # Chờ tất cả các thread hoàn thành
        for thread in threads:
            thread.join()

        print(f"{file_name} downloaded successfully.")

if __name__ == "__main__":
    main()
