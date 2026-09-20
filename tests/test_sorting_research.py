"""Research adaptations: adversarial lexical evidence and real sort transactions."""
import contextlib
import datetime as dt
import json
import os
from pathlib import Path
import random

import pytest
from typer.testing import CliRunner

from riposte import category_corpus as cc
from riposte.category_rules import build_rules, load_rules, match_title, save_rules
from riposte.cli import app
from riposte.errors import RiposteError
from riposte.organizer import audit_workspace, organize, plan, undo_sort
from riposte.policy import Policy, canonical_path, folder_for
from riposte.sort_titles import title_records
from riposte.store import catalog, connect
from riposte.terminal.service import select_rows
from riposte.title_categories import discover_categories

NAMES = ['femaleSoldierSniperDesert.png', 'maleSoldierUniform.png', 'soldierArmorWinter.png',
         'factoryPipeRust.png', 'factoryBrokenWall.png', 'factoryFloorMachinery.png',
         'forestOakAutumn.png', 'forestPineSnow.png', 'forestRockMoss.png']
POLICY = Policy(date_mode="modified")


def collection(root, make_image):
    for name in NAMES:
        make_image(root / name)


def test_research_example_yields_literal_supported_groups_and_abstains_on_conflict():
    model = cc.build_corpus(NAMES)
    assert {c.slug for c in model.categories} == {"factory", "forest", "soldier"}
    for name in NAMES:
        result = model.match(Path(name).stem)
        assert result.category and result.category.slug in name.casefold()
        assert result.matched_terms and result.margin > 0
    assert model.match("soldierFactory").category is None
    assert model.match("SML01").category is None
    assert model.match("unrelatedHoliday").category is None
    assert model.report()["score_kind"] == "IDF_COVERAGE_NOT_PROBABILITY"


def test_name_views_preserve_unicode_products_and_phrase_boundaries():
    assert cc.filename_tokens("ＨＥＡＶＹMetal_Québec_CanonEOS-R5") == ("heavy", "metal", "québec", "canon", "eos", "r5")
    terms = cc.semantic_terms("forest_FINAL_v03_1920x1080_2025-03-11_tree")
    assert terms == {"forest", "tree"}
    assert cc.semantic_terms("forest_123e4567-e89b-12d3-a456-426614174000_tree") == {"forest", "tree"}
    assert cc.semantic_terms("खेल-अभ्यास") == {"खेल", "अभ्यास", "खेल अभ्यास"}
    assert {"r5", "b52", "old", "new"} <= cc.semantic_terms("Canon-R5-B52-old-new")
    rules = build_rules(["Music=heavy metal", "Product=desertsniper", "Copies=copy"])
    assert match_title("HeavyMetalPoster", rules)["category"]["slug"] == "music"
    assert match_title("DesertSniper", rules)["category"]["slug"] == "product"
    assert match_title("copy", rules)["category"]["slug"] == "copies"


def test_normalized_variants_do_not_inflate_support_and_order_is_deterministic():
    names = NAMES + ["forestOakAutumn_copy_001.png", "forestOakAutumn_final_v3_1920x1080.png"]
    model = cc.build_corpus(names)
    assert model.families == len(NAMES)
    random.Random(5).shuffle(names)
    assert cc.build_corpus(names).report() == model.report()
    assert cc.build_corpus([f"forest_copy_{i}.png" for i in range(100)]).categories == ()


def test_npmi_degenerate_cases_and_supported_association():
    assert cc.association(2, 2, 3, 6) == pytest.approx(.6309297536)
    assert cc.association(0, 0, 0, 0) == -1
    assert cc.association(3, 3, 3, 3) == 0
    names = [f"factory_pipe_rust_{word}.png" for word in ("wall", "floor", "tower", "boiler")]
    model = cc.build_corpus(names + NAMES[6:] + ["forestFernWater.png"])
    assert model.pairs > 0
    assert model.match("factory_pipe_rust_wall").category is not None
    assert cc.build_corpus([f"forest_{word}.png" for word in ("oak", "pine", "rock", "moss", "fern", "tree")]).categories == ()


