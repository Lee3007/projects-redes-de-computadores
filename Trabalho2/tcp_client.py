import socket
import sys
import threading

from typing import Dict
from utils import calculate_sha256, recv_message, send_message
import os


class TCP_Client:
    def __init__(self, host, port, id=0):
        self.client_id = id
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))
        self.running = True
        self.open_files: Dict[str, socket.socket] = {}
        self.client_folder = f"./client{self.client_id}_files"
        os.makedirs(self.client_folder, exist_ok=True)
        self._run()

    def _receive_messages_handler(self):
        while self.running:
            try:
                response = recv_message(self.sock)

                split_message = response.split(b"<DELIMITER>")

                if split_message[0] == b"Arquivo":
                    if split_message[1] == b"NON_EXISTENT_FILE":
                        print("ERROR: File does not exist in the server.")
                    elif split_message[1] == b"SUCCESS":
                        file_name = split_message[2].decode("utf-8")
                        if split_message[3] == b"START":
                            if os.path.isfile(f"{self.client_folder}/{file_name}"):
                                os.remove(f"{self.client_folder}/{file_name}")
                        elif split_message[3] == b"DATA":
                            file_data = split_message[4]
                            if file_name not in self.open_files:
                                self.open_files[file_name] = open(
                                    f"{self.client_folder}/{file_name}", "ab+"
                                )
                            self.open_files[file_name].write(file_data)
                        elif split_message[3] == b"HASH":
                            self.open_files[file_name].flush()
                            remote_file_hash = split_message[4].decode("utf-8")
                            local_file_hash = calculate_sha256(
                                f"{self.client_folder}/{file_name}"
                            )
                            if remote_file_hash != local_file_hash:
                                print(
                                    "ERROR: File hash does not match. Trying again..."
                                )
                                os.remove(f"{self.client_folder}/{file_name}")
                                del self.open_files[file_name]
                                message_to_retry = (
                                    f"Arquivo<DELIMITER>{file_name}".encode("utf-8")
                                )
                                send_message(self.sock, message_to_retry)
                            else:
                                self.open_files[file_name].close()
                                del self.open_files[file_name]
                                print(f"File {file_name} successfully downloaded!")

                elif split_message[0] == b"Chat":
                    print(f"{split_message[1].decode('utf-8')}")

            except ConnectionAbortedError:
                print(f"Connection terminated.")
                break
        self.stop()

    def _send_messages_handler(self):
        while self.running:
            message = input()
            if message == "Sair":
                break
            message = message.replace("|", "<DELIMITER>")
            send_message(self.sock, message.encode("utf-8"))
        self.stop()

    def _run(self):
        receive_messages_thread = threading.Thread(
            target=self._receive_messages_handler
        )
        send_messages_thread = threading.Thread(target=self._send_messages_handler)

        receive_messages_thread.start()
        send_messages_thread.start()
        self.running = True

    def stop(self):
        self.running = False
        self.sock.close()
        print("Client stopped.")


if __name__ == "__main__":
    id = sys.argv[1]
    # HOST, PORT = "127.0.0.1", 3300
    HOST, PORT = "192.168.18.19", 3300
    client = TCP_Client(HOST, PORT, id)
