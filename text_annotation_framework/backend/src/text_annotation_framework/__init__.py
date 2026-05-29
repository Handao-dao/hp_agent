"""Generic text annotation framework."""

from text_annotation_framework.engine import TextAnnotationEngine
from text_annotation_framework.models import Annotation, AnnotationResult, Document, TextChunk
from text_annotation_framework.profiles import ProfileRegistry, default_profile_registry

__all__ = [
    "Annotation",
    "AnnotationResult",
    "Document",
    "ProfileRegistry",
    "TextAnnotationEngine",
    "TextChunk",
    "default_profile_registry",
]
