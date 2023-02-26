from enum import Enum


class ActivityTaskEnum(str, Enum):
    ENTITY_CLASSIFICATION = "entity_classification"
    MULTI_LABEL_CLASSIFICATION = "multi_label_classification"


class ActivityStatusEnum(str, Enum):
    CREATED = "created"
    INPROGRESS = "in_progress"
    INCOMPLETE = "incomplete"
    COMPLETED = "completed"
    SAVED = "saved"
    SHARED = "shared"
    DELETED = "deleted"
    TRAINING = "training"