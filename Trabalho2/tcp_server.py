import os
import socket
import threading
from typing import Literal

from utils import calculate_sha256, recv_message, send_message

CLIENT_MODES = Literal["Command", "Chat"]


class TCP_Server:
    def __init__(self, host: str, port: int) -> None:
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((host, port))
        self.server_socket.listen(5)
        self.clients = []
        self.chat_clients = []
        self.running = True

        print(f"Server listening on {host}:{port}")
        self._run()

    def _run(self):
        server_chat_send_thread = threading.Thread(target=self.server_chat_send_handler)
        server_chat_send_thread.start()
        while self.running:
            client_socket, addr = self.server_socket.accept()
            self.clients.append(client_socket)
            client_handler = threading.Thread(
                target=self.handle_client, args=(client_socket,)
            )
            client_handler.start()

    def handle_client(self, client_socket: socket.socket) -> None:
        client_mode: CLIENT_MODES = "Command"

        with client_socket as sock:
            print(f"Accepted connection from {sock.getpeername()}")

            while self.running:
                if client_mode == "Command":
                    try:
                        message = recv_message(sock=sock)
                    except ConnectionResetError:
                        print(f"Connection reset by peer: {sock.getpeername()}")
                        break
                    split_message = message.split(b"<DELIMITER>")

                    if split_message[0] == b"Sair":
                        sock.shutdown(socket.SHUT_RDWR)
                        sock.close()
                        print("Connection closed")
                        break

                    elif split_message[0] == b"Chat":
                        self.chat_clients.append(sock)
                        client_mode = "Chat"

                    elif split_message[0] == b"Arquivo" and len(split_message) >= 2:
                        filename = split_message[1].decode("utf-8")
                        if not os.path.isfile(f"./server_files/{filename}"):
                            print(f"ERROR: File {filename} does not exist.")
                            send_message(
                                sock,
                                f"Arquivo<DELIMITER>NON_EXISTENT_FILE".encode("utf-8"),
                            )
                        else:
                            print(f"Reading file {filename} and sending to client...")
                            with open(f"./server_files/{filename}", "rb") as file:
                                start_message = f"Arquivo<DELIMITER>SUCCESS<DELIMITER>{filename}<DELIMITER>START".encode(
                                    "utf-8"
                                )
                                send_message(sock, start_message)
                                while True:
                                    data = file.read(1024)
                                    if not data:
                                        break
                                    message_header = f"Arquivo<DELIMITER>SUCCESS<DELIMITER>{filename}<DELIMITER>DATA<DELIMITER>".encode(
                                        "utf-8"
                                    )
                                    message_to_send = message_header + data
                                    send_message(sock, message_to_send)
                                hash = calculate_sha256(f"./server_files/{filename}")
                                hash_message = f"Arquivo<DELIMITER>SUCCESS<DELIMITER>{filename}<DELIMITER>HASH<DELIMITER>{hash}".encode(
                                    "utf-8"
                                )
                                send_message(sock, hash_message)
                                print(f"Successfully sent file {filename} to client.")

                elif client_mode == "Chat":
                    self.server_chat_rcv_handler(sock)
                    client_mode = "Command"

    def server_chat_send_handler(self):
        while True:
            chat_message = input()
            self.send_to_all_clients(chat_message, asServer=True)

    def server_chat_rcv_handler(self, sock: socket.socket):
        while True:
            try:
                chat_message_encoded = recv_message(sock)
                if chat_message_encoded == b"Chat<DELIMITER>Sair":
                    self.chat_clients.remove(sock)
                    break
                if not chat_message_encoded:
                    break
                chat_message = chat_message_encoded.decode("utf-8")
                peer_name = sock.getpeername()
                chat_message_to_send = (
                    f"({peer_name[0]}:{peer_name[1]}): {chat_message}"
                )
                print(chat_message_to_send)
                to_send_message = f"Chat<DELIMITER>{chat_message_to_send}"
                self.send_to_all_clients(to_send_message, current_socket=sock)
            except Exception as error:
                print(f"Error in handle_chat: {error}")
                break

    def send_to_all_clients(self, message: str, asServer=False, current_socket=None):
        if message == "":
            return
        for client in self.chat_clients:
            if client != current_socket:
                try:
                    message_to_send = (
                        f"{'Chat<DELIMITER>SERVER: ' if asServer else ''}{message}"
                    )
                    send_message(client, message_to_send.encode("utf-8"))
                except:
                    client.close()
                    self.chat_clients.remove(client)


if __name__ == "__main__":
    HOST, PORT = "127.0.0.1", 3300
    tcp_server = TCP_Server(HOST, PORT)
