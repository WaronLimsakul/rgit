# base module provide higher level implementation of data.py
import os
import itertools
import string
from src import data, diff
from typing import Dict, Iterator, Tuple, Union
from collections import namedtuple, deque
from pathlib import Path


# a lazy way to define a class with just attributes
Commit = namedtuple("Commit", ["tree", "parents", "message"])
type Tree = Dict[str, str] # path -> oid
type NestedDict = Dict[str, Union[str, "NestedDict"]]


def init() -> None:
    data.init()
    create_branch("master", "") #  don't have any commit, so blank
    master_path = os.path.join("refs", "heads", "master")
    data.update_ref("HEAD", data.RefValue(symbolic=True, value=master_path), deref=False)


# the tree object is a hash of
# type oid name
# ...
# of the files object inside
def write_tree():
    tree_dict = {} # a dict that nested like tree
    with data.get_index() as index:
        for path, oid in index.items():
            file_name = os.path.basename(path)
            dir_name = os.path.dirname(path)
            traverse_list = Path(dir_name).parts

            cur = tree_dict
            for dir in traverse_list:
                if dir not in cur:
                    cur[dir] = {}
                cur = cur[dir]
            cur[file_name] = oid
    """
    Goal: receive dict tree -> return tree oid
    0. have tree content waiting
    1. iterate items
    2. check if it's file or directory
    3. if file (oid string),
        - get the oid, put in the tree content
    4. if dir,
        - jump into tree, call that again
        - get return oid from recursion use that to write tree content
    5. return the tree content
    """
    def write_tree_from_dict(tree_dict: NestedDict) -> str:
        tree_entries = []
        for name, value in tree_dict.items():
            if isinstance(value, str):
                type_ = "blob"
                oid = value
            else:
                type_ = "tree"
                oid = write_tree_from_dict(value)
            tree_entries.append((type_, oid, name))
            tree_content = "".join(f"{type_} {oid} {name}\n"
                for type_, oid, name in sorted(tree_entries))
        tree_oid = data.hash_object(tree_content.encode(), type_="tree")
        return tree_oid
    return write_tree_from_dict(tree_dict)


# now we will only ignore the .rgit (and .git since it's annoying) dir
def is_ignored(path: str) -> bool:
    return ".rgit" in path.split("/") or ".git" in path.split("/")


# get tree oid -> go get each child in tree object and yield as tuple (type, oid, name)
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


# get the oid of a tree, then update index
# and (optinally) write cwd according to the tree it gets
# workflow: tree -> index -> cwd
# write tree to index
# - open index and clear it
# - we have function get_tree that return dict that looks like our index
# - just update index according to the tree we have
# - if update_cwd, write cwd from index
def read_tree(oid: str, update_cwd: bool = False) -> None:
    with data.get_index() as index:
        index.clear()
        index.update(get_tree(oid))
        if update_cwd:
            _index_write_cwd(index)


# from index, write cwd
# - empty cwd
# - go through index items
# - makedirs in each item (exist_ok=True)
# - write the file
def _index_write_cwd(index: Dict[str, str]) -> None:
    _empty_current_dir()
    for path, oid in index.items():
        path = os.path.join(".", path) # not sure if the stored path is relative
        dir_name = os.path.dirname(path)
        os.makedirs(dir_name, exist_ok=True)

        content = data.get_object_content(oid, expected="blob")
        with open(path, "wb") as file:
            file.write(content)


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

    # other parent in merging case
    other_parent_oid = data.get_ref_value("MERGE_HEAD")
    if other_parent_oid:
        commit_content += f"parent {other_parent_oid.value}\n"

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
    tree, parents = "", []

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
            parents.append(value)
        else:
            raise ValueError(f"unknown field {key}")

    message = "\n".join(lines) # the lines left are just message

    return Commit(tree=tree, parents=parents, message=message)


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

    read_tree(commit_data.tree, update_cwd= True)
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
        oid = oids_queue.pop()
        if oid == "" or oid in visited: continue
        visited.add(oid)
        yield oid

        commit = get_commit(oid)
        if not commit:
            continue
        elif commit.parents:
            # we want to do DFS in each branch separately, so if we're at intersection
            # we will push first parent to the stack (append)
            # and other parents (branches) to the queue (extendleft)
            oids_queue.append(commit.parents[0]) # extend takes a list btw
            oids_queue.extendleft(commit.parents[1:])


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
def reset(commit_oid: str, hard: bool) -> None:
    commit = get_commit(commit_oid)
    assert commit is not None, f"invalid commit {commit_oid}"
    assert get_current_branch() is not None, "detached head"

    data.update_ref("HEAD", data.RefValue(symbolic=False, value=commit_oid), deref=True)
    if hard:
        read_tree(commit.tree)


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


