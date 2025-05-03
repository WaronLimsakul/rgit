import os
import hashlib
import sys
import shutil
from typing import Iterator, Tuple, Set
from collections import namedtuple

RGIT_DIR = ".rgit"
OBJECTS_DIR = f"{RGIT_DIR}/objects"
HEAD_FILE = f"{RGIT_DIR}/HEAD"

# a quick way to write a class with only attributes
RefValue = namedtuple("RefValue", ["symbolic", "value"])

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


def update_ref(ref: str, ref_value: RefValue) -> None:
    if ref_value.symbolic:
        raise ValueError("at update_ref: need normal ref, found symbolic")

    target_path = os.path.join(RGIT_DIR, ref)
    os.makedirs(os.path.dirname(target_path), exist_ok=True)

    with open(target_path, "w") as reffile:
        reffile.write(ref_value.value)


# get the ref name find the hash of the commit in .rgit/ref
def get_ref_hash(ref: str) -> RefValue | None:
    target_path = os.path.join(RGIT_DIR, ref)
    if not os.path.isfile(target_path):
        return None

    with open(target_path, "r") as reffile:
        ref_content = reffile.read().strip()

    # 2 cases here: the content is hash -> return / another ref (ref: <ref-name>) -> recur
    symref_prefix = "ref: "
    if ref_content.startswith(symref_prefix):
        return get_ref_hash(ref_content.removeprefix(symref_prefix))

    return RefValue(symbolic=False, value=ref_content)


def iter_refs() -> Iterator[Tuple[str, RefValue]]:
    refs = ["HEAD"]

    start_path = os.path.join(RGIT_DIR, "refs")
    for root, _, filenames in os.walk(start_path):
        # root form os.walk is absolute, but all our functionality need relative
        root = os.path.relpath(root, RGIT_DIR)
        for filename in filenames:
            refs.append(os.path.join(root, filename))

    for ref in refs:
        ref_hash = get_ref_hash(ref)
        if not ref_hash: continue

        yield (ref, ref_hash)
