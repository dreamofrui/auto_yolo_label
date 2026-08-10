# Core Filesystem Safety

File-changing workflows use a plan-before-write shape. Preflight should resolve
all source files, targets, classes, conflicts, and output paths before any
move, delete, overwrite, restore, or dataset creation.

## Preflight First

- `Sampler.preflight` and `preflight_independent` return estimates, copy/move
  counts, issues, and `can_execute` without writing output.
- `Restorer.preflight` and `preflight_independent` resolve label/image matches,
  classes, target folders, existing XML conflicts, and write counts without
  changing XML or mapping.
- `Converter.analyze_xml_dataset` collects pairs, classes, skipped files, and
  output conflicts before `convert_xml_dataset` is allowed to write.
- LabelImg `preflight` validates the environment and image inputs without
  starting the external process or creating output folders.

The corresponding tests assert that preflight leaves the filesystem and mapping
unchanged. Preserve that property when adding a new high-risk path.

## Output And Overwrite Rules

Generated YOLO directories contain `images/train`, `images/val`,
`labels/train`, `labels/val`, `classes.txt`, and `data.yaml`. Refuse a non-empty
output by default. Only clear or overwrite after the caller explicitly opts in
and the preflight is rerun against the same configuration.

Flow sampling and conversion copy source data. Independent sampling moves only
the selected images and matching labels; unselected images stay in place.
Inference never copies source images and writes a new run directory. Restore
writes VOC XML beside matched originals and blocks existing XML unless
overwrite was confirmed.

## Partial-Write Prevention

Do not create a partial dataset when preflight has blockers. Restore records
created XML paths and rolls them back on an `AutoLabelerError`. Preserve this
all-or-nothing boundary when adding new writes; do not catch an error, report
success, and continue with an incomplete output.

## Path Handling

Use `pathlib.Path` and `PathEncoder` for flattened Flow identities. Keep source
relative paths in mapping and Independent XML output; do not invent encoded
names where the product contract requires structure preservation. Never bypass
`MappingManager` to read or write `mapping.json`.
