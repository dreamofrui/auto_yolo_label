# AutoLabeler Domain

This context defines the shared language for image annotation workflows across
Flow and Independent modes.

## Language

**Annotation**:
The ordered collection of semantic class identities and continuous bounding-box
edges associated with one image size, independent of how that data is stored.
Each box must be finite, have positive area, and lie entirely within the image;
an out-of-bounds box is invalid and is never clipped.
_Avoid_: Treating YOLO labels and VOC labels as different domain concepts

**Annotation Format**:
The storage representation of an Annotation. AutoLabeler currently supports
YOLO TXT and Pascal VOC XML; conversion changes representation, not meaning.
_Avoid_: Annotation type, label type
