"""Webhook signature verification shell command definition."""
import click

from gencove.logger import (
    echo_info,
)

from .utils import is_valid_signature


@click.command("verify")
@click.argument("secret")
@click.argument("header")
@click.argument("payload")
# pylint: disable=too-many-arguments
def verify(
    secret,
    header,
    payload,
):
    """Verify webhook signature.

    Prints OK if the signature is valid INVALID otherwise.

    SECRET  key to be used as a secret for hmac algorithm.

    HEADER  Gencove-Signature header content.

    PAYLOAD JSON payload (i.e., the request’s body).

    \f
    Args:
        secret (str): key to be used as a secret for hmac algorithm.
        header (str): Gencove-Signature header content.
        payload (str): JSON payload (i.e., the request’s body).
    """
    echo_info(
        "OK" if is_valid_signature(secret, header, payload) else "INVALID"
    )
