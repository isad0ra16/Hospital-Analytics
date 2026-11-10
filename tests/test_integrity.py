import hashlib

import pytest

from hospital_analytics.integrity import ContentFingerprint, sha256_file


def test_sha256_file_matches_hashlib(tmp_path):
    path = tmp_path / "f.bin"
    path.write_bytes(b"abc" * 1_000_000)
    assert sha256_file(path) == hashlib.sha256(b"abc" * 1_000_000).hexdigest()


def _fp(columns, rows):
    fp = ContentFingerprint(columns)
    for row in rows:
        fp.update_row(row)
    return fp.hexdigest()


def test_fingerprint_is_deterministic():
    assert _fp(["A", "B"], [["1", "2"]]) == _fp(["A", "B"], [["1", "2"]])


@pytest.mark.parametrize(
    "other",
    [
        (["A", "B"], [["2", "1"]]),  # values swapped
        (["B", "A"], [["1", "2"]]),  # column names changed
        (["A", "B"], [["1", "2"], ["1", "2"]]),  # extra row
        (["A", "B"], [["1", "2 "]]),  # whitespace difference
    ],
)
def test_fingerprint_detects_changes(other):
    assert _fp(["A", "B"], [["1", "2"]]) != _fp(*other)


def test_fingerprint_is_not_fooled_by_value_boundaries():
    assert _fp(["A", "B"], [["ab", "c"]]) != _fp(["A", "B"], [["a", "bc"]])


def test_fingerprint_rejects_wrong_row_width():
    with pytest.raises(ValueError):
        ContentFingerprint(["A", "B"]).update_row(["1"])
