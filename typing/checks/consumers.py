"""Static-only callers: verify useful types at the existing API boundaries."""
from pathlib import Path
from typing import TYPE_CHECKING, Literal, assert_type

import numpy as np
from numpy.typing import NDArray
from PIL import Image

from riposte.cli import Root, Vae
from riposte.coupled import protect_coupled
from riposte.optimizer import protect
from riposte.release_guard import protect_release
from riposte.metrics import fidelity, transport_report
from riposte.organizer import audit_workspace, organize, plan
from riposte.policy import size_bin
from riposte.publication import (
    PublishRecipe, export_publication, publication_plan, publication_status,
    publication_zip, publications, review_publication,
)
from riposte.quality import QualityLimits, quality_report, spatial_budget
from riposte.sanitize import decode_clean, encode_clean, png_audit
from riposte.server import Jobs
from riposte.store import catalog, find_image, workspace_lock, write_report
from riposte.terminal.actions import command_line
from riposte.terminal.jobs import Operation
from riposte.terminal.keyboard import Key, KeyDecoder
from riposte.terminal.output import Presentation
from riposte.terminal.render import render
from riposte.terminal.service import Request, image_bytes, recipe, select_rows, view_image
from riposte.terminal.state import Session

if TYPE_CHECKING:
    from _riposte_types import (
        CatalogRow, FidelityReport, ImageInfo, JobStarted, OrganizationPlan,
        OrganizationReport, PngAudit, ProgressEvent, PublicationBatch,
        PublicationExport, PublicationPlan, PublicationSummary, QualityReport,
        RecipeRecord, TransportReport, WorkspaceAudit, Progress,
    )


def consume(root: Path, image: Image.Image, image_id: str, batch_id: str) -> None:
    alias_root: Root = root
    aliases: Vae = [root / "model"]
    assert aliases is not None
    assert_type(alias_root, Path)
    assert_type(aliases, list[Path])
    assert_type(size_bin(64, 64), Literal["SML", "MED", "LRG", "XTL"])
    audit = png_audit(encode_clean(image, "2026-09-16"))
    assert_type(audit, PngAudit)
    assert_type(audit["width"], int)
    assert_type(audit["metadata"], Literal["DATE_ONLY"])
    assert_type(decode_clean(root / "image.png").pixels, Image.Image)
    assert_type(catalog(root), list[CatalogRow])
    assert_type(find_image(root, image_id)["bytes"], int)
    assert_type(select_rows(root, month=9, limit=10), list[CatalogRow])
    assert_type(plan(root), OrganizationPlan)
    assert_type(organize(root), OrganizationReport)
    assert_type(audit_workspace(root), WorkspaceAudit)
    with workspace_lock(root) as held:
        assert_type(held, None)
        write_report(root, "last-audit.json", audit_workspace(root))
    assert_type(fidelity(image, image), FidelityReport)
    assert_type(fidelity(image, image)["psnr_db"], float | None)
    assert_type(transport_report(image, image), TransportReport)
    assert_type(quality_report(image, image), QualityReport)
    assert_type(spatial_budget(image, QualityLimits()), NDArray[np.uint8])
    config = PublishRecipe(edges=(64,))
    assert_type(config.public(), RecipeRecord)
    assert_type(publication_plan(root, [image_id], config), PublicationPlan)
    assert_type(publications(root), list[PublicationSummary])
    batch = publication_status(root, batch_id)
    assert_type(batch, PublicationBatch)
    assert_type(batch["items"][0]["status"], Literal["PENDING", "READY_FOR_REVIEW", "BLOCKED"])
    assert_type(review_publication(root, batch_id, [image_id], "REJECTED"), PublicationBatch)
    assert_type(publication_zip(root, batch_id), bytes)
    assert_type(export_publication(root, batch_id), PublicationExport)
    request = Request("publish", root, {"image_ids": [image_id], "vae_dirs": [root], "steps": 2})
    assert_type(command_line(request), str)
    assert_type(recipe(request.values), PublishRecipe)
    assert_type(image_bytes(root, {"image_id": image_id}), bytes)
    assert_type(view_image(root, {"image_id": image_id}), ImageInfo)


def progress(event: "ProgressEvent") -> None:
    if "processed" in event:
        assert_type(event["processed"], int)


def operation(request: Request, callback: "Progress") -> object:
    callback({"phase": "Fixture"})
    return request.name


class ExampleEncoder:
    def __call__(self, x: object) -> object:
        return x


def encoder_contracts(image: Image.Image, encoders: list[ExampleEncoder]) -> None:
    # Existing engines accept lists of concrete adapters and callbacks.
    assert_type(protect(image, encoders, progress=progress)[0], Image.Image)
    assert_type(protect_coupled(image, encoders, progress=progress)[0], Image.Image)
    assert_type(protect_release(image, encoders, progress=progress)[0], Image.Image)


def terminal_contracts() -> None:
    worker = Operation(Request("doctor"), operation)
    assert_type(worker.start(), Operation)
    assert_type(worker.snapshot().processed, int | None)
    assert_type(worker.join(), object)
    decoder = KeyDecoder()
    assert_type(decoder.next(), Key | None)
    state = Session(None, Presentation())
    assert_type(render(state, 80, 24).plain(), str)
    assert_type(Jobs().start(lambda: None), JobStarted)
