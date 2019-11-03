"""Download command executor."""
import re

from gencove import client
from gencove.command.base import Command, ValidationError
from gencove.constants import DownloadTemplateParts

from .constants import ALLOWED_STATUSES_RE
from .utils import build_file_path, download_file


class Download(Command):
    """Download command executor."""

    def __init__(self, download_to, filters, credentials, options):
        super(Download, self).__init__(credentials, options)
        self.download_to = download_to
        self.project_id = filters.project_id
        self.filters = filters
        self.sample_ids = set()
        self.file_types = filters.file_types
        self.download_template = options.download_template
        self.skip_existing = options.skip_existing

    def initialize(self):
        """Initialize download command."""
        if self.filters.project_id and self.filters.sample_ids:
            self.echo_debug("Bad configuration. Exiting")
            return

        self.login()

        if self.project_id:
            self.echo_debug(
                "Retrieving sample ids for a project: {}".format(
                    self.project_id
                )
            )

            try:
                samples_generator = self._get_paginated_samples()
                for sample in samples_generator:
                    self.sample_ids.add(sample["id"])
            except client.APIClientError:
                self.echo_warning(
                    "Project id {} not found.".format(self.project_id)
                )
                return

    def validate(self):
        """Validate command configuration before execution.

        Raises:
            ValidationError : something is wrong with configuration
        """
        if not self.filters.project_id and not self.filters.sample_ids:
            self.echo_warning(
                "Must specify one of: project id or sample ids", err=True
            )
            raise ValidationError(
                "Must specify one of: project id or sample ids"
            )

        if self.filters.project_id and self.filters.sample_ids:
            self.echo_warning(
                "Must specify only one of: project id or sample ids", err=True
            )
            raise ValidationError(
                "Must specify only one of: project id or sample ids"
            )

        self.echo_debug(
            "Host is {} downloading to {}".format(
                self.options.host, self.download_to
            )
        )

        if not self.is_logged_in:
            raise ValidationError("User must login. Exiting.")

    def execute(self):
        self.echo("Processing samples")
        downloaded_files = set()
        for sample_id in self.sample_ids:
            try:
                sample = self.api_client.get_sample_details(sample_id)
            except client.APIClientError:
                self.echo_warning(
                    "Sample with id {} not found. "
                    "Are you using client id instead of sample id?".format(
                        sample_id
                    )
                )
                return

            self.echo_debug(
                "Processing sample id {}, status {}".format(
                    sample["id"], sample["last_status"]["status"]
                )
            )

            if not ALLOWED_STATUSES_RE.match(sample["last_status"]["status"]):
                self.echo_warning(
                    "Sample #{} has no deliverable.".format(sample["id"]),
                    err=True,
                )
                return

            file_types_re = re.compile(
                "|".join(self.file_types), re.IGNORECASE
            )

            for sample_file in sample["files"]:
                # pylint: disable=C0330
                if self.file_types and not file_types_re.match(
                    sample_file["file_type"]
                ):
                    self.echo_debug(
                        "Deliverable file type is not in desired file types"
                    )
                    continue

                file_prefix = self.download_template.format(
                    **{
                        DownloadTemplateParts.client_id: sample["client_id"],
                        DownloadTemplateParts.gencove_id: sample["id"],
                    }
                )
                file_path = build_file_path(
                    sample_file, file_prefix, self.download_to
                )

                if file_path in downloaded_files:
                    self.echo_warning(
                        "Bad template! Multiple files have the same name. "
                        "Please fix the template and try again."
                    )

                    return

                download_file(
                    file_path, sample_file["download_url"], self.skip_existing
                )

                self.echo_debug("Adding file path: {}".format(file_path))
                downloaded_files.add(file_path)

    def _get_paginated_samples(self):
        """Generate for project samples that traverses all pages."""
        get_samples = True
        next_page = None
        while get_samples:
            self.echo_debug("Getting page: {}".format(next_page or 1))
            req = self.api_client.get_project_samples(
                self.project_id, next_page
            )
            for sample in req["results"]:
                yield sample
            next_page = req["meta"]["next"]
            get_samples = next_page is not None
