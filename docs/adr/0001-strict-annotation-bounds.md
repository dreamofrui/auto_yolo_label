# Reject out-of-bounds annotations

AutoLabeler treats image bounds as an Annotation invariant across Restore,
Sample, and Convert. An out-of-bounds YOLO box is rejected rather than silently
clipped, because clipping changes annotation meaning and would make the same
Annotation behave differently across workflows.
