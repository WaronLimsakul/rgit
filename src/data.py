import os
import hashlib

RGIT_DIR = ".rgit"

def init():
    os.makedirs(RGIT_DIR)
    os.makedirs(f"{RGIT_DIR}/objects")

def hash_object(file_content: str):

    hasher = hashlib.sha1(file_content) # create hasher + put message to hash
    object_id = hasher.hexdigest() # hash

    target_path = f"{RGIT_DIR}/objects/{object_id}"
    with open(target_path, "wb") as file:
        file.write(file_content)

    return object_id
