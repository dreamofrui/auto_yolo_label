"""Contract tests for public core entry points."""

from __future__ import annotations

import inspect
from dataclasses import is_dataclass
from typing import Any, get_type_hints

from core.converter import Converter, TxtToXmlConfig, XmlToTxtConfig
from core.inferencer import InferConfig, Inferencer
from core.labelimg_launcher import (
    LabelImgConfig,
    LabelImgLauncher,
    LabelImgValidateConfig,
)
from core.label_inspector import (
    GetProductLabelsConfig,
    GetRunTreeConfig,
    LabelInspector,
    ListRunsConfig,
)
from core.restorer import RestoreConfig, Restorer
from core.sampler import SampleConfig, Sampler
from core.scanner import ScanConfig, Scanner
from core.trainer import TrainConfig, Trainer

PUBLIC_ENTRYPOINTS: tuple[tuple[type[Any], str, type[Any]], ...] = (
    (Scanner, "scan", ScanConfig),
    (Sampler, "sample", SampleConfig),
    (Trainer, "train", TrainConfig),
    (Inferencer, "infer", InferConfig),
    (LabelInspector, "list_runs", ListRunsConfig),
    (LabelInspector, "get_run_tree", GetRunTreeConfig),
    (LabelInspector, "get_product_labels", GetProductLabelsConfig),
    (Restorer, "restore", RestoreConfig),
    (Converter, "txt_to_xml", TxtToXmlConfig),
    (Converter, "xml_to_txt", XmlToTxtConfig),
    (LabelImgLauncher, "validate", LabelImgValidateConfig),
    (LabelImgLauncher, "launch", LabelImgConfig),
)


def test_public_core_entrypoints_accept_single_dataclass_argument() -> None:
    """All public core entry methods accept exactly one dataclass argument."""
    for cls, method_name, config_cls in PUBLIC_ENTRYPOINTS:
        method = getattr(cls, method_name)
        signature = inspect.signature(method)
        parameters = list(signature.parameters.values())
        hints = get_type_hints(method)

        assert [parameter.name for parameter in parameters] == ["self", "config"]
        assert hints["config"] is config_cls
        assert is_dataclass(config_cls)
        assert parameters[1].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_public_core_entrypoints_do_not_accept_kwargs() -> None:
    """Public core entry methods do not use **kwargs."""
    for cls, method_name, _config_cls in PUBLIC_ENTRYPOINTS:
        signature = inspect.signature(getattr(cls, method_name))
        assert all(
            parameter.kind is not inspect.Parameter.VAR_KEYWORD
            for parameter in signature.parameters.values()
        )
