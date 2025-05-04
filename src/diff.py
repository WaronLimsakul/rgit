import subprocess
import sys
from collections import defaultdict
from typing import Tuple, Dict, Iterator
from src import data, base
from tempfile import NamedTemporaryFile as TempFile

# receive tuple of trees dict and yield (path, oid_from_tree0, oid_from_tree1, ...)
def compare_trees(*trees: base.Tree) -> Iterator[Tuple[str | None, ...]]:
    files: Dict[str, list[str | None]] = defaultdict(lambda: [None] * len(trees))
    for i, tree in enumerate(trees):
        for path, oid in tree.items():
            files[path][i] = oid

    for path, oids in files.items():
        yield (path, *oids)


def diff_trees(tree_to: base.Tree, tree_from: base.Tree) -> bytes:
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
