"""Storage: round trips, listing, and the boundary that must not leak."""

from __future__ import annotations

import pytest

from imagingagent.config import StorageConfig
from imagingagent.storage import LocalStorage, StorageError, get_storage


def test_bytes_round_trip(storage: LocalStorage) -> None:
    storage.write_bytes("a/b/c.bin", b"\x00\x01\x02")
    assert storage.exists("a/b/c.bin")
    assert storage.read_bytes("a/b/c.bin") == b"\x00\x01\x02"


def test_json_round_trip(storage: LocalStorage) -> None:
    storage.write_json("x.json", {"k": [1, 2, 3], "nested": {"ok": True}})
    assert storage.read_json("x.json") == {"k": [1, 2, 3], "nested": {"ok": True}}


def test_list_keys_uses_forward_slashes(storage: LocalStorage) -> None:
    storage.write_text("runs/1/report.json", "{}")
    storage.write_text("runs/2/report.json", "{}")
    storage.write_text("data/raw/x.txt", "x")
    assert storage.list_keys("runs") == ["runs/1/report.json", "runs/2/report.json"]
    assert storage.list_keys("missing") == []
    assert all("\\" not in key for key in storage.list_keys())


def test_append_and_delete(storage: LocalStorage) -> None:
    storage.append_text("log.txt", "one\n")
    storage.append_text("log.txt", "two\n")
    assert storage.read_text("log.txt") == "one\ntwo\n"
    storage.delete("log.txt")
    assert not storage.exists("log.txt")
    storage.delete("log.txt")  # deleting twice is harmless


def test_local_path_stays_inside_base(storage: LocalStorage) -> None:
    path = storage.local_path("runs/x.json")
    assert storage.base_dir in path.parents


@pytest.mark.parametrize(
    "bad", ["../escape", "/absolute", "a/../../b", "", " padded", "back\\slash"]
)
def test_unsafe_keys_are_rejected(storage: LocalStorage, bad: str) -> None:
    with pytest.raises(StorageError):
        storage.write_text(bad, "nope")


def test_missing_key_raises(storage: LocalStorage) -> None:
    with pytest.raises(StorageError):
        storage.read_bytes("does/not/exist")


def test_factory_builds_local_backend(tmp_path) -> None:
    backend = get_storage(StorageConfig(backend="local", base_dir=tmp_path))
    assert isinstance(backend, LocalStorage)
