import os
from src import data
from typing import Dict

def _get_remote_refs(path: str) -> Dict[str, data.RefValue]:
    with data.switch_rgit_dir(path):
        return {ref: ref_val for ref, ref_val in data.iter_refs(prefix="heads")}


def fetch(path: str) -> None:
    print("will fetch these refs")
    for ref, _ in _get_remote_refs(path).items():
        print(f"> {ref}")
