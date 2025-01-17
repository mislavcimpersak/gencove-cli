"""Gencove API client.

Exclude imports from linters due to install aliases breaking the rules.
"""

import datetime
import json
import time
from uuid import UUID
from builtins import str as text  # noqa
from urllib.parse import parse_qs, urljoin, urlparse

from pydantic import BaseModel

from requests import (  # pylint: disable=W0622
    ConnectTimeout,
    ConnectionError,
    ReadTimeout,
    get,
    post,
)

from gencove import constants  # noqa: I100
from gencove.constants import (
    SampleArchiveStatus,
    SampleAssignmentStatus,
    SampleSheetSortBy,
    SampleSortBy,
    SampleStatus,
    SortOrder,
)
from gencove.logger import echo_debug
from gencove.models import (
    AccessJWT,
    BaseSpaceBioSample,
    BaseSpaceProject,
    BatchDetail,
    CreateJWT,
    PipelineCapabilities,
    Project,
    ProjectBatchTypes,
    ProjectBatches,
    ProjectMergeVCFs,
    ProjectSamples,
    Projects,
    SampleDetails,
    SampleMetadata,
    SampleQC,
    SampleSheet,
    UploadCredentials,
    UploadSamples,
    UploadsPostData,
)
from gencove.version import version as cli_version


class CustomEncoder(json.JSONEncoder):
    """JSON encoder that knows how to encode `datetime`, `UUID`
    and `pydantic.BaseModel` objects.
    """

    # pylint: disable=method-hidden
    def default(self, o):
        """Override default method of JSONEncoder."""
        if isinstance(o, datetime.datetime):
            return o.isoformat()
        if isinstance(o, BaseModel):
            return {**o.dict(exclude_unset=True), **o.dict(exclude_none=True)}
        if isinstance(o, UUID):
            return str(o)
        return json.JSONEncoder.default(self, o)


class APIError(Exception):
    """Base API Error."""

    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class APIClientError(APIError):
    """Base HTTP error."""


class APIClientTooManyRequestsError(APIClientError):
    """Too many requests (429) HTTP error."""

    status_code = 429


class APIClientTimeout(APIClientError):
    """API timeout exception.

    From http://docs.python-requests.org/en/master/user/quickstart/#timeouts

        timeout is not a time limit on the entire response download;
        rather, an exception is raised if the server
        has not issued a response for timeout seconds
        (more precisely, if no bytes have been received on the underlying
        socket for timeout seconds).
        If no timeout is specified explicitly, requests do not time out.

    Catching this error will catch both
    :exc:`~requests.exceptions.ConnectTimeout` and
    :exc:`~requests.exceptions.ReadTimeout` errors.

    ConnectTimeout:
        The request timed out while trying to connect to the remote server.
        Requests that produced this error are safe to retry.

    ReadTimeout:
        The server did not send any data in the allotted amount of time.
    """


