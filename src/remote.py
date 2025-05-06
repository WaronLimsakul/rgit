import os
from src import data, base
from typing import Dict


REMOTE_REFS_BASE = os.path.join("refs", "heads") # remote store in refs/heads/
LOCAL_REFS_BASE = os.path.join("refs", "remote") # we will change to store here


def _get_remote_refs(remote_path: str) -> Dict[str, data.RefValue]:
    with data.switch_rgit_dir(remote_path):
        return {ref: ref_val for ref, ref_val in data.iter_refs(prefix="heads")}


def fetch(remote_path: str) -> None:
    remote_refs = _get_remote_refs(remote_path) # fetch the refs
    ref_vals = set() # want to use this when fetch objects

    # set the remote refs to our local repo
    for ref, ref_val in remote_refs.items():
        branch_name = os.path.relpath(ref, REMOTE_REFS_BASE)
        target_path = os.path.join(LOCAL_REFS_BASE, branch_name)
        data.update_ref(target_path, ref_val, deref=False)
        if not ref_val.symbolic:
            ref_vals.add(ref_val.value)

    for oid in base.iter_objects_in_commits(ref_vals):
        data.fetch_object_if_missing(remote_path, oid)

def _get_remote_objects(remote_path: str) -> set[str]:
    refs_dict = _get_remote_refs(remote_path)
    refvals_set = set()
    for ref_val in refs_dict.values():
        if ref_val.symbolic or not data.object_exists(ref_val.value):
            continue
        refvals_set.add(ref_val.value)

    objects = set()
    with data.switch_rgit_dir(remote_path):
       for oid in base.iter_objects_in_commits(refvals_set):
           objects.add(oid)
    return objects


# only 2 cases we can push:
# 1. remote repo doesn't have this branch
# 2. remote repo has branch + the remote latest commit is ancestor of our latest commit
def can_push(remote_path: str, branch_name: str) -> bool:
    remote_refs = _get_remote_refs(remote_path)
    branch_path = os.path.join("refs", "heads", branch_name)
    if branch_path not in remote_refs:
        return True

    remote_oid = remote_refs[branch_path].value
    if remote_oid == "": # in case remote is just init and "master" branch is ""
        return True

    our_oid = base.get_oid(branch_name)
    return base.is_ancestor(old_oid=remote_oid, new_oid=our_oid)


def push(remote_path: str, branch_name: str) -> None:
    if not can_push(remote_path, branch_name):
        print("cannot force push the repo")
        return

    target_oid = base.get_oid(branch_name)

    remote_objects = _get_remote_objects(remote_path)
    pushed_objects = {oid for oid in base.iter_objects_in_commits({target_oid})}
    needed_objects = pushed_objects.difference(remote_objects)

    for oid in needed_objects:
        data.push_object(remote_path, oid)

    # update the branch ref in remote repo to point to our latest commit
    with data.switch_rgit_dir(remote_path):
        branch_path = os.path.join("refs", "heads", branch_name)
        data.update_ref(branch_path,
            data.RefValue(symbolic=False, value=target_oid), deref=True)
