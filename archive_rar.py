#!/usr/bin/env python3

import subprocess
import os
import shutil
import logging
import re

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s: %(levelname)s: %(message)s',
                    handlers=[logging.FileHandler('archive.log', 'w', 'utf-8'), logging.StreamHandler()])

ARCHIVE_LIST = './archive.txt'
ARCHIVE_PATH = './archive'
LIMIT_SIZE = 4 * 1024 * 1024 * 1024
COMPRESS_PASSWD = 'ReplaceME'

def is_rar_available():
    """Check if 7z is available."""
    return shutil.which('rar') is not None

def get_dir_size(start_path = '.'):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            # skip if it is symbolic link
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)

    return total_size

def is_larger_than_4gb(path):
    """Check if the size of the given file or directory is larger than 4 GB."""
    if os.path.isfile(path):
        # If it's a file, just get its size
        return os.path.getsize(path) > LIMIT_SIZE
    elif os.path.isdir(path):
        # If it's a directory, sum the sizes of all files
        return get_dir_size(path) > LIMIT_SIZE
    else:
        print(f"{path} is neither a file nor a directory.")
        return False

def compress_path(path, archive_name, password):
    """Compress the given directory with rar using multi-threading."""
    command = [
        'rar', '-ma5', '-rr5', '-m0', '-hp{}'.format(password),
        '-ep1', 'a', '-r', archive_name, path
    ]
    if is_larger_than_4gb(path):
        command.insert(4, f'-v{LIMIT_SIZE}')

    logging.info(f"Compressing {path} to {archive_name}")
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        logging.error(f"Compression failed: {path}")
    return result.returncode

def handle_compressing(src_path):
    ret = 0
    logging.info(f"Processing {src_path}")

    if not os.path.exists(src_path):
        logging.error(f"File does not exist: {src_path}")
        return 1

    compressed_pattern = re.compile(r'.*\.rar$|\.zip$|\.7z$', re.IGNORECASE)
    if os.path.isfile(src_path):
        if compressed_pattern.search(src_path):
            archive_name = f"{ARCHIVE_PATH}/{src_path}.rar"
        else:
            archive_name = "%s/%s.%s" %(ARCHIVE_PATH, '.'.join(src_path.split('.')[:-1]), 'rar')
        if compress_path(src_path, archive_name, COMPRESS_PASSWD) != 0:
            logging.error(f"Compression failed: {src_path}")
            return 2

    if not os.path.exists(f"{ARCHIVE_PATH}/{src_path}"):
        os.makedirs(f"{ARCHIVE_PATH}/{src_path}")
    archive_prefix = f"{ARCHIVE_PATH}/{src_path}"
    for item in os.listdir(src_path):
        if os.path.isfile(f"{src_path}/{item}"):
            if compressed_pattern.search(item):
                logging.warning(f"{item} is already compressed.")
                archive_name = "%s/%s.%s" %(archive_prefix, item, 'rar')
            else:
                archive_name = "%s/%s.%s" %(archive_prefix, '.'.join(item.split('.')[:-1]), 'rar')
        else:
            archive_name = "%s/%s.%s" %(archive_prefix, item, 'rar')

        if compress_path(f"{src_path}/{item}", archive_name, COMPRESS_PASSWD) != 0:
            ret = 1
            break

    return ret

def main():
    ret = 0
    """Main function to process the paths listed in ARCHIVE_LIST."""
    logging.info("Starting the archiving process.")

    if not is_rar_available():
        logging.error("rar is not available. Please install it and add to your PATH.")
        return 1

    try:
        with open(ARCHIVE_LIST, 'r', encoding='UTF-8') as file:
            paths = file.read().splitlines()
    except FileNotFoundError:
        logging.error("The file archive.txt was not found.")
        return 2

    if os.path.exists(ARCHIVE_PATH) and os.path.isfile(ARCHIVE_PATH):
        logging.error("Result path {ARCHIVE_PATH} is a file. Please rename the file or change the ARCHIVE_PATH")
        return 3
    if not os.path.exists(ARCHIVE_PATH):
        os.makedirs(ARCHIVE_PATH)

    current_path = os.getcwd()
    for target_path in paths:
        if handle_compressing(target_path) != 0:
            ret = 3
            break

    logging.info("All files processed up to the point of failure or completion.")
    return ret

if __name__ == "__main__":
    exit(main())
