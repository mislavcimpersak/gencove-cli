"""Tests for utils of Gencove CLI."""
import csv
import os

from click.testing import CliRunner

from gencove.command.base import ValidationError
from gencove.command.download.utils import (
    _get_prefix_parts,
    get_download_template_format_params,
)
from gencove.command.upload.utils import (
    _validate_header,
    parse_fastqs_map_file,
    upload_file,
)
from gencove.constants import DOWNLOAD_TEMPLATE, DownloadTemplateParts
from gencove.command.utils import is_valid_uuid


def test_upload_file(mocker):
    """Sanity check upload function."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open("foo.txt", "w") as fastq_file:
            fastq_file.write("AAABBB")
        mocked_s3_client = mocker.Mock()
        assert upload_file(
            mocked_s3_client,
            "foo.txt",
            "foo-bucket",
            object_name="foo-object.txt",
        )
        mocked_s3_client.upload_file.assert_called_once()


def test___get_filename_dirs_prefix():
    """Test proper processing of parts in download template."""
    client_id = "12345"
    gencove_id = "1"
    template = DOWNLOAD_TEMPLATE.format(
        **get_download_template_format_params(client_id, gencove_id)
    )

    resp = _get_prefix_parts(template)

    assert resp.dirs == "{}/{}".format(client_id, gencove_id)
    assert resp.filename == "{{{}}}".format(
        DownloadTemplateParts.default_filename
    )
    assert resp.file_extension == ""

    template2 = "{client_id}-{gencove_id}_{file_type}".format(
        **get_download_template_format_params(client_id, gencove_id)
    )
    resp = _get_prefix_parts(template2)
    assert resp.dirs == ""
    assert resp.filename == "{}-{}_{{{}}}".format(
        client_id, gencove_id, DownloadTemplateParts.file_type
    )
    assert resp.file_extension == ""

    template3 = "{client_id}-{gencove_id}_{file_type}.vcf.gz".format(
        **get_download_template_format_params(client_id, gencove_id)
    )
    resp = _get_prefix_parts(template3)
    assert resp.dirs == ""
    assert resp.filename == "{}-{}_{{{}}}".format(
        client_id, gencove_id, DownloadTemplateParts.file_type
    )
    assert resp.file_extension == "vcf.gz"


def test_parse_fastqs_map_file():
    """Test parsing of map file into dict."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        os.mkdir("test_dir")
        with open("test_dir/test.fastq.gz", "w") as fastq_file1:
            fastq_file1.write("AAABBB")

        with open("test_dir/test_2.fastq.gz", "w") as fastq_file2:
            fastq_file2.write("AAABBB")

        with open("test_dir/test_3.fastq.gz", "w") as fastq_file3:
            fastq_file3.write("AAABBB")

        with open("test_map.csv", "w") as map_file:
            writer = csv.writer(map_file)
            writer.writerows(
                [
                    ["client_id", "r_notation", "path"],
                    ["barid", "r1", "test_dir/test.fastq.gz"],
                    ["barid", "r2", "test_dir/test_2.fastq.gz"],
                    ["barid", "r1", "test_dir/test_3.fastq.gz"],
                ]
            )

        fastqs = parse_fastqs_map_file("test_map.csv")
        assert len(fastqs) == 2
        assert ("barid", "R1") in fastqs
        assert ("barid", "R2") in fastqs
        assert len(fastqs[("barid", "R1")]) == 2
        assert fastqs[("barid", "R1")][0] == "test_dir/test.fastq.gz"
        assert fastqs[("barid", "R1")][1] == "test_dir/test_3.fastq.gz"


def test_invalid_fastqs_map_file():
    """Test that error is raised if file is invalid."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        os.mkdir("test_dir")
        with open("test_dir/test.fastq.gz", "w") as fastq_file1:
            fastq_file1.write("AAABBB")

        with open("test_dir/test_2.fastq.gz", "w") as fastq_file2:
            fastq_file2.write("AAABBB")

        with open("test_dir/test_3.fastq.gz", "w") as fastq_file3:
            fastq_file3.write("AAABBB")

        with open("test_map.csv", "w") as map_file:
            writer = csv.writer(map_file)
            writer.writerows(
                [
                    ["client_id", "r_notation", "path"],
                    ["barid", "r1", "test_dir/test.fastq.gz"],
                    ["barid", "r2", "test_dir/test_2.fastq.zip"],
                    ["barid", "r1", "test_dir/test_3.fastq.gz"],
                ]
            )
        try:
            parse_fastqs_map_file("test_map.csv")
        except ValidationError as err:
            assert "Bad file extension in path" in err.args[0]


def test_fastqs_map_file_path_does_not_exist():
    """Test that error is raised if file is invalid."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        os.mkdir("test_dir")
        with open("test_dir/test.fastq.gz", "w") as fastq_file1:
            fastq_file1.write("AAABBB")

        with open("test_dir/test_2.fastq.gz", "w") as fastq_file2:
            fastq_file2.write("AAABBB")

        with open("test_dir/test_3.fastq.gz", "w") as fastq_file3:
            fastq_file3.write("AAABBB")

        with open("test_map.csv", "w") as map_file:
            writer = csv.writer(map_file)
            writer.writerows(
                [
                    ["client_id", "r_notation", "path"],
                    ["barid", "r1", "test_dir/test.fastq.gz"],
                    ["barid", "r1", "test_dir/test_3.fastq.gz"],
                    ["barid", "r1", "test_dir/i_dont_exist.fastq.gz"],
                ]
            )
        try:
            parse_fastqs_map_file("test_map.csv")
        except ValidationError as err:
            assert "Could not find" in err.args[0]


def test_fastqs_map_file_has_wrong_header():
    """Test that header is validated properly."""
    with open("test_map.csv", "w") as map_file:
        writer = csv.writer(map_file)
        writer.writerows(
            [
                ["client_id", "r1_notation", "path"],
                ["barid", "r1", "test_dir/test.fastq.gz"],
                ["barid", "r1", "test_dir/test_3.fastq.gz"],
                ["barid", "r1", "test_dir/i_dont_exist.fastq.gz"],
            ]
        )
    try:
        parse_fastqs_map_file("test_map.csv")
    except ValidationError as err:
        assert "Unexpected CSV header" in err.args[0]


def test__validate_header():
    """Test that header is validated properly."""
    header_row = dict(foo="foo", bar="bar")
    try:
        _validate_header(header_row)
    except ValidationError:
        pass

    header_row = dict(
        client_id="client_id", r_notation="r_notation", path="path"
    )
    assert _validate_header(header_row) is None


def test_is_valid_uuid__is_valid():
    assert is_valid_uuid("11111111-1111-1111-1111-111111111111")


def test_is_valid_uuid__is_not_valid__too_long():
    assert is_valid_uuid("11111111-1111-1111-1111-11111111111122") is False


def test_is_valid_uuid__is_not_valid__too_short():
    assert is_valid_uuid("11111111-1111-1111-1111-1") is False


def test_is_valid_uuid__is_not_valid__text():
    assert is_valid_uuid("foo") is False
