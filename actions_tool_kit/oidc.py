from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional


def get_id_token(audience: Optional[str] = None) -> str:
    """Fetch an OIDC JWT from the GitHub Actions token endpoint.

    The calling workflow must have the ``id-token: write`` permission::

        permissions:
          id-token: write

    Args:
        audience: Optional token audience string (e.g. a cloud provider URL).
                  When omitted the runner uses its default audience.

    Returns:
        The raw JWT string.

    Raises:
        RuntimeError: When the OIDC environment variables are absent (i.e. the
                      workflow is missing the ``id-token: write`` permission, or
                      code is running outside a runner).
        urllib.error.URLError: When the HTTP request to the token endpoint fails.
    """
    request_url = os.getenv("ACTIONS_ID_TOKEN_REQUEST_URL")
    request_token = os.getenv("ACTIONS_ID_TOKEN_REQUEST_TOKEN")

    if not request_url or not request_token:
        raise RuntimeError(
            "OIDC token not available. "
            "Ensure the workflow has 'permissions: id-token: write' and is "
            "running on a GitHub-hosted or compatible runner."
        )

    url = request_url
    if audience:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}audience={urllib.parse.quote(audience, safe='')}"

    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {request_token}")
    req.add_header("Accept", "application/json; api-version=2.0")
    req.add_header("Content-Type", "application/json")

    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    return str(data["value"])


__all__ = ["get_id_token"]
