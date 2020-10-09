"""Get sample metadata subcommand."""

import click
import backoff
import json
import os

import requests

from gencove import client
from gencove.command.base import Command
from gencove.command.utils import is_valid_uuid
from gencove.exceptions import ValidationError


class GetMetadata(Command):
    """Get metadata command executor."""

    def __init__(self, sample_id, output_filename, credentials, options):
        super().__init__(credentials, options)
        self.sample_id = sample_id
        self.output_filename = output_filename

    def initialize(self):
        """Initialize list subcommand."""
        self.login()

    def validate(self):
        """Validate command input.

        Raises:
            ValidationError - if something is wrong with command parameters.
        """

        if is_valid_uuid(self.sample_id) is False:
            error_message = "Sample ID is not valid. Exiting."
            self.echo_warning(error_message, err=True)
            raise ValidationError(error_message)

    def execute(self):
        self.echo_debug("Retrieving sample metadata:")

        try:
            metadata = self.get_metadata()
            if not metadata["metadata"]:
                self.echo(
                    "There is no metadata associated with sample {}.".format(
                        self.sample_id
                    )
                )
                raise click.Abort()
            self.output_metadata(metadata)

        except client.APIClientError as err:
            self.echo_debug(err)
            if err.status_code == 400:
                self.echo_warning("There was an error getting the metadata.")
                self.echo("The following error was returned:")
                self.echo(err.message)
            elif err.status_code == 404:
                self.echo_warning(
                    "Sample metadata {} does not exist or you do not have "
                    "permission required to access it.".format(self.sample_id)
                )
            else:
                raise

    @backoff.on_exception(
        backoff.expo,
        (requests.exceptions.ConnectionError, requests.exceptions.Timeout),
        max_tries=2,
        max_time=30,
    )
    def get_metadata(self):
        """Get metadata page."""
        return self.api_client.get_metadata(sample_id=self.sample_id)

    def output_metadata(self, metadata):
        """Output reformatted metadata JSON."""
        self.echo_debug("Outputting JSON.")
        if self.output_filename == "-":
            self.echo(json.dumps(metadata, indent=4))
        else:
            dirname = os.path.dirname(self.output_filename)
            if dirname and not os.path.exists(dirname):
                os.makedirs(dirname)
            with open(self.output_filename, "w") as json_file:
                json_file.write(json.dumps(metadata, indent=4))
            self.echo(
                "Sample metadata saved to {}".format(self.output_filename)
            )
