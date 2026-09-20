"""PAC-032 real SQLite row budgets and catalog-integrity regressions."""
import contextlib
import json
from pathlib import Path
import sqlite3

import pytest
from PIL import Image

from riposte import organizer, store
from riposte.category_rules import build_rules, save_rules, load_rules
from riposte.errors import RiposteError
from riposte.policy import Policy
from riposte.sanitize import encode_clean, png_audit
from riposte.sort_titles import save_title, title_records

POLICY = Policy(date_mode="modified")


def collection(root, count):
    save_rules(root, build_rules(["Hockey=hockey"]), expected_revision="missing")
    rows = []
    with store.workspace_lock(root):
        for index in range(count):
            data = encode_clean(Image.new("RGB", (32, 24), (index % 256, 80, 150)), "2025-03-12")
            relative = f"2025/March/img/hockey/SML/SML{index + 1:02}.png"
            store.atomic_clean_write(root, relative, data)
            row = store.record_image(root, relative, png_audit(data), len(data), "filesystem_modified")
            save_title(root, {"id": row["id"], "media": "img", "original_filename": f"hockey-{index}.png",
                             "category": "hockey", "manual": False, "matched_terms": ["hockey"],
                             "rule_revision": load_rules(root).revision,
                             "sha256": row["sha256"]})
            rows.append(row)
    return rows


@contextlib.contextmanager
def read_meter():
    """Count returned media/title SQL rows and their logical JSON bytes, not disk IO."""
    from unittest.mock import patch
    counts = {"rows": 0, "bytes": 0, "selects": 0}
    connect = sqlite3.connect
    class Cursor(sqlite3.Cursor):
        measured = False
        def execute(self, sql, parameters=()):
            self.measured = sql.lstrip().upper().startswith("SELECT") and any(
                f"FROM {table}" in sql.upper() for table in ("IMAGES", "VIDEOS", "SORT_TITLES"))
            if self.measured: counts["selects"] += 1
            return super().execute(sql, parameters)
        def count(self, row):
            if self.measured and row is not None:
                counts["rows"] += 1
                counts["bytes"] += len(json.dumps(list(row), ensure_ascii=True).encode())
            return row
        def __next__(self): return self.count(super().__next__())
        def fetchone(self): return self.count(super().fetchone())
        def fetchall(self): return [self.count(row) for row in super().fetchall()]
    class Connection(sqlite3.Connection):
        def execute(self, sql, parameters=()): return self.cursor(Cursor).execute(sql, parameters)
    def measured(*args, **kwargs):
        kwargs["factory"] = Connection
        return connect(*args, **kwargs)
    with patch.object(sqlite3, "connect", measured): yield counts


@pytest.mark.parametrize("count", [16, 32])
@pytest.mark.parametrize("operation", ["audit", "lookup", "apply"])
def test_catalog_rows_scale_with_collection_not_its_square(root, count, operation):
    rows = collection(root, count)
    preview = organizer.plan(root, POLICY, categories=True)
    with read_meter() as reads:
        if operation == "audit": assert organizer.audit_workspace(root)["checkpoint"] == "COMPLETE"
        elif operation == "lookup":
            for row in rows: assert store.find_image(root, row["id"]) == row
        else: assert organizer.organize(root, POLICY, categories=True, plan_id=preview["plan_id"])["checkpoint"] == "COMPLETE"
    # A bounded number of initial catalog snapshots plus indexed per-file work.
    assert reads["rows"] <= (12 if operation == "apply" else 2 if operation == "audit" else 1) * count, reads


@pytest.mark.parametrize("categories", [False, True])
@pytest.mark.parametrize("change", ["image", "title", "video", "remove"])
def test_external_commit_during_apply_cannot_be_hidden_by_own_writes(root, make_image, categories, change):
    rows = collection(root, 2)
    source = make_image(root / "hockey-new.png")
    original = source.read_bytes()
    preview = organizer.plan(root, POLICY, categories=categories)
    fired = False
    def progress(event):
        nonlocal fired
        if fired: return
        fired = True
        with contextlib.closing(store.connect(root)) as db:
            if change == "image": db.execute("UPDATE images SET date_source='embedded' WHERE id=?", (rows[-1]["id"],))
            if change == "title": db.execute("DELETE FROM sort_titles WHERE id=?", (rows[-1]["id"],))
            if change == "video": db.execute("CREATE TABLE videos (id TEXT PRIMARY KEY, relative TEXT, day TEXT, date_source TEXT, width INTEGER, height INTEGER, sha256 TEXT, bytes INTEGER)")
            if change == "remove": db.execute("DELETE FROM images WHERE id=?", (rows[-1]["id"],))
            db.commit()
    result = organizer.organize(root, POLICY, progress, categories=categories, plan_id=preview["plan_id"])
    assert fired and result["checkpoint"] == "INCOMPLETE"
    assert result["blockers"].get("CATEGORY_PREVIEW_CHANGED" if categories else "SORT_PREVIEW_CHANGED") == 1
    assert source.read_bytes() == original


