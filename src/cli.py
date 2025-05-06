# lib for parsing cl argument into object that I can pick attribute from
import argparse
import os
import sys
import textwrap # lib for wrapping multi-line string
import subprocess # lib for openning other processes
from collections import defaultdict
from typing import Dict
from src import data, base, diff, remote # if I want to import local lib, I have specify where it is

def main():
    with data.switch_rgit_dir("."):
        args = parse_args()
        args.func(args)

def parse_args():
    parser = argparse.ArgumentParser() # parser object
    oid = base.get_oid # a caster function they count as a type

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
    cat_file_parser.add_argument("oid", type=oid)
    cat_file_parser.set_defaults(func=cat_file)

    write_tree_parser = commands.add_parser("write-tree")
    write_tree_parser.set_defaults(func=write_tree)

    read_tree_parser = commands.add_parser("read-tree")
    read_tree_parser.add_argument("oid", type=oid)
    read_tree_parser.set_defaults(func=read_tree)

    commit_parser = commands.add_parser("commit")
    commit_parser.add_argument("--message", "-m", required=True)
    commit_parser.set_defaults(func=commit)

    log_parser = commands.add_parser("log")
    # takes one value to be oid, if not, just use default
    log_parser.add_argument("oid", type=oid, nargs="?", default="@")
    log_parser.set_defaults(func=log)

    checkout_parser = commands.add_parser("checkout")
    checkout_parser.add_argument("commit")
    checkout_parser.set_defaults(func=checkout)

    tag_parser = commands.add_parser("tag")
    tag_parser.add_argument("tag_name")
    # nargs="?" means optional argument, if not provided: just None
    tag_parser.add_argument("commit", nargs="?", type=oid, default="@")
    tag_parser.set_defaults(func=tag)

    k_parser = commands.add_parser("k")
    k_parser.set_defaults(func=k)

    branch_parser = commands.add_parser("branch")
    branch_parser.add_argument("branch_name", nargs="?")
    branch_parser.add_argument("start_point", default="@", nargs="?", type=oid)
    branch_parser.set_defaults(func=branch)

    status_parser = commands.add_parser("status")
    status_parser.set_defaults(func=status)

    reset_parser = commands.add_parser("reset")
    reset_parser.add_argument("commit", type=oid)
    reset_parser.add_argument("--hard", action="store_true") # set default to not reset hard
    reset_parser.set_defaults(func=reset)

    show_parser = commands.add_parser("show")
    show_parser.add_argument("commit", default="@", nargs="?", type=oid)
    show_parser.set_defaults(func=show)

    diff_parser = commands.add_parser("diff")
    diff_parser.add_argument("commit", default="@", nargs="?", type=oid)
    diff_parser.set_defaults(func=show_diff)

    merge_parser = commands.add_parser("merge")
    merge_parser.add_argument("commit", type=oid)
    merge_parser.set_defaults(func=merge)

    merge_base_parser = commands.add_parser("merge-base")
    merge_base_parser.add_argument("commit_oid_a", type=oid)
    merge_base_parser.add_argument("commit_oid_b", type=oid)
    merge_base_parser.set_defaults(func=merge_base)

    fetch_parser = commands.add_parser("fetch")
    fetch_parser.add_argument("path")
    fetch_parser.set_defaults(func=fetch)

    push_parser = commands.add_parser("push")
    push_parser.add_argument("remote_path")
    push_parser.add_argument("branch")
    push_parser.set_defaults(func=push)

    add_parser = commands.add_parser("add")
    # takes >= 1 argument, wrap into list
    add_parser.add_argument("paths", nargs="+")
    add_parser.set_defaults(func=add)

    return parser.parse_args()


def init(args):
    base.init()
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


def _print_commit_data(commit_oid, commit: base.Commit, refs: list[str] = []) -> None:
    refs_msg = ", ".join(refs) if refs else ""
    print(f"commit {commit_oid}: {refs_msg}\n")

    # .indent(<string>, prefix) will add prefix to every line in the <string>
    print(textwrap.indent(commit.message, "    "))
    print()


def log(args):
    commit_oid = args.oid

    commit_to_ref = defaultdict(list)
    for ref, ref_value in data.iter_refs(deref=True):
        commit_to_ref[ref_value.value].append(ref)

    for commit_oid in base.iter_commits_and_parents({commit_oid}):
        commit = base.get_commit(commit_oid)
        _print_commit_data(commit_oid, commit, commit_to_ref[commit_oid])


