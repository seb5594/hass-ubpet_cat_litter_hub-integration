"""Distribution checks must reject files outside the explicitly reviewed inventory."""

import hashlib
import importlib.util
from zipfile import ZipFile

import pytest
from test_history import ROOT

spec = importlib.util.spec_from_file_location("distribution_provenance", ROOT / "tools/provenance.py")
provenance = importlib.util.module_from_spec(spec)
spec.loader.exec_module(provenance)


@pytest.mark.parametrize("candidate", [{"a.py": "changed"}, {}, {"a.py": "ok", "unexpected.py": "new"}])
def test_inventory_does_not_silently_accept_changed_missing_or_added_files(candidate):
    with pytest.raises(ValueError):
        provenance.verify(candidate, {"files": {"a.py": {"sha256": "ok"}}})


def test_an_archive_must_have_exactly_the_reviewed_bytes(tmp_path):
    archive = tmp_path / "component.zip"
    original = b"# reviewed project implementation\n"
    inventory = {"files": {"a.py": {"sha256": hashlib.sha256(original).hexdigest()}}}
    with ZipFile(archive, "w") as zipped:
        zipped.writestr("a.py", original + b"# unreviewed change\n")
    with ZipFile(archive) as zipped, pytest.raises(ValueError):
        provenance.verify({name: hashlib.sha256(zipped.read(name)).hexdigest() for name in zipped.namelist()}, inventory)


def test_bundled_vendor_key_file_is_rejected_even_before_recording(tmp_path):
    (tmp_path / "vendor_app_keys.json").write_text('{"fixture":"not-a-vendor-key"}')
    with pytest.raises(ValueError, match="vendor_app_keys"):
        provenance.distribution_files(tmp_path)


def test_windows_line_ending_conversion_cannot_create_a_different_linux_archive(tmp_path):
    (tmp_path / "fixture.py").write_bytes(b"# fixture\r\n")
    with pytest.raises(ValueError, match="LF"):
        provenance.distribution_files(tmp_path)