# receive 2 tree oids and a base tree oid, do 3-way merge and update index
# optionally, apply to working directory
def read_tree_merged(
    head_tree_oid: str,
    other_tree_oid: str,
    base_tree_oid: str,
    update_cwd: bool = False
) -> None:
    _empty_current_dir()

    head_tree = get_tree(head_tree_oid)
    other_tree = get_tree(other_tree_oid)
    base_tree = get_tree(base_tree_oid)

    merged_tree: Tree = diff.merge_trees(head_tree, other_tree, base_tree)
    # update index first
    with data.get_index() as index:
        index.clear()
        index.update(merged_tree)
        if update_cwd:
            _index_write_cwd(index)


def commit_to_tree_oid(commit_oid: str) -> str:
    commit = get_commit(commit_oid)
    assert commit is not None
    return commit.tree


# takes a commit oid and  fast-forward into it.
# require: commit has to be ahead of HEAD.
def _fast_forward(commit_oid: str) -> None:
    data.update_ref("HEAD", data.RefValue(symbolic=False, value=commit_oid), deref=True)
    tree = commit_to_tree_oid(commit_oid)
    read_tree(tree, update_cwd=True)


# receive any commit oid to merge into, then merge it into HEAD
def merge(commit_oid: str) -> None:
    head_oid = get_oid("HEAD")
    base_oid = get_merge_base(head_oid, commit_oid)

    if base_oid == head_oid:
        _fast_forward(commit_oid)
        print(f"Fast-forward to {commit_oid}")
        return

    head_tree_oid = commit_to_tree_oid(head_oid)
    other_tree_oid = commit_to_tree_oid(commit_oid)
    base_tree_oid = commit_to_tree_oid(base_oid)


    read_tree_merged(head_tree_oid, other_tree_oid, base_tree_oid, update_cwd=True)

    data.update_ref("MERGE_HEAD", data.RefValue(symbolic=False, value=commit_oid))
    commit(f"merge commit {commit_oid[:10]}")
    data.delete_ref("MERGE_HEAD")



# get 2 commit oids and return the commit oid of nearest common ancestor
# Note: I use BFS here because I think it's optimal.
def get_merge_base(oid_a: str, oid_b: str) -> str:
    visited: Dict[str, set[str]] = { "a": set(), "b": set() }
    queue = deque([(oid_a, "a"), (oid_b, "b")])
    while queue:
        oid, branch = queue.popleft()
        other_branch = "a" if branch == "b" else "a"
        if oid in visited[other_branch]:
            return oid

        commit = get_commit(oid)
        if commit is None: continue
        for parent in commit.parents:
            queue.append((parent, branch))
        visited[branch].add(oid)
    raise ValueError(f"couldn't find ancestor for {oid_a[:10]} {oid_b[:10]}")


# receive list of commits and yield all objects it found when traverse
# these commits. note that we don't visit remote repo in this function
# but will yield the oid we foudn to the caller to let it fetch if missing
def iter_objects_in_commits(commit_oids: set[str]) -> Iterator[str]:
    visited = set() # every tree/blob we visit
    # for get all objects from tree
    def iter_objects_in_tree(tree_oid: str) -> Iterator[str]:
        visited.add(tree_oid)
        yield tree_oid
        # this iter is very close to what we want
        for type_, oid, _ in _iter_tree_entries(tree_oid):
            if oid in visited: continue
            if type_ == "tree":
                yield from iter_objects_in_tree(oid)
            else:
                visited.add(oid)
                yield oid

    # iterate every commit we can touch (function guarantee no duplicate)
    for commit_oid in iter_commits_and_parents(commit_oids):
        yield commit_oid # let caller have a chance to fetch
        commit = get_commit(commit_oid)
        assert commit
        if commit.tree in visited: continue
        yield from iter_objects_in_tree(commit.tree)


def is_ancestor(old_oid: str, new_oid: str) -> bool:
    for oid in iter_commits_and_parents({new_oid}):
        if oid == old_oid:
            return True
    return False




# receive a path to file, write the file into object
# then write index: path -> oid
def add(paths: list[str]) -> None:
    def add_file(file_path: str) -> None:
        with open(file_path, "rb") as file:
            content = file.read()

        oid = data.hash_object(content, type_="blob")
        index[file_path] = oid

    def add_dir(dir_path: str) -> None:
        for root, _, file_names in os.walk(dir_path):
            for file_name in file_names:
                file_path = os.path.relpath(os.path.join(root, file_name))
                if is_ignored(file_path): continue
                add_file(file_path)

    with data.get_index() as index:
        for path in paths:
            if not os.path.exists(path):
                print(f"path {path} does not exist")
                continue

            if os.path.isfile(path):
                add_file(path)
            elif os.path.isdir(path):
                add_dir(path)
            else:
                print(f"{path} is neither file nor directory")


def get_index_tree() -> Dict[str, str]:
    with data.get_index() as index:
        return index