def test_phrase_and_equivalent_words_do_not_propose_competing_folders():
    names = [f'{group}_{word}.png' for group in ('forest_tree', 'factory_pipe')
             for word in ('oak', 'wall', 'moss', 'stone')]
    model = cc.build_corpus(names)
    assert len(model.categories) == 2
    assert all(model.match(Path(name).stem).category is not None for name in names)


def test_confirmed_anchor_is_reused_when_new_vocabulary_becomes_more_frequent():
    titles = ['forest_tree_oak.png', 'forest_tree_pine.png', 'forest_tree_moss.png',
              'tree_fir.png', 'tree_birch.png', 'tree_maple.png', 'factory_pipe.png', 'factory_floor.png', 'factory_wall.png']
    model = cc.build_corpus(titles, preferred=['forest'])
    assert model.match('forest_tree_snow').category.slug == 'forest'
    separate = cc.build_corpus(titles, preferred=['forest', 'tree'])
    assert {'forest', 'tree'} <= {c.slug for c in separate.categories}


def test_discovery_limit_reports_no_partial_groups(root, make_image, monkeypatch):
    import riposte.title_categories as tc
    collection(root, make_image)
    monkeypatch.setattr(cc, 'MAX_FAMILIES', 2)
    report = tc.discover_categories(root)
    assert report['corpus']['status'] == 'LIMIT_REACHED' and not report['corpus']['categories']


@pytest.mark.parametrize("bound", ["MAX_FAMILIES", "MAX_VOCABULARY", "MAX_FILE_TERMS", "MAX_GROUPS"])
def test_optional_analysis_limits_never_block_actual_sort(root, make_image, monkeypatch, bound):
    collection(root, make_image)
    monkeypatch.setattr(cc, bound, 1)
    preview = plan(root, POLICY, categories=True)
    assert preview["ready"] and not preview["blockers"]
    assert preview["corpus"]["status"] == "LIMIT_REACHED"
    assert all(f["category"] is None for f in preview["files"])
    result = organize(root, POLICY, categories=True, plan_id=preview["plan_id"])
    assert result["checkpoint"] == "COMPLETE" and len(catalog(root)) == len(NAMES)


def test_pair_limit_abstains_and_cancellation_propagates(monkeypatch):
    names = [f"factory_pipe_{w}.png" for w in ("wall", "floor", "boiler")] + NAMES[6:]
    monkeypatch.setattr(cc, "MAX_PAIRS", 0)
    assert cc.build_corpus(names).status == "LIMIT_REACHED"
    def cancel(event):
        assert "filename" not in event
        raise RiposteError("JOB_CANCELLED")
    with pytest.raises(RiposteError, match="JOB_CANCELLED"):
        cc.build_corpus(names, progress=cancel)


def test_default_category_plan_apply_stable_repeat_additions_and_exact_undo(root, make_image):
    collection(root, make_image)
    make_image(root / "soldierFactory.png")
    make_image(root / "SML01.png")
    held = make_image(root / "__float__" / "forestHidden.png")
    originals = {p.name: p.read_bytes() for p in root.glob("*.png")}
    preview = plan(root, POLICY, categories=True)
    assert preview["ready"] and preview["corpus"]["titles"] == 11
    assert preview["counts"]["corpus_category_files"] == 9
    assert all(f["destination"].startswith("2025/March/img/") for f in preview["files"])
    assert not (root / ".riposte").exists()
    assert organize(root, POLICY, categories=True, plan_id=preview["plan_id"])["checkpoint"] == "COMPLETE"
    first = catalog(root)
    repeated = plan(root, POLICY, categories=True)
    assert all(f["action"] == "KEEP" for f in repeated["files"])
    assert organize(root, POLICY, categories=True, plan_id=repeated["plan_id"])["sort_id"] is None
    make_image(root / "forestRiverBank.png")
    next_plan = plan(root, POLICY, categories=True)
    assert all(f["action"] == "KEEP" for f in next_plan["files"] if f["source"] != "forestRiverBank.png")
    new = next(f for f in next_plan["files"] if f["source"] == "forestRiverBank.png")
    assert new["category"]["slug"] == "forest"
    organize(root, POLICY, categories=True, plan_id=next_plan["plan_id"])
    assert undo_sort(root, apply=True)["checkpoint"] == "COMPLETE" and catalog(root) == first
    assert undo_sort(root, apply=True)["checkpoint"] == "COMPLETE" and not catalog(root)
    assert all((root / name).read_bytes() == data for name, data in originals.items())
    assert held.exists()


