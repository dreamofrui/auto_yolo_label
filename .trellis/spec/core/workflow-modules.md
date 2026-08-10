# Core Workflow Modules

Keep each workflow's policy in its owning module. The GUI and workers should
assemble configs and display results, not duplicate these rules.

| Module | Main entrypoint | Local contract |
| --- | --- | --- |
| `core/scanner.py` | `Scanner.scan` | Strict `site/Code/Product/image` tree; writes mapping and classes metadata. |
| `core/sampler.py` | `Sampler.sample`, `sample_independent` | Flow copies mapped images; Independent moves selected images; strategies are `count`, `ratio`, or `mixed`. |
| `core/labelimg_launcher.py` | `LabelImgLauncher.validate`, `preflight`, `launch` | Validates the configured Python/LabelImg environment and format-specific paths before launching an external process. |
| `core/label_inspector.py` | `LabelInspector.list_runs`, `get_run_tree`, `get_product_labels` | Resolves Flow review data from an inference run, mapping, classes, original images, and editable label paths. |
| `core/trainer.py` | `Trainer.train` | Validates a standard YOLO dataset, resolves device/batch, runs Ultralytics, and returns model paths and metrics. |
| `core/inferencer.py` | `Inferencer.infer` | Runs mapped unsampled/all or Independent folder inference into a separate timestamped run without copying images. |
| `core/restorer.py` | `Restorer.restore`, `restore_independent` | Converts YOLO labels to VOC XML beside matched originals; Flow updates mapping after successful writes. |
| `core/converter.py` | `Converter.analyze_xml_dataset`, `convert_xml_dataset`, `txt_to_xml`, `xml_to_txt` | Converts annotation formats or confirmed image/XML pairs into a standard YOLO dataset without mapping dependency for the XML dataset path. |

## Flow And Independent Modes

Flow operations use `.autolabeler/mapping.json` only when traceability is part
of the workflow. Independent sampling, inference, and restore accept explicit
paths and must not create or require mapping. Keep the distinction visible in
config types (`SampleConfig` versus `IndependentSampleConfig`, for example)
instead of a hidden global flag.

## Outputs

Return output paths and aggregate counts in result dataclasses. Inference uses
`run_YYYYMMDD_HHMMSS/` with `inference_config.json` and `labels/`; review reads
`run/labels` and mapping rather than copied prediction images. Training returns
`best.pt` and `last.pt` paths but does not select a model for the user.

## References

Use the module matrix in `docs/dev/ONBOARDING_SUMMARY.md` to find the matching
GUI page, worker, and focused test before changing a workflow.
