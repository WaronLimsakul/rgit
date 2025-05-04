from collections import defaultdict
from typing import Tuple, Dict, Iterator

# receive tuple of trees dict and yield (path, oid_from_tree0, oid_from_tree1, ...)
def compare_trees(*trees: Dict[str, str]) -> Iterator[Tuple[str | None, ...]]:
    files: Dict[str, list[str | None]] = defaultdict(lambda: [None] * len(trees))
    for i, tree in enumerate(trees):
        for path, oid in tree.items():
            files[path][i] = oid

    for path, oids in files.items():
        yield (path, *oids)


def diff_trees(tree_to: Dict[str, str], tree_from: Dict[str, str]) -> str:
    msg = ""
    for path, oid_to, oid_from in compare_trees(tree_to, tree_from):
        if oid_to != oid_from:
            msg += f"modified: {path}"
    return msg