# pylint: disable=too-many-public-methods
class APIClient:
    """Gencove API client."""

    endpoints = constants.ApiEndpoints

    def __init__(self, host=None):
        """Initialize api client."""
        self._jwt_token = None
        self._jwt_refresh_token = None
        self._api_key = None
        self.host = host if host is not None else constants.HOST

    @staticmethod
    def _serialize_post_payload(payload):
        return json.dumps(payload, cls=CustomEncoder)

    # pylint: disable=bad-option-value,bad-continuation,too-many-arguments
    # pylint: disable=too-many-branches
    def _request(
        self,
        endpoint="",
        params=None,
        method="get",
        custom_headers=None,
        timeout=60,
        sensitive=False,
    ):
        url = urljoin(text(self.host), text(endpoint))
        headers = {
            "content-type": "application/json",
            "date": None,
            "Gencove-cli-version": cli_version(),
        }
        if custom_headers:
            headers.update(custom_headers)

        if not params:
            params = {}

        echo_debug(
            "Contacting url: {} with payload: {}".format(
                url, "[SENSITIVE CONTENT]" if sensitive else params
            )
        )
        start = time.time()

        try:
            if method == "get":
                response = get(
                    url=url, params=params, headers=headers, timeout=timeout
                )
            else:
                post_payload = APIClient._serialize_post_payload(params)
                response = post(
                    url=url,
                    data=post_payload,
                    headers=headers,
                    timeout=timeout,
                )

            if response.status_code == 429:
                raise APIClientTooManyRequestsError("Too Many Requests")
        except (ConnectTimeout, ConnectionError):
            # If request timed out,
            # let upper level handle it the way it sees fit.
            # one place might want to retry another might not.
            raise APIClientTimeout(  # pylint: disable=W0707
                "Could not connect to the api server"
            )
        except ReadTimeout:
            raise APIClientTimeout(  # pylint: disable=W0707
                "API server did not respond in timely manner"
            )

        echo_debug(
            "API response is {} status is {} in {}ms".format(
                "[SENSITIVE CONTENT]" if sensitive else response.content,
                response.status_code,
                (time.time() - start) * 1000,
            )
        )

        # pylint: disable=no-member
        if response.status_code >= 200 and response.status_code < 300:
            return response.json() if response.text else {}

        http_error_msg = ""
        if 400 <= response.status_code < 500:
            http_error_msg = "API Client Error: {}".format(response.reason)
            if response.text:
                response_json = response.json()
                if "detail" in response_json:
                    http_error_msg += ": {}".format(response_json["detail"])
                else:
                    try:
                        error_msg = "\n".join(
                            [
                                # create-batch can return error details that
                                # is a dict, not a list
                                "  {}: {}".format(
                                    key,
                                    value[0]
                                    if isinstance(value, list)
                                    else str(value),
                                )
                                for key, value in response_json.items()
                            ]
                        )
                    except AttributeError:
                        error_msg = "\n".join(response_json)
                    http_error_msg += ":\n{}".format(error_msg)

        elif 500 <= response.status_code < 600:
            http_error_msg = "Server Error: {}".format(response.reason)

        raise APIClientError(http_error_msg, response.status_code)

    def _set_jwt(self, access_token, refresh_token=None):
        self._jwt_token = access_token
        if refresh_token is not None:
            self._jwt_refresh_token = refresh_token

    def _refresh_authentication(self):
        echo_debug("Refreshing authentication")
        jwt = self.refresh_token(self._jwt_refresh_token)
        self._set_jwt(jwt.access)

    def _get_authorization(self):
        if self._api_key:
            return {"Authorization": "Api-Key {}".format(self._api_key)}
        return {"Authorization": "Bearer {}".format(self._jwt_token)}

    def _post(
        self,
        endpoint,
        payload=None,
        timeout=120,
        authorized=False,
        sensitive=False,
        refreshed=False,
        model=None,
    ):
        headers = {} if not authorized else self._get_authorization()
        try:
            response = self._request(
                endpoint,
                params=payload,
                method="post",
                timeout=timeout,
                custom_headers=headers,
                sensitive=sensitive,
            )
            if model:
                return model(**response)
            return response
        except APIClientError as err:
            if not refreshed and err.status_code and err.status_code == 401:
                self._refresh_authentication()
                return self._post(
                    endpoint,
                    payload,
                    timeout,
                    authorized,
                    sensitive,
                    True,
                    model,
                )

            raise err

    def _get(
        self,
        endpoint,
        query_params=None,
        timeout=120,
        authorized=False,
        sensitive=False,
        refreshed=False,
        model=None,
    ):
        headers = {} if not authorized else self._get_authorization()
        try:
            response = self._request(
                endpoint,
                params=query_params,
                method="get",
                timeout=timeout,
                custom_headers=headers,
                sensitive=sensitive,
            )
            if model:
                return model(**response)
            return response
        except APIClientError as err:
            if not refreshed and err.status_code and err.status_code == 401:
                self._refresh_authentication()
                return self._get(
                    endpoint,
                    query_params,
                    timeout,
                    authorized,
                    sensitive,
                    True,
                    model,
                )

            raise err

    @staticmethod
    def _add_query_params(next_link, query_params=None, limit=200):
        if not query_params:
            query_params = {}
        query_params.update({"offset": 0, "limit": limit})
        if next_link:
            query_params["offset"] = parse_qs(urlparse(next_link).query)[
                "offset"
            ]
        return query_params

    def set_api_key(self, api_key):
        """Set api key on this instance."""
        self._api_key = api_key

    def refresh_token(self, refresh_token):
        """Refresh jwt token."""
        return self._post(
            self.endpoints.REFRESH_JWT.value,
            {"refresh": refresh_token},
            sensitive=True,
            model=AccessJWT,
        )

    def get_jwt(self, email, password):
        """Get jwt token."""
        return self._post(
            self.endpoints.GET_JWT.value,
            dict(email=email, password=password),
            sensitive=True,
            model=CreateJWT,
        )

    def login(self, email, password):
        """Log user in."""
        jwt = self.get_jwt(email, password)
        self._set_jwt(jwt.access, jwt.refresh)

    def get_upload_details(self, gncv_file_path):
        """Get file upload details.
        Args:
            gncv_file_path (str): gncv notated path

        Returns:
            dict: Upload details from the backend
        """
        return self._post(
            self.endpoints.UPLOAD_DETAILS.value,
            dict(destination_path=gncv_file_path),
            authorized=True,
            model=UploadsPostData,
        )

    def get_upload_credentials(self):
        """Get aws credentials for user."""
        return self._post(
            self.endpoints.GET_UPLOAD_CREDENTIALS.value,
            authorized=True,
            sensitive=True,
            model=UploadCredentials,
        )

    def get_project_samples(
        self,
        project_id,
        next_link=None,
        search="",
        sample_status=SampleStatus.ALL.value,
        sample_archive_status=SampleArchiveStatus.ALL.value,
        sort_by=SampleSortBy.MODIFIED.value,
        sort_order=SortOrder.DESC.value,
    ):
        """List single project's associated samples."""
        project_endpoint = self.endpoints.PROJECT_SAMPLES.value.format(
            id=project_id
        )
        params = self._add_query_params(
            next_link,
            {
                "search": search,
                "sort_by": sort_by,
                "sort_order": sort_order,
                "status": sample_status,
                "archive_status": sample_archive_status,
            },
        )
        return self._get(
            project_endpoint,
            query_params=params,
            authorized=True,
            model=ProjectSamples,
        )

    def add_samples_to_project(self, samples, project_id, metadata=None):
        """Assign samples to a project.

        Args:
            samples (list of dicts): sample sheet results
            project_id (str): project to which to assign the samples
            metadata (str): JSON metadata to be applied to all samples
        """
        payload = {"uploads": samples, "metadata": metadata}

        return self._post(
            self.endpoints.PROJECT_SAMPLES.value.format(id=project_id),
            payload,
            authorized=True,
            model=UploadSamples,
        )

    def get_sample_details(self, sample_id):
        """Fetch single sample details."""
        return self._get(
            self.endpoints.SAMPLE_DETAILS.value.format(id=sample_id),
            authorized=True,
            model=SampleDetails,
        )

    def get_sample_qc_metrics(self, sample_id):
        """Fetch sample qc metrics.

        Args:
            sample_id(str of uuid): gencove sample id

        Returns:
            list of qc params objects.
        """
        return self._get(
            self.endpoints.SAMPLE_QC_METRICS.value.format(id=sample_id),
            authorized=True,
            model=SampleQC,
        )

    def get_sample_sheet(
        self,
        gncv_path=None,
        assigned_status=SampleAssignmentStatus.ALL.value,
        next_link=None,
        sort_by=SampleSheetSortBy.CREATED.value,
        sort_order=SortOrder.DESC.value,
    ):
        """Fetch user samples.

        Args:
            gncv_path (str): filter samples by gncv notated path.
            assigned_status (str, optional, default 'all'): filter samples by
                assignment status. One of SAMPLE_ASSIGNMENT_STATUS.
            next_link (str, optional): url from previous
                response['meta']['next'].
            sort_by(str): upload fastq field to sort by
            sort_order(str): asc or desc sorting
        """
        params = self._add_query_params(
            next_link,
            {
                "search": gncv_path,
                "status": assigned_status,
                "sort_by": sort_by,
                "sort_order": sort_order,
            },
        )
        return self._get(
            self.endpoints.SAMPLE_SHEET.value,
            query_params=params,
            authorized=True,
            model=SampleSheet,
        )

    def list_projects(self, next_link=None):
        """Fetch projects.

        Args:
            next_link (str, optional): url from previous
                response['meta']['next'].

        Returns:
            api response (dict):
                {
                    "meta": {
                        "count": int,
                        "next": str,
                        "previous": optional[str],
                    },
                    "results": [...]
                }
        """
        params = self._add_query_params(next_link)
        return self._get(
            self.endpoints.PROJECTS.value,
            query_params=params,
            authorized=True,
            model=Projects,
        )

    def get_pipeline_capabilities(self, pipeline_id):
        """Get pipeline capabilities details.

        Args:
            pipeline_id (str:uuid): pipeline id

        Returns:
            dict: pipeline details
        """
        resp = self._get(
            self.endpoints.PIPELINE_CAPABILITES.value.format(id=pipeline_id),
            authorized=True,
            model=PipelineCapabilities,
        )
        return resp

    def get_project_batch_types(self, project_id, next_link=None):
        """List single project's available batch types."""
        project_endpoint = self.endpoints.PROJECT_BATCH_TYPES.value.format(
            id=project_id
        )
        params = self._add_query_params(next_link)
        return self._get(
            project_endpoint,
            query_params=params,
            authorized=True,
            model=ProjectBatchTypes,
        )

    def get_project_batches(self, project_id, next_link=None):
        """List single project's batches."""
        project_endpoint = self.endpoints.PROJECT_BATCHES.value.format(
            id=project_id
        )
        params = self._add_query_params(next_link)
        return self._get(
            project_endpoint,
            query_params=params,
            authorized=True,
            model=ProjectBatches,
        )

    def create_project_batch(
        self, project_id, batch_type, batch_name, sample_ids
    ):
        """Making a post request to create project batch."""
        project_endpoint = self.endpoints.PROJECT_BATCHES.value.format(
            id=project_id
        )

        payload = {
            "name": batch_name,
            "batch_type": batch_type,
            "sample_ids": sample_ids,
        }

        return self._post(
            project_endpoint, payload, authorized=True, model=ProjectBatches
        )

    def get_batch(self, batch_id):
        """Get single batch."""
        batches_endpoint = self.endpoints.BATCHES.value.format(id=batch_id)
        return self._get(batches_endpoint, authorized=True, model=BatchDetail)

    def restore_project_samples(self, project_id, sample_ids):
        """Make a request to restore samples in given project."""
        restore_project_samples_endpoint = (
            self.endpoints.PROJECT_RESTORE_SAMPLES.value.format(id=project_id)
        )

        payload = {"sample_ids": sample_ids}

        return self._post(
            restore_project_samples_endpoint, payload, authorized=True
        )

    def get_project(self, project_id):
        """Get single project."""
        project_endpoint = f"{self.endpoints.PROJECTS.value}{project_id}"
        return self._get(project_endpoint, authorized=True, model=Project)

    def create_merged_vcf(self, project_id):
        """Merge VCF files for a project."""
        merge_vcf_endpoint = self.endpoints.PROJECT_MERGE_VCFS.value.format(
            id=project_id
        )
        return self._post(
            merge_vcf_endpoint, authorized=True, model=ProjectMergeVCFs
        )

    def retrieve_merged_vcf(self, project_id):
        """Retrieve the status of the merge command for a project."""
        merge_vcf_endpoint = self.endpoints.PROJECT_MERGE_VCFS.value.format(
            id=project_id
        )
        return self._get(
            merge_vcf_endpoint, authorized=True, model=ProjectMergeVCFs
        )

    def get_metadata(self, sample_id):
        """Retrieve the metadata for a sample."""
        sample_metadata_endpoint = (
            self.endpoints.SAMPLE_METADATA.value.format(id=sample_id)
        )
        return self._get(
            sample_metadata_endpoint, authorized=True, model=SampleMetadata
        )

    def set_metadata(self, sample_id, metadata):
        """Assign the metadata to a sample."""
        sample_metadata_endpoint = (
            self.endpoints.SAMPLE_METADATA.value.format(id=sample_id)
        )
        payload = {
            "metadata": metadata,
        }
        return self._post(
            sample_metadata_endpoint,
            payload,
            authorized=True,
            model=SampleMetadata,
        )

    def import_basespace_projects(
        self, basespace_project_ids, project_id, metadata=None
    ):
        """Make a request to import BioSamples from BaseSpace projects to a given
        project.

        Args:
            basespace_project_ids (list of strings): BaseSpace projects
            project_id (str): project to which to assign the samples
            metadata (str): JSON metadata to be applied to all samples
        """

        payload = {
            "basespace_project_ids": basespace_project_ids,
            "project_id": project_id,
            "metadata": metadata,
        }

        return self._post(
            self.endpoints.BASESPACE_PROJECTS_IMPORT.value,
            payload,
            authorized=True,
        )

    def list_basespace_projects(self, next_link=None):
        """Make a request to list BaseSpace projects.

        Args:
            next_link (str, optional): url from previous
                response['meta']['next'].

        Returns:
            api response (dict):
                {
                    "meta": {
                        "count": int,
                        "next": str,
                        "previous": optional[str],
                    },
                    "results": [...]
                }
        """
        params = self._add_query_params(next_link)
        return self._get(
            self.endpoints.BASESPACE_PROJECTS_LIST.value,
            query_params=params,
            authorized=True,
            model=BaseSpaceProject,
        )

    def list_biosamples(self, basespace_project_id, next_link=None):
        """Make a request to list BioSamples from a BaseSpace project.

        Args:
            basespace_project_id (str): what BaseSpace project to request
                BioSamples from
            next_link (str, optional): url from previous
                response['meta']['next'].

        Returns:
            api response (dict):
                {
                    "meta": {
                        "count": int,
                        "next": str,
                        "previous": optional[str],
                    },
                    "results": [...]
                }
        """
        params = self._add_query_params(next_link)
        return self._get(
            self.endpoints.BASESPACE_BIOSAMPLES_LIST.value.format(
                id=basespace_project_id
            ),
            query_params=params,
            authorized=True,
            model=BaseSpaceBioSample,
        )
