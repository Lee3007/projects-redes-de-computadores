import hashlib
import socket
import struct


def calculate_sha256(file_path):
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as file:
        for chunk in iter(lambda: file.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def calculate_sha256_of_file(file):
    sha256_hash = hashlib.sha256()
    with file:
        for chunk in iter(lambda: file.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def send_message(sock: socket.socket, message: bytes):
    message_len = struct.pack(">I", len(message))
    message_to_send = message_len + message
    sock.sendall(message_to_send)


def recv_message(sock: socket.socket):
    message_length = _recv_num_of_bytes(sock, 4)
    if not message_length:
        return None
    message_length = struct.unpack(">I", message_length)[0]
    return _recv_num_of_bytes(sock, message_length)


def _recv_num_of_bytes(sock: socket.socket, num: int):
    data = bytearray()
    while len(data) < num:
        packet = sock.recv(num - len(data))
        if not packet:
            return None
        data.extend(packet)
    return data
