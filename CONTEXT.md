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

**Visual Data Operations Team**:
An enterprise team responsible for preparing, labeling, training, reviewing,
and restoring image data through a controlled production workflow.
_Avoid_: Generic AI team, content team

**Local-First Workbench**:
AutoLabeler's current product posture in which source images, models, task
execution, and file decisions remain under the operator's local control.
_Avoid_: Cloud workspace, multi-tenant workspace

**Product Homepage**:
The first application surface that explains AutoLabeler's value and guides a
user into a supported data workflow; it is distinct from the task center.
_Avoid_: Operations dashboard, task board
