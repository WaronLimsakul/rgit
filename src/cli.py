# lib for parsing cl argument into object that I can pick attribute from
import argparse
import os
from . import data # if I want to import local lib, I have specify where it is

def main():
    args = parse_args()
    args.func(args)

def parse_args():
    parser = argparse.ArgumentParser() # parser object

    # We will add sub-parser for handling sub-command
    commands = parser.add_subparsers(dest="command")
    commands.required = True # force user to have command

    # this function take the command string, then return the parser we can modify
    init_parser = commands.add_parser("init") # this one is init parser
    init_parser.set_defaults(func=init) # just set the attribute name "func" to the init function

    hash_object_parser = commands.add_parser("hash-object")
    hash_object_parser.add_argument("file_path")
    hash_object_parser.set_defaults(func=has_object)

    return parser.parse_args()

def init(args):
    data.init()
    print(f"initialize rgit repo in {os.getcwd()}/{data.RGIT_DIR}")

def hash_object(args):
    with open(file_path, "rb") as file:
        file_content = file.read()

    oid = data.hash_object(file_content)
    printf(f"hash object {args.file_path} -> {oid}")