@pytest.mark.parametrize("change", ["missing", "bytes", "path"])
def test_indexed_lookup_keeps_selected_file_integrity(root, change):
    row = collection(root, 2)[0]
    source = root / row["relative"]
    if change == "missing": source.unlink()
    if change == "bytes": source.write_bytes(encode_clean(Image.new("RGB", (32, 24), "red"), "2025-03-12"))
    if change == "path":
        with contextlib.closing(store.connect(root)) as db:
            db.execute("UPDATE images SET relative='../escape.png' WHERE id=?", (row["id"],)); db.commit()
    with pytest.raises(RiposteError): store.find_image(root, row["id"])


def test_missing_lookup_is_readonly(root):
    before = list(root.iterdir())
    with pytest.raises(RiposteError, match="IMAGE_NOT_FOUND"): store.find_image(root, "a" * 32)
    assert list(root.iterdir()) == before


def test_audit_rejects_a_revision_change_after_snapshot(root, monkeypatch):
    rows = collection(root, 3)
    validate = organizer._validate_managed
    fired = False
    def changed(path, row):
        nonlocal fired
        result = validate(path, row)
        if not fired:
            fired = True
            with contextlib.closing(store.connect(root)) as db:
                db.execute("UPDATE images SET date_source='embedded' WHERE id=?", (rows[-1]["id"],)); db.commit()
        return result
    monkeypatch.setattr(organizer, "_validate_managed", changed)
    result = organizer.audit_workspace(root)
    assert result["checkpoint"] == "INCOMPLETE" and result["blockers"]["CATALOG_CHANGED"] == 1


def test_lookup_uses_the_existing_primary_key_index(root, monkeypatch):
    row = collection(root, 3)[0]
    statements = []
    connect = sqlite3.connect
    def traced(*args, **kwargs):
        db = connect(*args, **kwargs)
        db.set_trace_callback(statements.append)
        return db
    monkeypatch.setattr(sqlite3, "connect", traced)
    assert store.find_image(root, row["id"]) == row
    selected = [s for s in statements if s.upper().startswith("SELECT") and "FROM images" in s]
    assert len(selected) == 1
    with contextlib.closing(connect(root / ".riposte/catalog.sqlite3")) as db:
        details = [r[3] for r in db.execute("EXPLAIN QUERY PLAN " + selected[0])]
    assert any("SEARCH images USING INDEX" in detail and "id=?" in detail for detail in details), details


@pytest.mark.parametrize("categories", [False, True])
def test_foreign_commit_after_own_catalog_write_preserves_source(root, make_image, monkeypatch, categories):
    rows = collection(root, 2)
    source = make_image(root / "hockey-new.png")
    original = source.read_bytes()
    preview = organizer.plan(root, POLICY, categories=categories)
    record = organizer.record_image
    def with_external_commit(*args, **kwargs):
        result = record(*args, **kwargs)
        with contextlib.closing(store.connect(root)) as db:
            db.execute("DELETE FROM sort_titles WHERE id=?", (rows[-1]["id"],)); db.commit()
        return result
    monkeypatch.setattr(organizer, "record_image", with_external_commit)
    result = organizer.organize(root, POLICY, categories=categories, plan_id=preview["plan_id"])
    assert result["checkpoint"] == "INCOMPLETE"
    assert result["blockers"].get("CATEGORY_PREVIEW_CHANGED" if categories else "SORT_PREVIEW_CHANGED") == 1
    assert source.read_bytes() == original


def test_unexpected_trigger_writes_are_not_accepted_as_owned_changes(root, make_image):
    rows = collection(root, 2)
    source = make_image(root / "hockey-new.png")
    original = source.read_bytes()
    with contextlib.closing(store.connect(root)) as db:
        db.execute("CREATE TRIGGER unrelated_title AFTER INSERT ON images BEGIN DELETE FROM sort_titles; END")
        db.commit()
    preview = organizer.plan(root, POLICY)
    result = organizer.organize(root, POLICY, plan_id=preview["plan_id"])
    assert result["checkpoint"] == "INCOMPLETE" and result["blockers"]["SORT_PREVIEW_CHANGED"] == 1
    assert source.read_bytes() == original
    assert all((root / row["relative"]).exists() for row in rows)


def test_catalog_guard_detects_new_database_in_readonly_empty_workspace(root):
    from riposte.catalog_guard import CatalogGuard
    with contextlib.closing(CatalogGuard(root, "CATALOG_CHANGED", read_only=True)) as guard:
        assert not list(root.iterdir())
        with contextlib.closing(store.connect(root)): pass
        with pytest.raises(RiposteError, match="CATALOG_CHANGED"): guard.check()


def test_revision_guard_connection_closes_after_interrupt(root):
    from riposte.catalog_guard import CatalogGuard
    with pytest.raises(KeyboardInterrupt):
        with contextlib.closing(CatalogGuard(root, "CATALOG_CHANGED")) as guard:
            with guard.write() as db:
                db.execute("INSERT INTO images VALUES (?,?,?,?,?,?,?,?)", ("a" * 32, "2025/March/img/SML/SML01.png", "2025-03-12", "embedded", 1, 1, "b" * 64, 1))
                raise KeyboardInterrupt
    assert store.catalog(root) == []
    with pytest.raises(sqlite3.ProgrammingError): db.execute("SELECT 1")
