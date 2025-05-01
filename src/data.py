import os
import hashlib

RGIT_DIR = ".rgit"
OBJECTS_DIR = f"{RGIT_DIR}/objects"

def init():
    os.makedirs(RGIT_DIR)
    os.makedirs(OBJECTS_DIR)


# get file content, hash it, then put the content in .rgit/objects/<hash>
def hash_object(file_content: str):

    hasher = hashlib.sha1(file_content) # create hasher + put message to hash
    object_id = hasher.hexdigest() # hash

    target_path = f"{OBJECTS_DIR}/{object_id}"
    with open(target_path, "wb") as file:
        file.write(file_content)

    return object_id


def get_object_content(oid: str) -> str:
    # read in binary mode
    with open(f"{OBJECTS_DIR}/{oid}", 'rb') as file:
        return file.read()
