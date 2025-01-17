"""Describe all constants in Gencove CLI."""
from enum import Enum, unique
from typing import Optional

from pydantic import BaseModel  # pylint: disable=no-name-in-module

HOST = "https://api.gencove.com"


@unique
class ApiEndpoints(Enum):
    """ApiEndpoints enum"""

    GET_JWT = "/api/v2/jwt-create/"
    REFRESH_JWT = "/api/v2/jwt-refresh/"
    UPLOAD_DETAILS = "/api/v2/uploads-post-data/"
    GET_UPLOAD_CREDENTIALS = "/api/v2/upload-credentials/"
    PROJECT_SAMPLES = "/api/v2/project-samples/{id}"
    SAMPLE_DETAILS = "/api/v2/samples/{id}"
    SAMPLE_QC_METRICS = "/api/v2/sample-quality-controls/{id}"
    SAMPLE_SHEET = "/api/v2/sample-sheet/"
    PROJECTS = "/api/v2/projects/"
    PIPELINE_CAPABILITES = "/api/v2/pipeline-capabilities/{id}"
    PROJECT_BATCH_TYPES = "/api/v2/project-batch-types/{id}"
    PROJECT_BATCHES = "/api/v2/project-batches/{id}"
    BATCHES = "/api/v2/batches/{id}"
    PROJECT_MERGE_VCFS = "/api/v2/project-merge-vcfs/{id}"
    SAMPLE_METADATA = "/api/v2/sample-metadata/{id}"
    PROJECT_RESTORE_SAMPLES = "/api/v2/project-restore-samples/{id}"
    BASESPACE_PROJECTS_IMPORT = "/api/v2/basespace-projects-import/"
    BASESPACE_PROJECTS_LIST = "/api/v2/basespace-projects/"
    BASESPACE_BIOSAMPLES_LIST = "/api/v2/basespace-project-biosamples/{id}"


@unique
class SampleAssignmentStatus(Enum):
    """SampleAssignmentStatus enum"""

    ALL = "all"
    UNASSIGNED = "unassigned"
    ASSIGNED = "assigned"


@unique
class SampleSheetSortBy(Enum):
    """SampleSheetSortBy enum"""

    CREATED = "created"
    MODIFIED = "modified"


@unique
class SampleStatus(Enum):
    """SampleStatus enum"""

    COMPLETED = "completed"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    RUNNING = "running"
    ALL = "all"


@unique
class SampleArchiveStatus(Enum):
    """SampleArchiveStatus enum"""

    AVAILABLE = "available"
    ARCHIVED = "archived"
    RESTORE_REQUESTED = "restore_requested"
    ALL = "all"


@unique
class SampleSortBy(Enum):
    """SampleSortBy enum"""

    CREATED = "created"
    MODIFIED = "modified"
    STATUS = "status"
    CLIENT_ID = "client_id"
    ID = "id"


@unique
class SortOrder(Enum):
    """SortOrder enum"""

    ASC = "asc"
    DESC = "desc"


# pylint: disable=too-few-public-methods
class Credentials(BaseModel):
    """Credentials model"""

    email: str
    password: str
    api_key: str


# pylint: disable=too-few-public-methods
class Optionals(BaseModel):
    """Optionals model"""

    host: Optional[str]


@unique
class DownloadTemplateParts(Enum):
    """DownloadTemplateParts enum"""

    CLIENT_ID = "client_id"
    GENCOVE_ID = "gencove_id"
    FILE_TYPE = "file_type"
    FILE_EXTENSION = "file_extension"
    DEFAULT_FILENAME = "default_filename"


DOWNLOAD_TEMPLATE = "{{{}}}/{{{}}}/{{{}}}".format(
    DownloadTemplateParts.CLIENT_ID.value,
    DownloadTemplateParts.GENCOVE_ID.value,
    DownloadTemplateParts.DEFAULT_FILENAME.value,
)

MAX_RETRY_TIME_SECONDS = 300  # 5 minutes
FASTQ_MAP_EXTENSION = ".fastq-map.csv"
UPLOAD_PREFIX = "gncv://"
ASSIGN_BATCH_SIZE = 200
