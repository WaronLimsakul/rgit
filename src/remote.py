import os
from src import data, base
from typing import Dict


REMOTE_REFS_BASE = os.path.join("refs", "heads") # remote store in refs/heads/
LOCAL_REFS_BASE = os.path.join("refs", "remote") # we will change to store here

def _get_remote_refs(remote_path: str) -> Dict[str, data.RefValue]:
    with data.switch_rgit_dir(remote_path):
        return {ref: ref_val for ref, ref_val in data.iter_refs(prefix="heads")}


def fetch(remote_path: str) -> None:
    remote_refs = _get_remote_refs(remote_path)
    ref_vals = set()
    # fetch the the refs
    for ref, ref_val in remote_refs.items():
        branch_name = os.path.relpath(ref, REMOTE_REFS_BASE)
        target_path = os.path.join(LOCAL_REFS_BASE, branch_name)
        data.update_ref(target_path, ref_val, deref=False)
        if not ref_val.symbolic:
            ref_vals.add(ref_val.value)

    times = 0
    for oid in base.iter_objects_in_commits(ref_vals):
        data.fetch_object_if_missing(remote_path, oid)
        times += 1
    print(f"fetch {times} times")
