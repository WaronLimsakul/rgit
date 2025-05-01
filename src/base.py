# base module provide higher level implementation of data.py
import os
# from . import data

def write_tree(dir_path: str = "."):
    # listdir will just give list of file name in dir
    # scandir will give list of file-like object I can directly call method on
    # but I have to close the list. so I will use with ... as ... to auto close
    with os.scandir(dir_path) as ls:
        for file in ls:
            full_path = f"{dir_path}/{file.name}"
            if file.is_file():
                print(full_path)
            elif file.is_dir():
                write_tree(full_path)
