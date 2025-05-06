import os
import hashlib
import sys
import shutil
import json
from typing import Iterator, Tuple, Set, Generator, Dict
from collections import namedtuple
from contextlib import contextmanager

RGIT_DIR = "" # will be set in cli.main()
SYMREF_PREFIX = "ref: "

# a quick way to write a class with only attributes
RefValue = namedtuple("RefValue", ["symbolic", "value"])


@contextmanager # only ONE function below this line is wrapped
# Get the path that rgit dir is, then switch to that path/.rgit temporarily
# (for remote-related task)
def switch_rgit_dir(path: str) -> Iterator[None]:
    global RGIT_DIR
    old_dir = RGIT_DIR
    RGIT_DIR = os.path.join(path, ".rgit")
    try:
        yield
    finally:
        RGIT_DIR = old_dir


def init():
    os.makedirs(RGIT_DIR)
    os.makedirs(os.path.join(RGIT_DIR, "objects"))


def clear():
    shutil.rmtree(RGIT_DIR)


# get file content, hash it with object type, then put the content in .rgit/objects/<hash>
def hash_object(file_content: bytes, type_: str ="blob") -> str:
    # prepend the type to the content
    file_content = type_.encode() + b"\0" + file_content
    hasher = hashlib.sha1(file_content) # create hasher + put message to hash
    object_id = hasher.hexdigest() # hash

    target_path = f"{RGIT_DIR}/objects/{object_id}"
    with open(target_path, "wb") as file:
        # prepend the object type
        file.write(file_content)

    return object_id


# get the oid and expected type, return if found + has expected type
def get_object_content(oid: str, expected: str | None = "blob") -> bytes:
    # read in binary mode
    with open(f"{RGIT_DIR}/objects/{oid}", 'rb') as file:

        # get the type first
        # this function divide bytes into 3 parts, before - first_sep - after
        type_, _, content = file.read().partition(b"\0")
        type_str = type_.decode()
        if expected is not None:
            assert type_str == expected, f"Expected {expected} type, found {type_str}"
        return content


# get ref name and trace it back until the non-symbolic ref. Return that ref and the value
# use deref = False if just want to get value of exact ref
def _get_ref_internal(ref: str, deref: bool = True) -> Tuple[str, RefValue | None]:
    target_path = os.path.join(RGIT_DIR, ref)
    if not os.path.isfile(target_path): # return zero value if file doesn't exist
        return (ref, None)

    with open(target_path, "r") as reffile:
        ref_content = reffile.read().strip()

    # content has 2 cases here: the content is hash / another ref (ref: <ref-name>)
    symbolic = ref_content.startswith(SYMREF_PREFIX)

    if symbolic: # update to cut prefix if possible
        ref_content = ref_content.removeprefix(SYMREF_PREFIX)

    # if deref + symbolic => trace back
    if symbolic and deref:
        return _get_ref_internal(ref=ref_content, deref=True)

    # if not deref or not symbolic (have oid) => return right away
    return (ref, RefValue(symbolic=symbolic, value=ref_content))


# takes ref address and value, (optional deref) then update
def update_ref(ref: str, ref_value: RefValue, deref: bool = True) -> None:
    ref, _ = _get_ref_internal(ref, deref) # reset the ref to where we will update
    # don't have to check the second value, because sometimes we want to create

    target_path = os.path.join(RGIT_DIR, ref)
    os.makedirs(os.path.dirname(target_path), exist_ok=True)

    if ref_value.symbolic: # prepare before writing
        updated_value = SYMREF_PREFIX + ref_value.value
    else:
        updated_value = ref_value.value

    with open(target_path, "w") as reffile:
        reffile.write(updated_value)


# get the ref name find the value of the ref in .rgit/
def get_ref_value(ref: str, deref: bool = True) -> RefValue | None:
    _, value = _get_ref_internal(ref, deref=deref)
    return value


# iterate every refs inside .rgit/ and return (full_ref, ref_value)
# choose deref = False to get value of symbolic ref
# choose prefix = something to only iterate in .rgit/refs/something
def iter_refs(deref: bool = True, prefix: str = "") -> Iterator[Tuple[str, RefValue]]:
    refs = ["HEAD", "MERGE_HEAD"] if not prefix else []

    start_path = os.path.join(RGIT_DIR, "refs", prefix)
    for root, _, filenames in os.walk(start_path):
        # root form os.walk is absolute, but all our functionality need relative
        root = os.path.relpath(root, RGIT_DIR)
        for filename in filenames:
            refs.append(os.path.join(root, filename))

    for ref in refs:
        ref_hash = get_ref_value(ref, deref=deref)
        if not ref_hash: continue
        yield (ref, ref_hash)


# for deleting MERGE_HEAD ref when merge
def delete_ref(ref: str) -> None:
    target_path = os.path.join(RGIT_DIR, ref)
    try:
        os.remove(target_path)
    except OSError as error:
        # if the file already doesn't exist, it should be fine
        pass


def object_exists(oid: str) -> bool:
    target_path = os.path.join(RGIT_DIR, "objects", oid)
    return os.path.isfile(target_path)

def fetch_object_if_missing(remote_path: str, oid: str) -> None:
    if object_exists(oid):
        return

    shutil.copy(
        os.path.join(remote_path, ".rgit", "objects", oid),
        os.path.join(RGIT_DIR, "objects", oid)
    )


def push_object(remote_path: str, oid: str) -> None:
    assert object_exists(oid), f"can't find oid {oid}"
    shutil.copy(
        os.path.join(RGIT_DIR, "objects", oid),
        os.path.join(remote_path, ".rgit", "objects", oid)
    )


# yield index file as a dict, let the caller deal with it
# and then dump it back to save.
@contextmanager
def get_index() -> Iterator[Dict[str, str]]:
    index = {} # in case we don't have .rgit/index
    index_path = os.path.join(RGIT_DIR, "index")
    if os.path.isfile(index_path):
        with open(index_path, "r") as index_file:
            index = json.load(index_file) # load into a dict

    yield index

    with open(index_path, "w") as index_file:
        json.dump(index, index_file) # rewrite the file