def test_saved_rules_precede_corpus_and_rule_conflicts_are_not_overridden(root, make_image):
    collection(root, make_image)
    save_rules(root, build_rules(["Nature=forest", "Other=forest", "Industry=factory"]), expected_revision=load_rules(root).revision)
    preview = plan(root, POLICY, categories=True)
    assert preview["ready"]
    for item in preview["files"]:
        if "forest" in item["source"].casefold():
            assert item["category"] is None and item["match_status"] == "AMBIGUOUS"
        elif "factory" in item["source"].casefold():
            assert item["category"]["slug"] == "industry" and item["category_source"] == "MATCHED"


def test_corpus_receipt_changes_with_input_and_algorithm_settings(root, make_image, monkeypatch):
    collection(root, make_image)
    preview = plan(root, POLICY, categories=True)
    monkeypatch.setattr(cc, "MIN_MARGIN", .2)
    with pytest.raises(RiposteError, match="CATEGORY_PREVIEW_CHANGED"):
        organize(root, POLICY, categories=True, plan_id=preview["plan_id"])
    assert not (root / ".riposte").exists()


def test_discovery_cli_and_plan_share_groups_without_saving_rules(root, make_image):
    collection(root, make_image)
    groups = discover_categories(root)["corpus"]["categories"]
    assert groups == plan(root, POLICY, categories=True)["corpus"]["categories"]
    result = CliRunner().invoke(app, ["--json", "sort", str(root), "--categories", "--date-mode", "modified"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["corpus"]["categories"] == json.loads(json.dumps(groups))
    assert load_rules(root).revision == "missing" and not (root / ".riposte").exists()


@pytest.mark.parametrize("year", ["0001", "1999", "2023", "2027", "2099"])
def test_real_year_paths_and_canonical_compatibility(year):
    assert folder_for(year + "-03-04", 80, 60).parts == (year, "March", "SML")
    assert canonical_path(f"{year}/March/img/forest/SML/SML01.png")
    assert canonical_path("EVERYTHING_ELSE/March/img/SML/SML01.png")


def test_legacy_year_catalog_relocation_preview_apply_undo_and_filters(root, make_image):
    source = make_image(root / "old.png")
    stamp = dt.datetime(2023, 3, 4, 12).timestamp()
    os.utime(source, (stamp, stamp))
    organize(root, POLICY, plan_id=plan(root, POLICY)["plan_id"])
    row = catalog(root)[0]
    old = root / row["relative"]
    legacy = "EVERYTHING_ELSE/" + row["relative"].split("/", 1)[1]
    dest = root / legacy; dest.parent.mkdir(parents=True)
    old.rename(dest)
    with contextlib.closing(connect(root)) as db:
        db.execute("UPDATE images SET relative=? WHERE id=?", (legacy, row["id"])); db.commit()
    assert select_rows(root, year="EVERYTHING_ELSE")[0]["id"] == row["id"]
    preview = plan(root, POLICY, categories=True)
    assert preview["ready"] and preview["files"][0]["destination"].startswith("2023/March/")
    organize(root, POLICY, categories=True, plan_id=preview["plan_id"])
    assert select_rows(root, year="2023")[0]["id"] == row["id"]
    assert audit_workspace(root)["checkpoint"] == "COMPLETE"
    assert undo_sort(root, apply=True)["checkpoint"] == "COMPLETE"
    assert catalog(root)[0]["relative"] == legacy and title_records(root)[0]["original_filename"] == "old.png"
