"""Content-hash verification of result-set code provenance.

Each result's provenance.json records the historical development commit
(`code_commit`) its outputs were produced from. That commit is not part of this
repository's Git history, so equivalence of the run-relevant source files is
verified by SHA-256 against tests/provenance_dependency_hashes.json, whose
hashes were taken from the files' content at that historical commit.
"""
import hashlib
import json
import os

MANIFEST = os.path.join(os.path.dirname(__file__), "provenance_dependency_hashes.json")


def assert_dependencies_unchanged(result_key, prov, deps):
    with open(MANIFEST, encoding="utf-8") as fh:
        entry = json.load(fh)["results"][result_key]
    assert entry["code_commit"] == prov["code_commit"], (
        f"{result_key}: manifest code_commit {entry['code_commit']} != provenance.json {prov['code_commit']}")
    recorded = {d["path"]: d["sha256"] for d in entry["dependencies"]}
    assert set(recorded) == set(deps), f"{result_key}: manifest dependencies {sorted(recorded)} != {sorted(deps)}"
    for path in deps:
        with open(path, "rb") as fh:
            actual = hashlib.sha256(fh.read()).hexdigest()
        assert actual == recorded[path], (
            f"{result_key}: {path} differs from the recorded commit {prov['code_commit']} "
            f"(sha256 {actual} != {recorded[path]})")