def checkout(args):
    base.checkout(args.commit)
    print(f"checkout {args.commit}, now HEAD is {args.commit}")


def tag(args):
    commit_oid = args.commit
    base.create_tag(args.tag_name, commit_oid)
    print(f"create tag: {args.tag_name} for commit: {commit_oid}")


# generate the dot format for graphviz to visualize the commits we have from refs
def k(args):
    dot = 'digraph "commits" {\n'
    dot += '"root" [style=filled color=gray];\n'
    oids = set()
    for (ref, ref_value) in data.iter_refs(deref=False):
        dot += f'"{ref}" [shape=note style=filled color=salmon2];\n'
        dot += f'"{ref}" -> "{ref_value.value}";\n'
        if not ref_value.symbolic: # we want only oid from what we found
            oids.add(ref_value.value)

    for oid in base.iter_commits_and_parents(oids):
        commit = base.get_commit(oid)
        dot += f'"{oid}" [style=filled label="{oid[:10]}" color=darkolivegreen3];\n'
        if commit and commit.parents:
            for parent in commit.parents:
                dot += f'"{oid}" -> "{parent or "root"}";\n'

    dot += "}"
    print(dot)

    # subprocess is a lib for openning other program
    # Popen stands for process open, start another process and execute something:
        # it return a object represented a process
    # we use with ... as ... to terminate gracefully at the end
    with subprocess.Popen(
        ["xdot", "/dev/stdin"], # run "dot" using gtk (gui) from stdin
        stdin=subprocess.PIPE # set up a way python program can use the process's stdin
    ) as process:
        process.communicate(dot.encode()) # this function send bytes into stdin



def branch(args):
    if not args.branch_name:
        cur_branch = base.get_current_branch()
        for branch in base.iter_branches_name():
            prefix = "*" if cur_branch == branch else " "
            print(f"{prefix} {branch}")
    else:
        base.create_branch(args.branch_name, args.start_point)
        print(f"create branch {args.branch_name} at {args.start_point[:10]}")


def status(args):
    current_branch = base.get_current_branch()
    if current_branch:
        print(f"current branch: {current_branch}")
    else: # detached case
        head_oid = base.get_oid("HEAD")
        print(f"HEAD detached at {head_oid[:10]}")

    merge_head = data.get_ref_value("MERGE_HEAD")
    if merge_head:
        print(f"Merging with {merge_head.value[:10]}")

    latest_commit_oid = base.get_oid("HEAD")
    latest_commit = base.get_commit(latest_commit_oid)
    assert latest_commit is not None
    target_tree = base.get_tree(latest_commit.tree)
    working_tree = base.get_working_tree()

    print("\nChanges to be commited\n")
    for (path, change_type) in diff.iter_changed_files(working_tree, target_tree):
        print(f"{change_type}: {path}")


def reset(args):
    base.reset(args.commit, args.hard)
    print(f"reset to commit {args.commit[:10]}")


def show(args):
    commit_oid = args.commit
    commit = base.get_commit(commit_oid)
    _print_commit_data(commit_oid, commit)
    if commit.parents:
        parent = commit.parents[0] # we use first parent to always be HEAD branch
        parent_tree_oid = base.get_commit(parent).tree
        current_tree_oid = commit.tree

        parent_tree = base.get_tree(parent_tree_oid)
        current_tree = base.get_tree(current_tree_oid)
        diff_msg = diff.diff_trees(current_tree, parent_tree)

        sys.stdout.buffer.flush()
        sys.stdout.buffer.write(diff_msg)

def show_diff(args):
    target_commit = base.get_commit(args.commit)
    assert target_commit is not None
    target_tree = base.get_tree(target_commit.tree)
    working_tree = base.get_working_tree()

    diff_msg = diff.diff_trees(working_tree, target_tree)
    sys.stdout.buffer.flush()
    sys.stdout.buffer.write(diff_msg)


def merge(args):
    base.merge(args.commit)
    print(f"merge commit {args.commit}")


def merge_base(args):
    base_oid = base.get_merge_base(args.commit_oid_a, args.commit_oid_b)
    print(f"the base is commit {base_oid[:10]}")


def fetch(args):
    path = args.path
    assert os.path.exists(path)
    remote.fetch(path)
    print(f"fetch from {path}")


def push(args):
    remote.push(args.remote_path, args.branch)
    print(f"push {args.branch} to {args.remote_path}")


def add(args):
    base.add(args.paths)
