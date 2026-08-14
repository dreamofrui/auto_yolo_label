# AutoLabeler Product Spec

> Status: owner-confirmed mainline spec.
> Last updated: 2026-08-14
> See also: `docs/dev/ARCHITECTURE.md` (system architecture).

This is the requirements baseline for new work. If code, removed docs, or
`legacy/` disagree with this file, follow this file and stop to clarify before
coding.

## 1. Product Goal

AutoLabeler is a desktop-first YOLO semi-automatic image labeling tool.

The user may act as data labeler, model trainer, and operator. The main pain is
manual labeling cost. The product succeeds when the user can label a smaller
training subset, train a YOLO model, predict the remaining images, review/fix
predictions, and write final labels back to the original image folders.

## 2. Main Workflow

```text
scan -> sample -> label with LabelImg -> train -> infer
-> review with LabelImg -> restore XML labels
```

There are two usage modes.

**Flow mode** is the professional, traceable workflow. The user scans a strict
`site/Code/Product/image` tree first. Scan creates `mapping.json` and
`classes.txt`; later modules use mapping for sampling, inference, review, and
restore.

**Independent mode** is for standalone tools. A module may run without mapping
only when it can do its job from explicit user-selected paths. It must not
secretly create or require mapping.

## 3. Mapping

`mapping.json` exists only for Flow mode traceability.

Mapping records at least:

- original relative image path
- code/class name
- product name
- original image file name and suffix
- encoded training/inference identity where needed
- sampled, split, inferred, and restored status where needed

Mapping is used to:

- copy sampled images without losing the original source relationship
- select unsampled images for inference
- locate original images for prediction review
- restore reviewed labels back beside original images

Mapping is not used to:

- force independent tools into the scan workflow
- normalize arbitrary folder structures
- hide global state inside standalone modules

## 4. Scanner

Purpose: create Flow mode metadata from a strict site tree.

Input:

- site root folder
- optional output location
- supported image formats: `.jpg`, `.jpeg`, `.png`, `.bmp`

Required structure:

```text
site/
  CodeA/
    Product1/
      image001.jpg
      image002.png
  CodeB/
    Product2/
      image003.jpg
```

Rules:

- `Code` folder name is the class name.
- `Product` folder name is the product group.
- Supported images must be direct children of a Product folder.
- Product folders may contain supported images and VOC XML label files only;
  other direct files block scan.
- XML label files are ignored during scan; scan does not parse or validate
  their object names against the `Code` folder.
- Images directly under `site/`, directly under `Code/`, or nested below a
  Product subfolder are invalid.
- If any supported image violates the structure, scan fails and reports the
  invalid paths.
- Different Products may contain images with the same file name.
- Within the same `Code/Product`, two images with the same stem but different
  suffixes are invalid because they would produce the same label name.
- Scan does not move, rename, or organize user files.

Output:

- `.autolabeler/mapping.json`
- `classes.txt`
- scan statistics and product counts

## 5. Sampler

Purpose: build a YOLO training dataset that reduces manual labeling work.

Supported strategies:

- `count`: fixed number per group
- `ratio`: percentage per group
- `mixed`: small groups can be fully selected; large groups use min/max/ratio

### Flow Mode Sampling

Input:

- scanned site folder
- mapping
- output dataset folder
- sampling strategy
- train/val ratio

Rules:

- Group by Code/Product from mapping. If the same Product name appears under
  different Codes, treat each Code/Product pair as a separate sampling group.
- Copy sampled images and labels to the YOLO dataset; do not move original
  site files.
- Prefer already labeled images.
- If already labeled images exceed the target sample count, keep them all.
- Fill remaining slots from unlabeled images.
- Non-empty YOLO TXT labels are copied.
- VOC XML labels are converted to YOLO TXT.
- If TXT and XML both exist, prefer TXT and report the duplicate source.
- Empty TXT is invalid; delete only after explicit user confirmation.

### Independent Sampling

Input:

- source image folder
- output folder
- output format: XML labeling folder by default, or YOLO dataset when explicitly
  selected
- sampling strategy
- train/val ratio
- optional classes list or classes file

Rules:

- No mapping is created or updated.
- Group by the smallest folder that directly contains images.
- If a folder directly contains images and any child folder also contains
  images, the structure is ambiguous; stop and ask the user to reorganize the
  directory.
