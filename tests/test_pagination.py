"""The _all methods page as Maxio does (over a mock transport)."""

import httpx
import pytest
from apiroute.testing import MockTransport

from maxio_apiroute.advanced_billing import AdvancedBillingApi


@pytest.fixture
def mock():
    return MockTransport()


@pytest.fixture
def maxio(mock):
    return AdvancedBillingApi(api_key="key_123", site="acme", transport=mock)


def subscriptions(*ids):
    return httpx.Response(200, json=[{"subscription": {"id": i}} for i in ids])


def test_array_lists_page_until_a_short_page(maxio, mock):
    mock.respond(subscriptions(1, 2), subscriptions(3))
    found = [
        s["subscription"]["id"] for s in maxio.subscriptions.list_subscriptions_all(per_page=2)
    ]
    assert found == [1, 2, 3]
    assert [call.params.get("page") for call in mock.calls] == [None, "2"]
    assert all(call.params["per_page"] == "2" for call in mock.calls)
    assert all(call.operation == "listSubscriptions" for call in mock.calls)


def test_without_a_page_size_an_empty_page_ends_the_list(maxio, mock):
    mock.respond(subscriptions(1), subscriptions())
    assert len(list(maxio.subscriptions.list_subscriptions_all())) == 1
    assert len(mock.calls) == 2


def test_object_lists_read_their_items_key(maxio, mock):
    mock.respond(
        httpx.Response(200, json={"invoices": [{"uid": "inv_1"}, {"uid": "inv_2"}]}),
        httpx.Response(200, json={"invoices": [{"uid": "inv_3"}]}),
    )
    uids = [invoice["uid"] for invoice in maxio.invoices.list_invoices_all(per_page=2)]
    assert uids == ["inv_1", "inv_2", "inv_3"]


def test_total_pages_ends_the_list(maxio, mock):
    page = {"total_count": 2, "current_page": 1, "total_pages": 1, "per_page": 20}
    mock.respond(httpx.Response(200, json={**page, "metadata": [{"id": 1}, {"id": 2}]}))
    assert len(list(maxio.custom_fields.list_metadata_all("subscriptions", 7, per_page=20))) == 2
    assert len(mock.calls) == 1


def test_the_one_page_method_is_unchanged(maxio, mock):
    mock.respond(subscriptions(1))
    assert maxio.subscriptions.list_subscriptions(per_page=1) == [{"subscription": {"id": 1}}]
    assert len(mock.calls) == 1
