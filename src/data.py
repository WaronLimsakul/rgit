import os
import hashlib
import sys
import shutil
from typing import Iterator, Tuple, Set
from collections import namedtuple

RGIT_DIR = ".rgit"
OBJECTS_DIR = f"{RGIT_DIR}/objects"
HEAD_FILE = f"{RGIT_DIR}/HEAD"
SYMREF_PREFIX = "ref: "

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


# iterate every refs inside .rgit/
# choose deref = False to get value of symbolic ref
def iter_refs(deref: bool = True) -> Iterator[Tuple[str, RefValue]]:
    refs = ["HEAD"]

    start_path = os.path.join(RGIT_DIR, "refs")
    for root, _, filenames in os.walk(start_path):
        # root form os.walk is absolute, but all our functionality need relative
        root = os.path.relpath(root, RGIT_DIR)
        for filename in filenames:
            refs.append(os.path.join(root, filename))

    for ref in refs:
        ref_hash = get_ref_value(ref, deref=deref)
        if not ref_hash: continue
        yield (ref, ref_hash)
