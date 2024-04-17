import hashlib

def calculate_checksum(data: str | bytes) -> str: # len 64
    if type(data) == str:
        data = data.encode('utf-8')
    hash_object = hashlib.sha256()
    hash_object.update(data)
    checksum = hash_object.hexdigest()
    # print(f'data: {data}')
    # print(f'checksum calculated: {checksum}')
    return checksum

def format_part_no(num: int) -> str:
    return str(num).zfill(8)
    

def deformat_part_no(num: str) -> int:
    return int(num)