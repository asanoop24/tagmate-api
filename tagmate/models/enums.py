from enum import Enum
from arq.jobs import JobStatus as ArqJobStatus


class ActivityTaskEnum(str, Enum):
    ENTITY_CLASSIFICATION = "entity_classification"
    MULTI_LABEL_CLASSIFICATION = "multi_label_classification"
    CLUSTERING = "clustering"


class ActivityStatusEnum(str, Enum):
    CREATED = "created"
    INPROGRESS = "in_progress"
    INCOMPLETE = "incomplete"
    COMPLETED = "completed"
    SAVED = "saved"
    SHARED = "shared"
    DELETED = "deleted"
    TRAINING = "training"

class JobStatusEnum(str, Enum):
    queued = "queued"
    deferred = "deferred"
    complete = "complete"
    in_progress = "in_progress"
    not_found = "not_found"
    success = "success"
    failed = "failed"