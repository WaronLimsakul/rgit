# base module provide higher level implementation of data.py
import os
import itertools
import string
from src import data
from typing import Dict, Iterator, Tuple
from collections import namedtuple, deque


# a lazy way to define a class with just attributes
Commit = namedtuple("Commit", ["tree", "parent", "message"])
type Tree = Dict[str, str] # path -> oid


def init() -> None:
    data.init()
    create_branch("master", "") #  don't have any commit, so blank
    master_path = os.path.join("refs", "heads", "master")
    data.update_ref("HEAD", data.RefValue(symbolic=True, value=master_path), deref=False)


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
def get_tree(oid: str, base_path: str = "") -> Tree:
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

    parent_oid = data.get_ref_value("HEAD")
    if parent_oid: # the first commit doesn't have parent ("")
        commit_content += f"parent {parent_oid.value}\n"

    commit_content += "\n"
    commit_content += f"{message}\n"

    commit_oid = data.hash_object(commit_content.encode(), type_="commit")
    # deref=True because we want to update the non-symbolic one, not shallow ref
    data.update_ref("HEAD", data.RefValue(symbolic=False, value=commit_oid), deref=True)

    return commit_oid


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


def _is_branch(name: str) -> bool:
    branch_path = os.path.join("refs", "heads", name)
    return data.get_ref_value(branch_path, deref=False) is not None


# find the commit oid, read tree from it and update head to the shallow ref (if exist)
def checkout(commit: str) -> None:
    symbolic = _is_branch(commit)
    if symbolic:
        commit = os.path.join("refs", "heads", commit) # update commit to real path
        ref_value = data.get_ref_value(commit, deref=True)
        assert ref_value is not None
        commit_oid = ref_value.value
    else:
        commit_oid = commit

    commit_data = get_commit(commit_oid)
    if not commit_data:
        raise FileNotFoundError(f"commit {commit_oid} from input {commit} not found")

    read_tree(commit_data.tree)
    # deref=False because we want HEAD to be able to be symbolic (point to a branch, not oid)
    data.update_ref("HEAD", data.RefValue(symbolic=symbolic, value=commit), deref=False)


# use update_ref to create tag.
def create_tag(tag: str, commit: str) -> None:
    data.update_ref(f"refs/tags/{tag}", data.RefValue(symbolic=False, value=commit))


# check if the name is from SHA1 hash
def _is_hash(name: str) -> bool:
    return len(name) == 40 and all(ch in string.hexdigits for ch in name)


# receive a name (either ref or oid), if it's not ref hash, then we
# assume it is oid so we return right away
def get_oid(name: str) -> str:
    # "@" is an alias for HEAD
    if name == "@": name = "HEAD"
    # try to get from ref first.
    found_hash = ( # might be deref=False?
        data.get_ref_value(name) or
        data.get_ref_value(f"refs/{name}") or
        data.get_ref_value(f"refs/tags/{name}") or
        data.get_ref_value(f"refs/heads/{name}")
    )
    if found_hash:
        return found_hash.value # sure that it is not symbolic
    elif _is_hash(name): #  this means the name is already oid
        return name
    else:
        raise ValueError(f"couldn't get oid from name {name}")


# Yield as many commit it can reach from commit oids
def iter_commits_and_parents(commit_oids: set[str]) -> Iterator[str]:
    oids_queue = deque(commit_oids)
    visited = set()
    while oids_queue:
        oid = oids_queue.popleft()
        if oid in visited: continue
        visited.add(oid)
        yield oid

        commit = get_commit(oid)
        if not commit:
            continue
        elif commit.parent:
            oids_queue.appendleft(commit.parent)


# create a branch file in refs/heads/ then write the oid to the branch
def create_branch(branch_name: str, start_commit: str) -> None:
    branch_path = os.path.join("refs", "heads", branch_name)
    data.update_ref(branch_path, data.RefValue(symbolic=False, value=start_commit))


# return current branch name in string, return "" if not found
def get_current_branch() -> str:
    head_data = data.get_ref_value("HEAD", deref=False)
    if head_data and head_data.symbolic: # if HEAD is symbolic, it points to a branch
        return os.path.basename(head_data.value) # cut prefix /refs/heads out
    else:
        return ""


def iter_branches_name() -> Iterator[str]:
    for branch_path, _  in data.iter_refs(deref=False, prefix="heads"):
        yield os.path.basename(branch_path)


# move the head (trace back too) to whatever
def reset(commit_oid: str) -> None:
    if not get_commit(commit_oid):
        raise ValueError(f"invalid commit {commit_oid}")

    # have to check if we are detached?
    if not get_current_branch():
        raise ValueError("detached head")

    data.update_ref("HEAD", data.RefValue(symbolic=False, value=commit_oid), deref=True)


# get a Tree for working directory
def get_working_tree(start_point: str = ".") -> Tree:
    working_tree = {}
    for path, _, filenames in os.walk(start_point):
        if is_ignored(path): continue
        for filename in filenames:
            file_path = os.path.join(path, filename)
            with open(file_path, "rb") as file:
                file_bytes = file.read()
            target_path = os.path.relpath(file_path)
            oid = data.hash_object(file_bytes, type_="blob")
            working_tree[target_path] = oid

    return working_tree
