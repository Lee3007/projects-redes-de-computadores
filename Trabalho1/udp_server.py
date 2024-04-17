import math
import sys
import socket
from loguru import logger  
from utils import calculate_checksum, format_part_no, deformat_part_no
import random

class UDP_Server:
    def __init__(self, ip='127.0.0.1', port=4567, buffer_size=1024) -> None:
        self.ip = ip
        logger.info(f'Using {self.ip}')
        self.port = port
        self.buffer_size = buffer_size
        self.checksum_size = 64
        self.packet_no_size = 8
        self.separators_size = 2
        # Calculated supposing the worst case scenario: tranfering files
        self.content_size = buffer_size - (self.checksum_size + self.packet_no_size + self.separators_size)
        self.UDP_Server_Socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self.UDP_Server_Socket.bind((self.ip, self.port))
        self.UDP_Server_Socket.settimeout(2.0)
        self.should_corrupt = False
        should_corrupt_input = input("Should some packets be corrupted? (y/n) ")
        if should_corrupt_input == 'y':
            self.should_corrupt = True
        logger.success(f"UDP server started on {self.ip}:{self.port}")
        self.start()

    def start(self):
        while True:
            try:
                message, address = self.UDP_Server_Socket.recvfrom(self.buffer_size)
                logger.info(f'Received the following from {address}:{message}')
                decoded_message = message.decode('utf-8')
                req_args = decoded_message.split(':')
                if req_args[0] == 'FETCH':
                    self.handle_fetch_request(address, req_args)
                elif req_args[0] == 'CFETCH':
                    self.handle_continue_fetch_request(address, req_args)
            except socket.timeout:
                continue  
            except KeyboardInterrupt:
                break 
    
    # Fetch file: FETCH:filename
    def handle_fetch_request(self, address, req_args: list[str]):
        file_name = req_args[1]
        logger.info(f'Identified a FETCH request to {file_name}')
        try:
            with open(f'server_data/{file_name}', 'rb') as file:
                file_bytes = file.read()
                max_parts_no = math.ceil(len(file_bytes)/self.content_size)
                response_message = f'FOUND:100:parts:{format_part_no(max_parts_no)}'
                response = response_message
        except FileNotFoundError:
            logger.error("Error:FileNotFoundError")
            response = f'ERROR:701:File {file_name} was not found.'
        except Exception as error:
            logger.error(f'Error in CFETCH (address:{address}) (req_args:{req_args}): {error}')
            response = f'ERROR:702:Unknown error.'
        finally:
            self.respond(address, response)    

    # Continue fetching file: CFETCH:filename:part
    def handle_continue_fetch_request(self, address, req_args: list[str]):
        file_name = req_args[1]
        file_part_no = int(req_args[2])
        logger.info(f'Identified a CFETCH request to {file_name}, part:{file_part_no}')
        try:
            with open(f'server_data/{file_name}', 'rb') as file:
                file_bytes = file.read()
                max_parts_no = math.ceil(len(file_bytes)/self.content_size)
                if file_part_no > max_parts_no:
                    response = f'ERROR:700:File part number exceeded maximum.'
                else:
                    start_index = self.content_size * (file_part_no - 1)
                    end_index = start_index + self.content_size
                    response_content = file_bytes[start_index:end_index]
                    response = response_content + f':{format_part_no(file_part_no)}'.encode('utf-8')
        except FileNotFoundError:
            logger.error("Error:FileNotFoundError")
            response = f'ERROR:701:File {file_name} was not found.'
        except Exception as error:
            logger.error(f'Error in CFETCH (address:{address}) (req_args:{req_args}): {error}')
            response = f'ERROR:702:Unknown error.'
        finally:
            self.respond(address, response)
    
    def respond(self, address, message: str | bytes) -> None:
        logger.info(f'Responding to {address}')
        checksum = calculate_checksum(message)
        if type(message) == str:
            message = message.encode('utf-8')
        response = message + f':{checksum}'.encode('utf-8')
        if self.should_corrupt:
            num_of_random_changes = random.randint(0 ,100)
            if num_of_random_changes < 3:
                response = self.modify_bytes(response, num_of_random_changes)
        self.UDP_Server_Socket.sendto(response, address)
        
    def modify_bytes(self, data: bytes, num_changes: int) -> bytes:
        print(f'Modifying {num_changes} bytes')
        modified_data = bytearray(data)
        indices_to_change = random.sample(range(len(modified_data)), num_changes)
        for index in indices_to_change:
            modified_data[index] = random.randint(0, 255)
        print(f'are they the same? {bytes(modified_data) == data}')
        return bytes(modified_data)
        


if __name__ == "__main__":
    if len(sys.argv) > 1: 
        server = UDP_Server(ip=sys.argv[1])
    else:
        server = UDP_Server()