- Move only selected images and matching labels supported by the selected
  output format.
- Unselected images remain in the source folder.
- XML output is the default because it is intended for manual VOC labeling:
  move selected images into the output folder while preserving their source
  relative directory structure, move existing same-stem XML beside them in
  that preserved structure, and do not create `images/`, `labels/`,
  `classes.txt`, or `data.yaml`.
- YOLO output remains optional: move selected images and matching labels into
  a standard YOLO dataset.
- For XML output, preserve source relative directories instead of encoding
  source paths into file names.
- For YOLO output, do not preserve source grouping in output file names and do
  not encode source paths into file names.
- If selected output paths conflict, stop before changing files.
- For YOLO output, if classes are not provided, create an empty `classes.txt`;
  training must block until classes are filled.

### Shared Sampling Safety

- Flow output and optional Independent YOLO output are standard YOLO datasets:
  `images/train`, `images/val`, `labels/train`, `labels/val`, `classes.txt`,
  `data.yaml`.
- For YOLO outputs, split each group after sample selection. If a group has
  only one selected image, put it in train.
- Do not do incremental merge.
- Refuse a non-empty output directory by default.
- Clear output only after explicit user confirmation.
- Before move/delete/overwrite, run full preflight checks. If preflight fails,
  do not modify source files and do not create a partial dataset.

## 6. LabelImg And Review

Purpose: use external LabelImg for both manual labeling and prediction review.

This module is a launcher/helper, not an internal annotation editor.

### Free Labeling

Free labeling supports two annotation formats.

YOLO labeling: the user selects:

- image folder
- `classes.txt`
- label output folder

The tool validates paths, starts LabelImg in YOLO mode, and uses the selected
label output folder for YOLO TXT labels.

VOC labeling: the user selects:

- image folder

The tool validates the image folder, starts LabelImg in Pascal VOC mode, and
lets LabelImg write same-stem XML files beside the images.

Free labeling preflight validates the configured Python/LabelImg environment
and the current mode's required paths before launch. It must not start LabelImg
or create output folders. Launch feedback should show user-facing status such
as PID, mode, and selected paths; it must not expose internal wrapper source or
full `python -c` commands in the GUI log.

### Flow Mode Prediction Review

The user selects an inference run, then selects a Code/Product node from the run
tree.

Rules:

- Review uses mapping to locate original images.
- Review uses `run/labels/...` as the editable prediction label root.
- Prediction images are not copied into the run.
- Missing original images block opening that node and report missing paths.
- Missing labels are allowed, but the user is warned that some images need new
  labels.
- Missing or empty `classes.txt` blocks opening.
- Independent inference review uses Free Labeling; it has no automatic mapping
  tree.

## 7. Trainer

Purpose: train a YOLO model from a prepared YOLO dataset.

Input must be a standard YOLO dataset with:

- `images/train`
- `images/val`
- `labels/train`
- `labels/val`
- `data.yaml`

Rules:

- `data.yaml` must contain valid classes.
- Empty classes block training.
- `images/train` must be non-empty.
- `labels/train` must contain at least one valid label.
- Empty `images/val` is allowed with a warning.
- Empty or missing validation labels are allowed with a warning that metrics are
  not reliable.
- Negative samples are allowed; report missing/empty label counts.

User-facing parameters:

- model path
- epochs
- image size
- batch size, default auto
- device: CPU, GPU, auto, or explicit CUDA ids such as `0`, `1`, `0,1`
- output directory
- advanced YOLO parameters under an advanced settings section with defaults

Output:

- training run directory
- YOLO output files such as `best.pt` and `last.pt`
- metrics and logs when available

The tool displays output model paths. The user chooses which model to use for
inference. Do not automatically select one.

Output directory rules:

- Create a new run by default.
- Refuse a non-empty fixed output directory by default.
- Clear/overwrite only after user confirmation.
- Resume training is not a first-version mainline feature.

## 8. Inferencer

Purpose: generate YOLO TXT prediction labels.

### Flow Mode Inference

Input:

- scanned site folder
- mapping
- model path
- optional confidence threshold
- optional label Y-offset (shift predicted boxes down by a fixed pixel count)
- confidence, IoU, device, batch
- output/run settings

Rules:

- Default source is unsampled images from mapping.
- Optional source is all mapping images.
- Do not copy images.
- Save each inference as a separate run under
  `.autolabeler/inference_results/`.

