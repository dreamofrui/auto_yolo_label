"""Scenario C: skip training and infer custom images."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image

from core.inferencer import InferConfig, Inferencer
from core.restorer import RestoreConfig, Restorer
from utils.mapping_manager import ImageInfo, MappingManager
from utils.path_encoder import PathEncoder


@dataclass
class FakeBox:
    """Minimal predicted box."""

    cls: int
    xywhn: tuple[float, float, float, float]


@dataclass
class FakeResult:
    """Minimal YOLO prediction result."""

    boxes: list[FakeBox]


class FakeYOLO:
    """Fake inference model."""

    def predict(self, **kwargs: Any) -> list[FakeResult]:
        """Return one prediction for each source image."""
        sources = kwargs["source"]
        return [FakeResult([FakeBox(0, (0.5, 0.5, 0.25, 0.25))]) for _ in sources]


def make_image(path: Path) -> None:
    """Create a tiny image fixture."""
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (64, 64), color=(255, 255, 255)).save(path)


def make_mapping_for_custom_site(site: Path, image_name: str) -> None:
    """Create mapping for restoring a custom inference run."""
    encoder = PathEncoder()
    image_path = site / "CodeA" / "Product1" / image_name
    manager = MappingManager(site / ".autolabeler" / "mapping.json").create_new(site)
    manager.add_class(0, "CodeA")
    manager.add_image(
        encoder.encode("CodeA", "Product1", image_name),
        ImageInfo(
            original_relative=image_path.relative_to(site).as_posix(),
            code="CodeA",
            product="Product1",
            original_name=image_name,
            format=image_path.suffix.lower(),
        ),
    )
    manager.save()


def test_scenario_c_external_model_custom_infer_then_restore(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    """A best.pt from elsewhere can infer custom images and restore labels."""
    site = tmp_path / "site"
    image = site / "CodeA" / "Product1" / "a1.jpg"
    make_image(image)
    make_mapping_for_custom_site(site, image.name)
    model_path = tmp_path / "best.pt"
    model_path.write_bytes(b"model")
    run_dir = site / ".autolabeler" / "inference_results" / "run_custom"
    monkeypatch.setattr("core.inferencer._load_yolo_model", lambda path: FakeYOLO())
    monkeypatch.setattr("core.inferencer._run_id", lambda: "run_custom")

    infer_result = Inferencer().infer(
        InferConfig(
            model_path=model_path,
            site_folder=site,
            output_base_dir=site / ".autolabeler" / "inference_results",
            image_source="custom",
            custom_images=[image],
            device="cpu",
        )
    )

    produced = infer_result.inference_output_dir / "CodeA" / "Product1" / "a1.txt"
    assert produced.exists()

    restore_result = Restorer().restore(
        RestoreConfig(site_folder=site, source_type="inference", run_id="run_custom")
    )

    assert restore_result.success == 1
    assert (site / "CodeA" / "Product1" / "a1.txt").exists()
