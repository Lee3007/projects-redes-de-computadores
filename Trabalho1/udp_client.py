import math
import socket
import sys
import time
from loguru import logger  
from utils import calculate_checksum, format_part_no, deformat_part_no
from tqdm import tqdm

class ChecksumFailedException(Exception):
    pass

class UDP_Client:
    def __init__(self, ip='127.0.0.1', port=4567, buffer_size=1024) -> None:
        self.ip = ip
        logger.info(f'Using {self.ip}')
        self.port = port
        self.buffer_size = buffer_size
        self.content_size = buffer_size - (64 + 8 + 2) # checksum_size = 64 bytes + packet_num = 8 bytes + 2x 1 byte ':'
        self.UDP_Client_Socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self.UDP_Client_Socket.settimeout(2.0)
        logger.success(f"UDP client started on {self.ip}:{self.port}")
        self.start()
        
    def start(self):
        while True:
            file_name = input("Enter a filename (or 'q' to exit): ")
            if file_name.lower() == 'q':
                break
            while True:
                try:
                    self.fetch(file_name)
                    break
                except FileNotFoundError:
                    break
                except socket.timeout:
                    break  
                except KeyboardInterrupt:
                    return
                except ChecksumFailedException:
                    continue
                except Exception:
                    continue
        
    def fetch(self, file_name: str):
        logger.info(f'Sending FETCH:{file_name}')
        encodedRequestMessage = f'FETCH:{file_name}'.encode('utf-8')
        self.UDP_Client_Socket.sendto(encodedRequestMessage, (self.ip, self.port))
        
        try:
            res_args, _ = self.receive_response()
        except ChecksumFailedException:
            logger.error('Checksum failed! Retry...')
            raise ChecksumFailedException
        except Exception as error:
            logger.error(f'error in fetch() {error}')
            raise Exception(error)
        
        if res_args[0] == 'ERROR':
            logger.error(f'Error code: {res_args[1]}')
            logger.error(f'Error message: {res_args[2]}')
            if res_args[1] == '701':
                raise FileNotFoundError()
            return
        elif res_args[0] == 'FOUND':
            with open(f'client_data/{file_name}', 'wb') as file:
                file.write(''.encode('utf-8'))
            number_of_parts = int(res_args[3])
            i = 0
            with tqdm(total=number_of_parts, desc="Downloading") as pbar:
                while i < number_of_parts:
                    try:
                        self.cfetch(file_name, i+1)
                        i += 1
                        pbar.update(1) 
                    except ChecksumFailedException:
                        logger.error(f'Corrupted Information, trying again for part {i+1}')
                    except TimeoutError:
                        logger.error(f'Timeout: Server took too long to answer, trying again for part {i+1}')
                    except Exception as error:
                        logger.error(f'Error in cfetch: {error}')
                        error_args = error.args[0].split(':')
                        if error_args[0] == 'code':
                            if error_args[1] == '701' or error_args[1] == '702':
                                return
                            elif error_args[1] == '700':
                                logger.error('Requesting more parts than existing')
                                return
                        elif error_args[0] == 'need':
                            part_needed = int(error_args[1])
                            i = part_needed - 1
            logger.success(f'Finished bringing file {file_name}')
        else:
            logger.error('Not implemented')
            logger.error(f'res_args: {res_args}')
            return
                
    def cfetch(self, file_name: str, part_no: int):
        # logger.info(f'Sending CFETCH:{file_name}:{part_no}')
        encodedRequestMessage = f'CFETCH:{file_name}:{part_no}'.encode('utf-8')
        self.UDP_Client_Socket.sendto(encodedRequestMessage, (self.ip, self.port))
        res_args, file_content = self.receive_response(has_file=True)
        if res_args[0] == 'ERROR':
            logger.error(f'Error code: {res_args[1]}')
            logger.error(f'Error message: {res_args[2]}')
            raise Exception(f'code:{res_args[1]}')
        else:
            existing_parts = 0
            with open(f'client_data/{file_name}', 'rb') as file:
                file_bytes = file.read()
                existing_parts = math.ceil(len(file_bytes)/self.content_size)
                part_no_received = deformat_part_no(res_args[0])
                if part_no_received != existing_parts + 1:
                    logger.error('part_no_received != existing_parts + 1')
                    logger.error(f'{part_no_received}')
                    logger.error(f'{existing_parts} + 1')
                    raise Exception(f'need:{existing_parts + 1}')
            with open(f'client_data/{file_name}', 'ab') as file:
                file.write(file_content)
        
    def receive_response(self, has_file=False):
        response, server_address = self.UDP_Client_Socket.recvfrom(self.buffer_size)
        # logger.info(f'Received response from {server_address}')
        checksum = response[-64:]
        checksum_content = response[:-65]
        if has_file:    # file_content + : + 8bytes + : + checksum
            args_content = response[-73:]
            res_args = args_content.decode('utf-8').split(':')
            file_content = response[:-74]   
        else:
            res_args = response.decode('utf-8').split(':')
            file_content = 'None'
        verified = self.verify_checksum(checksum, checksum_content)
        if not verified:
            raise ChecksumFailedException('checksum_failed')
        return res_args, file_content
        
    def verify_checksum(self, received_checksum: str | bytes, message: bytes) -> bool:
        if type(received_checksum) == bytes:
            received_checksum = received_checksum.decode('utf-8')
        calculated_checksum = calculate_checksum(message)
        return calculated_checksum == received_checksum
    
if __name__ == "__main__":
    if len(sys.argv) > 1: 
        server = UDP_Client(ip=sys.argv[1])
    else:
        server = UDP_Client()