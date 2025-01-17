"""Gencove CLI models"""
from datetime import datetime
from typing import Any, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, HttpUrl


# pylint: disable=too-few-public-methods
class GencoveBaseModel(BaseModel):
    """Gencove Base Model"""

    id: UUID


class AccessJWT(BaseModel):
    """AccessJWT model"""

    access: str


class CreateJWT(AccessJWT):
    """CreateJWT model"""

    refresh: str


class S3Object(BaseModel):
    """S3Object model"""

    bucket: Optional[str]
    object_name: Optional[str]


class GencoveStatus(GencoveBaseModel):
    """GencoveStatus model"""

    status: Optional[str]
    note: Optional[str]
    created: Optional[datetime]
    transition_cutoff: Optional[datetime]


class UploadsPostData(GencoveBaseModel):
    """UploadsPostData model"""

    destination_path: Optional[str]
    s3: Optional[S3Object]
    last_status: Optional[GencoveStatus]


class ResponseMeta(BaseModel):
    """ResponseMeta model"""

    count: Optional[int]
    next: Optional[str]
    previous: Optional[str]


# pylint: disable=too-few-public-methods
class PipelineCapabilities(GencoveBaseModel):
    """Pipeline Capabilities record"""

    name: Optional[str]
    private: Optional[bool]
    merge_vcfs_enabled: Optional[bool]


class SampleFile(GencoveBaseModel):
    """SampleFile model"""

    s3_path: Optional[str]
    size: Optional[int]
    download_url: Optional[HttpUrl]
    file_type: Optional[str]


# pylint: disable=too-few-public-methods
class Project(GencoveBaseModel):
    """Project record"""

    name: Optional[str]
    description: Optional[str]
    created: Optional[datetime]
    organization: Optional[str]
    sample_count: Optional[int]
    pipeline_capabilities: Optional[Union[UUID, PipelineCapabilities]]
    roles: Optional[dict]
    webhook_url: Optional[Union[HttpUrl, str]]  # deprecated
    files: Optional[List[SampleFile]]


class UploadCredentials(BaseModel):
    """UploadCredentials model"""

    version: Optional[int]
    access_key: Optional[str]
    secret_key: Optional[str]
    token: Optional[str]
    expiry_time: Optional[str]  # needs to be str for boto3 to work


class SampleDetails(GencoveBaseModel):
    """SampleDetails model"""

    created: Optional[datetime]
    modified: Optional[datetime]
    client_id: Optional[str]
    physical_id: Optional[str]
    legacy_id: Optional[str]
    last_status: Optional[GencoveStatus]
    archive_last_status: Optional[GencoveStatus]
    files: Optional[List[SampleFile]]


class ProjectSamples(BaseModel):
    """ProjectSamples model"""

    meta: ResponseMeta
    results: Optional[List[SampleDetails]]


class Upload(BaseModel):
    """Upload model"""

    upload: Optional[UUID]
    destination_path: Optional[str]
    last_status: Optional[GencoveStatus]


class Fastqs(BaseModel):
    """Fastqs model"""

    r1: Optional[Upload]
    r2: Optional[Upload]


class Sample(BaseModel):
    """Sample model"""

    client_id: Optional[str]
    fastq: Optional[Fastqs]
    sample: Optional[UUID]


class SampleSheet(BaseModel):
    """SampleSheet model"""

    meta: ResponseMeta
    results: Optional[List[Sample]]


class UploadSamples(BaseModel):
    """UploadSamples model"""

    uploads: Optional[List[Sample]]
    metadata: Optional[Any]


class QualityControlType(BaseModel):
    """QualityControlType model"""

    key: Optional[str]
    type: Optional[str]


class QualityControlData(BaseModel):
    """QualityControlData model"""

    value_expected: Optional[float]
    value_measured: Optional[float]
    status: Optional[str]


class QualityControl(BaseModel):
    """QualityControl model"""

    quality_control_type: Optional[QualityControlType]
    quality_control: Optional[QualityControlData]


class SampleQC(BaseModel):
    """SampleQC model"""

    meta: ResponseMeta
    results: Optional[List[QualityControl]]


class ClientFastQ(BaseModel):
    """ClientFastQ model"""

    client_id: Optional[str]
    fastq: Optional[Upload]


class UploadFastQ(BaseModel):
    """UploadFastQ model"""

    meta: ResponseMeta
    results: Optional[List[ClientFastQ]]


class Projects(BaseModel):
    """Projects model"""

    meta: ResponseMeta
    results: Optional[List[Project]]


class BatchType(BaseModel):
    """BatchType model"""

    key: Optional[str]
    description: Optional[str]


class ProjectBatchTypes(BaseModel):
    """ProjectBatchTypes model"""

    meta: ResponseMeta
    results: Optional[List[BatchType]]


class BatchDetail(GencoveBaseModel):
    """BatchDetail model"""

    name: Optional[str]
    batch_type: Optional[str]
    sample_ids: Optional[List[UUID]]
    last_status: Optional[GencoveStatus]
    files: Optional[List[SampleFile]]


class ProjectBatches(BaseModel):
    """ProjectBatches model"""

    meta: ResponseMeta
    results: Optional[List[BatchDetail]]


class ProjectMergeVCFs(GencoveBaseModel):
    """ProjectMergeVCFs model"""

    created: Optional[datetime]
    user: Optional[UUID]
    last_status: Optional[GencoveStatus]
    up_to_date: Optional[bool]


class SampleMetadata(BaseModel):
    """SampleMetadata model"""

    metadata: Optional[Any]


class BaseSpaceProjectDetail(BaseModel):
    """BaseSpace project detail model"""

    basespace_id: Optional[str]
    basespace_name: Optional[str]
    basespace_date_created: Optional[datetime]


class BaseSpaceProject(BaseModel):
    """BaseSpace project model"""

    meta: ResponseMeta
    results: Optional[List[BaseSpaceProjectDetail]]


class BaseSpaceBioSampleDetail(BaseModel):
    """BaseSpace BioSample detail model"""

    basespace_id: Optional[str]
    basespace_bio_sample_name: Optional[str]
    basespace_date_created: Optional[datetime]


class BaseSpaceBioSample(BaseModel):
    """BaseSpace BioSample model"""

    meta: ResponseMeta
    results: Optional[List[BaseSpaceBioSampleDetail]]
