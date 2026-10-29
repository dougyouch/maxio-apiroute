"""MaxioAuth: Basic auth with the API key, the site's host by region, and the events host."""

import base64
import json

import httpx
import pytest
from apiroute import Retries, UnexpectedResponse

from maxio_apiroute.advanced_billing import AdvancedBillingApi


@pytest.fixture
def maxio(transport):
    return AdvancedBillingApi(api_key="key_123", site="acme", transport=transport)


def basic(key: str) -> str:
    return "Basic " + base64.b64encode(f"{key}:x".encode()).decode()


def test_the_key_is_the_basic_auth_username(maxio, recorder):
    maxio.customers.read_customer(42)
    assert str(recorder.last.url) == "https://acme.chargify.com/customers/42.json"
    assert recorder.last.headers["Authorization"] == basic("key_123")


def test_a_key_function_is_called_on_every_request(transport, recorder):
    keys = iter(["key_a", "key_b"])
    maxio = AdvancedBillingApi(api_key=lambda: next(keys), site="acme", transport=transport)
    maxio.sites.read_site()
    maxio.sites.read_site()
    assert [r.headers["Authorization"] for r in recorder.requests] == [
        basic("key_a"),
        basic("key_b"),
    ]


def test_eu_sites(transport, recorder):
    maxio = AdvancedBillingApi(api_key="k", site="acme", region="eu", transport=transport)
    maxio.subscriptions.list_subscriptions(per_page=5)
    assert str(recorder.last.url) == "https://acme.ebilling.maxio.com/subscriptions.json?per_page=5"


def test_an_unknown_region_is_refused():
    with pytest.raises(ValueError, match="region"):
        AdvancedBillingApi(api_key="k", site="acme", region="apac")


def test_json_bodies(maxio, recorder):
    maxio.customers.create_customer(body={"customer": {"first_name": "Ada", "email": "a@b.co"}})
    assert recorder.last.method == "POST"
    assert recorder.last.headers["Content-Type"] == "application/json"
    assert json.loads(recorder.last.content) == {
        "customer": {"first_name": "Ada", "email": "a@b.co"}
    }


def test_events_go_to_the_events_host(maxio, recorder):
    maxio.subscription_components.record_event("api_calls", body={"chargify": {"id": 1}})
    assert str(recorder.last.url) == "https://events.chargify.com/acme/events/api_calls.json"
    assert recorder.last.headers["Authorization"] == basic("key_123")
    maxio.subscription_components.list_usages("1", "2")
    assert str(recorder.last.url).startswith("https://acme.chargify.com/")


def test_another_base_url_keeps_every_operation(transport, recorder):
    maxio = AdvancedBillingApi(
        api_key="k", site="acme", base_url="http://localhost:8080", transport=transport
    )
    maxio.subscription_components.record_event("api_calls", body={})
    assert str(recorder.last.url) == "http://localhost:8080/events/api_calls.json"


@pytest.mark.parametrize(("status", "retried"), [(429, True), (500, False), (422, False)])
def test_rate_limits_are_retried(transport, recorder, status, retried):
    maxio = AdvancedBillingApi(api_key="k", site="acme", transport=transport).with_options(
        retries=Retries(attempts=2, sleep=0)
    )
    recorder.respond(httpx.Response(status, json={}), httpx.Response(201, json={}))
    try:
        maxio.customers.create_customer(body={"customer": {"first_name": "Ada"}})
    except UnexpectedResponse:
        pass
    assert len(recorder.requests) == (2 if retried else 1)
