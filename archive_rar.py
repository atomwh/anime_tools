#!/usr/bin/env python3

from pathlib import Path
import subprocess
import os
import shutil
import logging
import re
import locale

ARCHIVE_LIST = "./archive.txt"
ARCHIVE_PATH = "./archive"
LOG_FILE = "./archive.log"
LIMIT_SIZE = 4 * 1024 * 1024 * 1024
COMPRESS_PASSWD = "ReplaceME"
SYSTEM_ENCODING = locale.getpreferredencoding()
DEFAULT_ENCODING = "utf-8"


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s: %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, "w", DEFAULT_ENCODING),
        logging.StreamHandler(),
    ],
)


def is_rar_available():
    """Check if rar is available."""
    return shutil.which("rar") is not None


def get_dir_size(start_path="."):
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
        "rar",
        "-ma5",
        "-rr5",
        "-m0",
        "-hp{}".format(password),
        "-ep1",
        "a",
        "-r",
        archive_name,
        path,
    ]
    if is_larger_than_4gb(path):
        command.insert(4, f"-v{LIMIT_SIZE}b")

    logging.info(f"Compressing {path} to {archive_name}")
    result = subprocess.run(command, capture_output=True)
    if result.returncode != 0:
        logging.error(f"Compression failed: {path}")
        try:
            stderr_output = result.stderr.decode(SYSTEM_ENCODING)
        except UnicodeDecodeError:
            stderr_output = result.stderr.decode(DEFAULT_ENCODING, errors="replace")
        # write stderr output to log file
        with open(LOG_FILE, "a", encoding=DEFAULT_ENCODING) as log_file:
            log_file.write(stderr_output)
    return result.returncode


def handle_compressing(src_path_str):
    ret = 0
    logging.info(f"Processing {src_path_str}")

    src_path = Path(src_path_str)
    if not src_path.exists():
        logging.error(f"Path does not exist: {str(src_path)}")
        return 1

    compressed_pattern = re.compile(r".*\.rar$|\.zip$|\.7z$", re.IGNORECASE)
    if src_path.is_file():
        if compressed_pattern.search(src_path.name):
            logging.warning(f"{src_path.name} is already compressed.")
            archive_path = Path(ARCHIVE_PATH) / f"{src_path.name}.rar"
        else:
            archive_path = Path(ARCHIVE_PATH) / src_path.with_suffix(".rar").name
        if compress_path(str(src_path), str(archive_name), COMPRESS_PASSWD) != 0:
            logging.error(f"Compression failed: {src_path}")
            return 2

    archive_prefix_path = Path(ARCHIVE_PATH) / src_path
    archive_prefix_path.mkdir(parents=True, exist_ok=True)

    for entry in src_path.iterdir():
        if entry.is_file():
            if compressed_pattern.search(entry.name):
                logging.warning(f"{entry.name} has already been compressed.")
                archive_path = archive_prefix_path / f"{entry.name}.rar"
            else:
                archive_path = archive_prefix_path / entry.with_suffix(".rar").name
                archive_part_path = archive_prefix_path / entry.with_suffix(".part1.rar").name
                """
                    sometime there are files have the same name without suffix,
                    for example: A.mka and A.mkv, or A.ass and A.mp4
                    we need to handle this by add original suffix back
                """
                if archive_path.exists() or archive_part_path.exists():
                    archive_path = archive_prefix_path / f"{entry.name}.rar"
        else:
            archive_path = archive_prefix_path / f"{entry.name}.rar"

        if compress_path(str(entry), str(archive_path), COMPRESS_PASSWD) != 0:
            ret = 3
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
        with open(ARCHIVE_LIST, "r", encoding=DEFAULT_ENCODING) as file:
            paths = file.read().splitlines()
    except FileNotFoundError:
        logging.error("The file archive.txt was not found.")
        return 2

    if os.path.exists(ARCHIVE_PATH) and os.path.isfile(ARCHIVE_PATH):
        logging.error(
            "Result path {ARCHIVE_PATH} is a file. Please rename the file or change the ARCHIVE_PATH"
        )
        return 3
    if not os.path.exists(ARCHIVE_PATH):
        os.makedirs(ARCHIVE_PATH)

    current_path = os.getcwd()
    for target_path in paths:
        if handle_compressing(target_path) != 0:
            ret = 3
            break

    if ret == 0:
        logging.info("All files processed successfully.")
    else:
        logging.error("Some files failed to compress. lease check the log file.")
    return ret


if __name__ == "__main__":
    exit(main())