### Independent Inference

Input:

- image folder
- model path
- optional confidence threshold
- optional label Y-offset
- confidence, IoU, device, batch
- output/run settings

Rules:

- Recursively infer every supported image under the selected folder.
- No mapping is required or updated.
- Preserve the source relative directory structure under `run/labels`.
- Do not copy images.

### Shared Inference Output

All inference runs use this structure:

```text
run_YYYYMMDD_HHMMSS/
  inference_config.json
  labels/
    ...relative label paths...
```

Rules:

- Flow mode run root is `site/.autolabeler/inference_results/`.
- Independent run root is the user-selected output root.
- `inference_config.json` records mode, model, parameters, image root, counts,
  and timestamp.
- Empty predictions write empty `.txt` files.
- Report total images, predicted images, empty predictions, and failures.
- Do not overwrite an existing run or output directory unless the user confirms.
- When run structure changes, update LabelImg review, restore, tests, and docs
  together.

## 9. Restorer

Purpose: write reviewed YOLO labels back as VOC XML beside original images.

Default output is:

```text
YOLO TXT -> VOC XML -> original image folder
```

Do not default to restoring YOLO TXT beside original images. If YOLO format is
needed, use Converter.

Supported sources:

- Flow mode sampled dataset labels: `dataset/labels/train|val` plus mapping.
- Flow mode inference run: `run/labels/...` plus mapping.
- Independent label directory: `label_root/...` plus `image_root/...` using the
  same relative structure.

Independent restore rules:

- No mapping is needed.
- The label relative path must match an image relative path by stem.
- Missing image, multiple same-stem images, missing classes, invalid labels, or
  XML conversion errors fail preflight.
- No mapping is updated.

Shared restore rules:

- Requires `classes.txt` to convert class ids to names.
- Reads image dimensions from the matched image.
- Writes XML with the same stem beside the matched image.
- Existing XML blocks restore by default.
- Overwrite only after user confirmation.
- Run full preflight before writing. If preflight fails, write nothing.
- No automatic backup in the first version.

## 10. Converter

Purpose: build YOLO training data from XML annotations and provide label format
conversion helpers.

Main feature: image + XML directory to standard YOLO dataset.

Input:

- source directory containing images and XML files
- output dataset directory
- train ratio
- optional existing `classes.txt`

Rules:

- No mapping dependency.
- Recursively find supported images and same-stem XML files.
- Valid image/XML pairs all enter the output dataset.
- Do not apply sample `count`, `ratio`, or `mixed` strategies here.
- Use only train/val split ratio.
- Split by the smallest folder that directly contains images.
- Copy source images/XML-derived labels; do not move source data.
- Image without XML is skipped and counted.
- XML without image is skipped and counted.
- XML parse errors block conversion.
- If no valid image/XML pair exists, block conversion.
- Default classes come from XML object names, sorted by name for stability.
- Show collected classes for user confirmation before conversion.
- If the user provides classes, use that order.
- XML object names missing from provided classes block conversion.
- Preserve original file names in the YOLO dataset.
- Do not encode source paths into output file names.
- File-name conflicts are detected during preflight and block conversion.
- Refuse non-empty output directories by default.
- Clear output only after user confirmation.
- Do not do incremental merge and do not write partial datasets.

Helper conversion:

- YOLO TXT + images + classes -> VOC XML
- VOC XML -> YOLO TXT
- These helpers do not replace Restorer and do not infer original business
  structure.

## 11. Non-Goals

- Web, FastAPI, browser UI, or Node subprocess integration.
- Multi-user login, permissions, server job queues, or cloud storage.
- Internal bounding-box editor in the first version.
- Automatic cleanup/restructuring of arbitrary user source directories.
- Guessing classes when the user has not provided enough information.
- Incremental merge into existing generated datasets.
- Silent file moves, deletes, or overwrites.

## 12. Success Criteria

The first version is successful when the user can:

- run the Flow mode chain from scan through XML restore
- use Independent sampling without mapping while preserving unselected source
  data
- open LabelImg for free labeling and Flow mode prediction review
- train from a valid YOLO dataset
- infer with or without mapping
- restore Flow or Independent YOLO labels as XML beside matching images
- convert XML-labeled folders into YOLO training datasets
