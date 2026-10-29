"""Live tests: calls to a Maxio test site, run only when MAXIO_API_KEY and MAXIO_SITE are set.

    MAXIO_API_KEY=... MAXIO_SITE=acme-test uv run pytest tests/live

MAXIO_REGION=eu is for a site hosted in the EU. They check requests and typed models against
what Maxio actually accepts and sends, and clean up the customers they create. A site that
isn't a test site (the site's own "test" flag) is refused, never used.
"""

import os

import pytest

from maxio_apiroute.advanced_billing import AdvancedBillingApi

KEY = os.environ.get("MAXIO_API_KEY", "")
SITE = os.environ.get("MAXIO_SITE", "")
REGION = os.environ.get("MAXIO_REGION", "us")


def pytest_collection_modifyitems(items):
    if KEY and SITE:
        return
    reason = "live tests need MAXIO_API_KEY and MAXIO_SITE, a Maxio test site"
    for item in items:
        if "tests/live/" in item.nodeid:
            item.add_marker(pytest.mark.skip(reason=reason))


@pytest.fixture(scope="session")
def maxio() -> AdvancedBillingApi:
    client = AdvancedBillingApi(api_key=KEY, site=SITE, region=REGION)
    site = client.sites.read_site()["site"]
    assert site.get("test") is True, "refusing to run live tests on a site that isn't a test site"
    return client
