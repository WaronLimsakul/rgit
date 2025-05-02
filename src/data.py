import os
import hashlib
import sys
import shutil

RGIT_DIR = ".rgit"
OBJECTS_DIR = f"{RGIT_DIR}/objects"
HEAD_FILE = f"{RGIT_DIR}/HEAD"

def init():
    os.makedirs(RGIT_DIR)
    os.makedirs(OBJECTS_DIR)

def clear():
    shutil.rmtree(RGIT_DIR)

# get file content, hash it with object type, then put the content in .rgit/objects/<hash>
def hash_object(file_content: bytes, type_: str ="blob") -> str:

    # prepend the type to the content
    file_content = type_.encode() + b"\0" + file_content
    hasher = hashlib.sha1(file_content) # create hasher + put message to hash
    object_id = hasher.hexdigest() # hash

    target_path = f"{OBJECTS_DIR}/{object_id}"
    with open(target_path, "wb") as file:
        # prepend the object type
        file.write(file_content)

    return object_id


# get the oid and expected type, return if found + has expected type
def get_object_content(oid: str, expected: str | None = "blob") -> bytes:
    # read in binary mode
    with open(f"{OBJECTS_DIR}/{oid}", 'rb') as file:

        # get the type first
        # this function divide bytes into 3 parts, before - first_sep - after
        type_, _, content = file.read().partition(b"\0")
        type_str = type_.decode()
        if expected is not None:
            assert type_str == expected, f"Expected {expected} type, found {type_str}"
        return content

def set_head(oid :str) -> None:
    with open(HEAD_FILE, "wb") as headfile:
        headfile.write(oid.encode())


def get_head_hash() -> str:
    if not os.path.isfile(HEAD_FILE):
        return ""
    with open(HEAD_FILE, "r") as headfile:
        return headfile.read().strip() #strip trailing and leading space?
