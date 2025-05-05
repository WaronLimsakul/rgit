import subprocess
import sys
from collections import defaultdict
from typing import Tuple, Dict, Iterator, IO
from src import data
from tempfile import NamedTemporaryFile as TempFile


# duplicate of Tree in base.py, avoid circular import
type Tree = Dict[str, str]


# receive tuple of trees dict and yield (path, oid_from_tree0, oid_from_tree1, ...)
def compare_trees(*trees: Tree) -> Iterator[Tuple[str | None, ...]]:
    files: Dict[str, list[str | None]] = defaultdict(lambda: [None] * len(trees))
    for i, tree in enumerate(trees):
        for path, oid in tree.items():
            files[path][i] = oid

    for path, oids in files.items():
        yield (path, *oids)


def diff_trees(tree_to: Tree, tree_from: Tree) -> bytes:
    msg = b""
    for path, oid_to, oid_from in compare_trees(tree_to, tree_from):
        if oid_to != oid_from:
            msg += diff_blobs(oid_to, oid_from, path)
    return msg

def diff_blobs(blob_to_oid: str | None, blob_from_oid: str | None, path: str | None ="blob") -> bytes:
    blob_to_content = data.get_object_content(blob_to_oid) if blob_to_oid else b""
    blob_from_content = data.get_object_content(blob_from_oid) if blob_from_oid else b""

    with TempFile() as blob_to, TempFile() as blob_from:
        blob_to.write(blob_to_content)
        blob_to.flush()

        blob_from.write(blob_from_content)
        blob_from.flush()

        with subprocess.Popen(
            ["/usr/bin/diff", "--unified", "--show-c-function",
            "--label", f"a/{path}", blob_from.name,
            "--label", f"b/{path}", blob_to.name],
            stdout=subprocess.PIPE
        ) as process:
            diff_msg, _ = process.communicate()
        return diff_msg


def iter_changed_files(tree_to: Tree, tree_from: Tree) -> Iterator[Tuple[str, str]]:
    for path, oid_to, oid_from in compare_trees(tree_to, tree_from):
        if oid_to == oid_from or path is None: continue
        elif oid_from is None: yield (path, "created")
        elif oid_to is None: yield (path, "deleted")
        else: yield (path, "modified")

def _temp_file(oid: str | None) -> IO[bytes]:
    file = TempFile()
    content = data.get_object_content(oid) if oid else b""
    file.write(content)
    file.flush()
    return file

def merge_blobs(
    head_oid: str | None,
    other_oid: str | None,
    base_oid: str | None
) -> str:
    with _temp_file(head_oid) as head_file, \
         _temp_file(other_oid) as other_file, \
         _temp_file(base_oid) as base_file:
        with subprocess.Popen(
            ["/usr/bin/diff3", "-m",
                "-L", "HEAD", head_file.name,
                "-L", "BASE", base_file.name,
                "-L", "MERGE_HEAD", other_file.name],
            stdout=subprocess.PIPE
        ) as process:
            merged_content, _ = process.communicate()

        merged_oid = data.hash_object(merged_content, type_="blob")
        return merged_oid


def merge_trees(tree_to: Tree, tree_from: Tree, tree_base: Tree) -> Tree:
    merged_tree = {}
    for path, blob_to, blob_from, blob_base in compare_trees(tree_to, tree_from, tree_base):
        merged_blob_oid = merge_blobs(blob_to, blob_from, blob_base)
        assert path
        merged_tree[path] = merged_blob_oid
    return merged_tree
