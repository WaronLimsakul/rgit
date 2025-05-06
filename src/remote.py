import os
from src import data
from typing import Dict


REMOTE_REFS_BASE = os.path.join("refs", "heads") # remote store in refs/heads/
LOCAL_REFS_BASE = os.path.join("refs", "remote") # we will change to store here

def _get_remote_refs(path: str) -> Dict[str, data.RefValue]:
    with data.switch_rgit_dir(path):
        return {ref: ref_val for ref, ref_val in data.iter_refs(prefix="heads")}


def fetch(path: str) -> None:
    remote_refs = _get_remote_refs(path)
    for ref, ref_val in remote_refs.items():
        branch_name = os.path.relpath(ref, REMOTE_REFS_BASE)
        target_path = os.path.join(LOCAL_REFS_BASE, branch_name)
        data.update_ref(target_path, ref_val, deref=False)
