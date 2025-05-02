# base module provide higher level implementation of data.py
import os
import itertools
import string
from src import data
from typing import Dict, Iterator, Tuple
from collections import namedtuple

# the tree object is a hash of
# type oid name
# ...
# of the files object inside
def write_tree(dir_path: str = ".") -> str:
    # listdir will just give list of file name in dir
    # scandir will give list of file-like object I can directly call method on
    # but I have to close the list. so I will use with ... as ... to auto close
    with os.scandir(dir_path) as ls:
        tree_content_list = [] # list of string
        for file in ls:
            type_ = "blob" # have to add _ because it will conflict with keyword
            full_path = f"{dir_path}/{file.name}"
            if is_ignored(full_path):
                continue
            elif file.is_file():
                with open(full_path, 'rb') as f:
                    oid = data.hash_object(f.read())
            elif file.is_dir():
                type_ = "tree"
                oid = write_tree(full_path)
            else:
                raise TypeError(f"file {file.name} is neither file nor directory")

            tree_content_list.append((type_, oid, file.name))
        tree_content = "".join(
            f"{type_} {oid} {file_name}\n"
            for (type_, oid, file_name)
            in sorted(tree_content_list)
        ).encode()
        tree_oid = data.hash_object(tree_content, type_="tree")
        return tree_oid

# now we will only ignore the .rgit (and .git since it's annoying) dir
def is_ignored(path: str) -> bool:
    return ".rgit" in path.split("/") or ".git" in path.split("/")

# get oid -> go get each child in tree object and yield as tuple (type, oid, name)
def _iter_tree_entries(oid: str) -> Iterator[Tuple[str, str, str]]:
    if not oid:
        return
    tree_content_bytes = data.get_object_content(oid, expected="tree")
    tree_content_lines = tree_content_bytes.decode().splitlines()
    for line in tree_content_lines:
        type_, oid, name = line.split(" ", 2)
        yield (type_, oid, name)


# get oid and opt base_path, put every blob inside the tree to dict: path -> oid
def get_tree(oid: str, base_path: str = "") -> Dict[str, str]:
    res = {}
    for (child_type, child_oid, child_name) in _iter_tree_entries(oid):
        assert "/" not in child_name
        assert child_name not in (".", "..")
        child_path = base_path + child_name # assume base_path has trailing /
        if child_type == "blob":
            res[child_path] = child_oid
        elif child_type == "tree":
            res.update(get_tree(child_oid, child_path + "/"))
        else:
            raise ValueError(f"child with oid {oid} has invalid type {child_type}")

    return res

# get the oid of a tree, then write cwd according to the tree it gets
def read_tree(oid: str) -> None:
    _empty_current_dir()
    for (path, oid) in get_tree(oid, base_path="./").items():
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as obj:
            obj.write(data.get_object_content(oid))


# like name said, empty the current dir (ignore .rgit)
# we call it before doing read_tree.
def _empty_current_dir():
    for (root, dirnames, filenames) in os.walk(".", topdown=False):
        for filename in filenames:
            path = os.path.relpath(f"{root}/{filename}")
            if is_ignored(path) or not os.path.isfile(path):
                continue
            os.remove(path)

        for dirname in dirnames:
            path = os.path.relpath(f"{root}/{dirname}")
            if is_ignored(path):
                continue

        try:
            os.rmdir(path)
        except (FileNotFoundError, OSError):
            # some dir has ignored files, we can't delete the non-empty dir
            # so we just pass
            pass

# get message, write tree then hash the commit object
def commit(message: str) -> str:
    tree_oid = write_tree()

    # TODO: have user and timestamp too
    commit_content = f"tree {tree_oid}\n"

    parent_oid = data.get_ref_hash("HEAD")
    if parent_oid: # the first commit doesn't have parent ("")
        commit_content += f"parent {parent_oid}\n"

    commit_content += "\n"
    commit_content += f"{message}\n"


    commit_oid = data.hash_object(commit_content.encode(), type_="commit")
    data.update_ref("HEAD", commit_oid)

    return commit_oid


# a lazy way to define a class with just attributes
Commit = namedtuple("Commit", ["tree", "parent", "message"])

# get the oid of the commit, parse the data then return
# the Commit object (explicit fields, better than normal dict)
def get_commit(oid: str) -> Commit | None:
    if not oid:
        return None
    commit_content = data.get_object_content(oid, expected="commit")
    tree, parent = "", ""

    # iter takes a list and return iterator, an object you can call next() to
    # get the next thing. + there is lib called itertools for loop this class
    lines = iter(commit_content.decode().splitlines())

    # takewhile(predicate, iterator) will get next() thing until predicate
    # return False on the current one. so I use it to just check empty line
    for line in itertools.takewhile(bool, lines):
        key, value = line.split(" ", 1)
        if key == "tree":
            tree = value
        elif key == "parent":
            parent = value
        else:
            raise ValueError(f"unknown field {key}")

    message = "\n".join(lines) # the lines left are just message

    return Commit(tree=tree, parent=parent, message=message)

# read tree using commit_oid and set the head to that ID
def checkout(commit_oid: str) -> None:
    if not os.path.exists(f"{data.OBJECTS_DIR}/{commit_oid}"):
        raise ValueError(f"checkout faile: commit {commit_oid} doesn't exist")

    commit_data = get_commit(commit_oid)
    if not commit_data: return

    read_tree(commit_data.tree)
    data.update_ref("HEAD", commit_oid)


# use update_ref to create tag.
def create_tag(tag: str, commit: str) -> None:
    data.update_ref(f"refs/tags/{tag}", commit)


# check if the name is from SHA1 hash
def _is_hash(name: str) -> bool:
    return len(name) == 40 and all(ch in string.hexdigits for ch in name)


# receive a name (either ref or oid), if it's not ref hash, then we
# assume it is oid so we return right away
def get_oid(name: str) -> str:
    # try to get from ref first.
    found_hash = (
        data.get_ref_hash(name) or
        data.get_ref_hash(f"refs/{name}") or
        data.get_ref_hash(f"refs/tags/{name}") or
        data.get_ref_hash(f"refs/heads/{name}")
    )
    if found_hash:
        return found_hash
    elif _is_hash(name): #  this means the name is already oid
        return name
    else:
        raise ValueError(f"couldn't get oid from name {name}")
