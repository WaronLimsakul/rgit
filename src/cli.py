# lib for parsing cl argument into object that I can pick attribute from
import argparse
import os
import sys
import textwrap # lib for wrapping multi-line string
from typing import Dict
from src import data # if I want to import local lib, I have specify where it is
from src import base

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

    # for only development
    clear_parser = commands.add_parser("clear")
    clear_parser.set_defaults(func=clear)

    hash_object_parser = commands.add_parser("hash-object")
    hash_object_parser.add_argument("file_path")
    hash_object_parser.set_defaults(func=hash_object)

    cat_file_parser = commands.add_parser("cat-file")
    cat_file_parser.add_argument("oid")
    cat_file_parser.set_defaults(func=cat_file)

    write_tree_parser = commands.add_parser("write-tree")
    write_tree_parser.set_defaults(func=write_tree)

    read_tree_parser = commands.add_parser("read-tree")
    read_tree_parser.add_argument("oid")
    read_tree_parser.set_defaults(func=read_tree)

    commit_parser = commands.add_parser("commit")
    commit_parser.add_argument("--message", "-m", required=True)
    commit_parser.set_defaults(func=commit)

    log_parser = commands.add_parser("log")
    # takes one value to be oid, if not, just use default
    log_parser.add_argument("oid", nargs="?", default="HEAD")
    log_parser.set_defaults(func=log)

    checkout_parser = commands.add_parser("checkout")
    checkout_parser.add_argument("commit")
    checkout_parser.set_defaults(func=checkout)

    tag_parser = commands.add_parser("tag")
    tag_parser.add_argument("tag_name")
    # nargs="?" means optional argument, if not provided: just None
    tag_parser.add_argument("commit", nargs="?")
    tag_parser.set_defaults(func=tag)

    return parser.parse_args()

def init(args):
    data.init()
    print(f"initialize rgit repo in {os.getcwd()}/{data.RGIT_DIR}")

def clear(args):
    data.clear()
    print("clear .rgit directory")

def hash_object(args):
    with open(args.file_path, "rb") as file:
        file_content = file.read()

    oid = data.hash_object(file_content)
    print(f"hash object {args.file_path} -> {oid}")

def cat_file(args):
    # get file content in binary
    file_content = data.get_object_content(args.oid, expected=None)

    # flush() tell system to send everything in buffer to stdout
    # (basically, empty the buffer)
    sys.stdout.flush()
    # so we use stdout to write binary because it is designed to do so
    # (while print(f"") will print b"content"\n)
    sys.stdout.buffer.write(file_content)

def write_tree(args):
    tree_oid = base.write_tree()
    print(tree_oid)

def read_tree(args):
    base.read_tree(args.oid)

def commit(args):
    version_oid = base.commit(args.message)
    print(f"commit {version_oid}")

def _print_commit_data(commit_oid, commit: base.Commit) -> None:
    print(f"commit {commit_oid}\n")

    # .indent(<string>, prefix) will add prefix to everyline in the <string>
    print(textwrap.indent(commit.message, "    "))
    print()


def log(args):
    if args.oid != "HEAD":
        commit_oid = args.oid
    else:
        commit_oid = data.get_ref_hash("HEAD")

    while commit_oid:
        commit = base.get_commit(commit_oid)
        _print_commit_data(commit_oid, commit)
        commit_oid = commit.parent


def checkout(args):
    base.checkout(args.commit)
    print(f"checkout commit, now HEAD is {args.commit}")

def tag(args):
    # this means takes args.commit if available, else, takes head
    commit_oid = args.commit or data.get_ref_hash("HEAD")
    base.create_tag(args.tag_name, commit_oid)
