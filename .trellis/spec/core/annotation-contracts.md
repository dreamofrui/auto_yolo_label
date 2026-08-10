# Annotation Contracts

`core/annotation_formats.py` is the single owner for the meaning and
serialization of annotations. `CONTEXT.md` calls the domain objects
`Annotation` and `Annotation Format`; YOLO TXT and Pascal VOC XML are storage
representations of the same data.

## Shared Types And Helpers

- `YoloBox` stores a class id and normalized `x_center`, `y_center`, `width`,
  and `height`.
- `VocObject` stores a class name and integer pixel bounds.
- `VocAnnotation` stores a positive image size and parsed objects.
- Use `parse_yolo_label_text`, `yolo_boxes_to_voc_xml`,
  `parse_voc_xml_text`, and `voc_objects_to_yolo_boxes` rather than writing a
  second parser in a feature module.

## Validation Rules

YOLO rows have exactly five fields, finite numeric values, an in-range class id,
centers in `[0, 1]`, and positive dimensions no greater than `1`. Empty or
blank-only TXT is a valid negative annotation. VOC XML requires positive image
dimensions, object names, positive-area boxes, and bounds entirely inside the
image. Invalid boxes are rejected, never clipped.

Raise `AnnotationFormatError` with the shared validation code. Restore adds
feature path context, row number, raw row, image size, class, pixel bounds, and
the violated boundary to its diagnostic; see `core/restorer.py` and
`tests/test_restorer.py`.

## Conversion Ownership

`core/converter.py` owns batch file conversion and XML dataset construction;
`core/restorer.py` owns the business action of writing reviewed labels beside
original images. Do not use a converter helper as a replacement for Restore,
and do not duplicate parser tests in every worker.

## Tests

Put format-level behavior in `tests/test_annotation_formats.py`. Keep
workflow policy and lifecycle assertions in `tests/test_sampler.py`,
`tests/test_restorer.py`, `tests/test_converter.py`, and their worker tests.
