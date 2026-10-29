"""Authentication for the generated Maxio Advanced Billing client.

This file is written by hand: the generated client extends MaxioAuth (through the
`base_class` entry in apis.yaml), so regenerating never touches it.
"""

import base64
import dataclasses
from collections.abc import Callable
from typing import Any, Literal

from apiroute import Client, RequestSpec, UnexpectedResponse

from maxio_apiroute.spec_info import OPERATION_SERVERS

ApiKey = str | Callable[[], str]
Region = Literal["us", "eu"]

# Each site is a subdomain of its region's host
REGION_HOSTS = {
    "us": "https://{site}.chargify.com",
    "eu": "https://{site}.ebilling.maxio.com",
}


class MaxioAuth(Client):
    """A Maxio Advanced Billing API key, and the site (subdomain) it belongs to.

        maxio = AdvancedBillingApi(api_key=os.environ["MAXIO_API_KEY"], site="acme")
        maxio.subscriptions.list_subscriptions(per_page=20)
        maxio.customers.models.read_customer(123)

    api_key is a site's API key, or a function returning the current one; it is sent as the
    Basic auth username, with "x" as the password, as Maxio asks. site is the subdomain of
    the site's URL (acme for acme.chargify.com). region="eu" is for sites hosted in the EU
    (acme.ebilling.maxio.com).

    With retries on (they're off by default), a 429 is retried as well as connection failures:
    Maxio processed nothing, so even a POST is safe to repeat. The backoff waits at least as
    long as a Retry-After header asks.

    Event ingestion (recordEvent, bulkRecordEvents) is served from events.chargify.com, and
    is sent there, unless base_url points somewhere else (a proxy or a mock server).
    """

    headers = {
        "Authorization": lambda self: f"Basic {self.basic_credentials()}",
    }

    def __init__(self, api_key: ApiKey, *, site: str, region: Region = "us", **kwargs: Any):
        if region not in REGION_HOSTS:
            raise ValueError(f"region must be one of {sorted(REGION_HOSTS)}, not {region!r}")
        self.site = site
        self.site_url = REGION_HOSTS[region].format(site=site)
        kwargs.setdefault("base_url", self.site_url)
        super().__init__(**kwargs)
        self._api_key = api_key

    def current_api_key(self) -> str:
        return self._api_key() if callable(self._api_key) else self._api_key

    def basic_credentials(self) -> str:
        return base64.b64encode(f"{self.current_api_key()}:x".encode()).decode()

    def should_retry(self, error: Exception, attempt: int) -> bool:
        if isinstance(error, UnexpectedResponse):
            return error.response.status_code == 429
        return super().should_retry(error, attempt)

    def on_request(self, request: RequestSpec) -> RequestSpec | None:
        server = OPERATION_SERVERS.get(request.operation)
        if server is None or not request.url.startswith(f"{self.site_url}/"):
            return None
        host = server.format(site=self.site)
        return dataclasses.replace(request, url=host + request.url[len(self.site_url) :])
