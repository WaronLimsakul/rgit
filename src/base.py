# base module provide higher level implementation of data.py
import os
from . import data

def write_tree(dir_path: str = ".") -> None:
    # listdir will just give list of file name in dir
    # scandir will give list of file-like object I can directly call method on
    # but I have to close the list. so I will use with ... as ... to auto close
    with os.scandir(dir_path) as ls:
        for file in ls:
            full_path = f"{dir_path}/{file.name}"
            if is_ignored(full_path):
                continue
            elif file.is_file():
                with open(full_path, 'rb') as f:
                    oid = data.hash_object(f.read())
                print(f"obj: {full_path}, oid: {oid}")
            elif file.is_dir():
                write_tree(full_path)


# now we will only ignore the .rgit (and .git since it's annoying) dir
def is_ignored(path: str) -> bool:
    return ".rgit" in path.split("/") or ".git" in path.split("/")
