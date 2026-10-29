# maxio-apiroute

[![Build](https://github.com/dougyouch/maxio-apiroute/actions/workflows/build.yml/badge.svg)](https://github.com/dougyouch/maxio-apiroute/actions/workflows/build.yml)
[![Release](https://github.com/dougyouch/maxio-apiroute/actions/workflows/release.yml/badge.svg)](https://github.com/dougyouch/maxio-apiroute/actions/workflows/release.yml)

A Python client for [Maxio Advanced Billing](https://developers.maxio.com/http/getting-started/overview), the subscription billing API formerly known as Chargify. It's generated with [apiroute](https://github.com/dougyouch/apiroute) from the OpenAPI spec that Maxio's developer portal publishes, and a weekly build keeps it current. Sections and methods carry the spec's names, the same ones Maxio's own SDKs use: `maxio.subscriptions.list_subscriptions()`, `maxio.customers.create_customer(...)`, `maxio.invoices.read_invoice(uid)`.

- **Two layers:** every call works with plain dicts (`maxio.customers.read_customer(123)`). Under `.models`, calls take and return typed pydantic models (`maxio.customers.models.read_customer(123)`).
- **Sync and async:** add `.aio` to any call for the async version.
- **Lazy loading:** only the sections and models you use get imported. The client covers all 285 operations and about 1,100 models, and importing it takes about a seventh of a second.
- **Typed:** the package ships `py.typed`.

## Installation

```bash
pip install maxio-apiroute    # or: uv add maxio-apiroute
```

It needs Python 3.10 or newer.

## Usage

```python
import os
from maxio_apiroute.advanced_billing import AdvancedBillingApi

maxio = AdvancedBillingApi(api_key=os.environ["MAXIO_API_KEY"], site="acme")  # acme.chargify.com

customer = maxio.customers.create_customer(  # a dict
    body={"customer": {"first_name": "Ada", "last_name": "Lovelace", "email": "ada@example.com"}}
)
found = maxio.customers.models.read_customer(customer["customer"]["id"])  # CustomerResponse
print(found.customer.email)

subscription = maxio.subscriptions.models.create_subscription(
    body={"subscription": {"product_handle": "pro", "customer_id": found.customer.id}}
)
page = maxio.subscriptions.list_subscriptions(state="active", per_page=50)
for item in maxio.subscriptions.models.list_subscriptions_all(per_page=200):  # every page
    print(item.subscription.id, item.subscription.state)
invoice = await maxio.invoices.models.aio.read_invoice("inv_8gk5bwkct3gqt")
```

- **Request and response bodies** are JSON, wrapped the way Maxio wraps them: `{"customer": {...}}` in and out, and a list of `[{"subscription": {...}}, ...]` from most list calls.
- **Sections follow the API reference:** `maxio.subscriptions`, `maxio.subscription_components`, `maxio.customers`, `maxio.products`, `maxio.product_price_points`, `maxio.invoices`, `maxio.coupons`, `maxio.payment_profiles`, `maxio.webhooks`, and so on: 43 sections.
- **Pagination:** list operations have a `_all` twin (`list_subscriptions_all`, `list_invoices_all`, `list_customers_all` …). It takes the same arguments and iterates every page's items, counting up `page` until a short or empty page (or the `total_pages` that some lists return). `async for` works through `.aio`, `.pages()` gives whole pages, and `itertools.islice` or `break` stops early. Pass `per_page` so that a short page ends the list without one more request. [`specs/advanced_billing.pagination.yaml`](specs/advanced_billing.pagination.yaml) sets which operations get one.
- **Event ingestion** (`subscription_components.record_event`, `bulk_record_events`) goes to `events.chargify.com/<site>`, as Maxio requires.
- **Errors** raise `apiroute.UnexpectedResponse`, whose `.response` carries Maxio's error body.

### Keys and sites

| Argument | |
| --- | --- |
| `api_key` | A site's API key, or a function returning the current one. It's sent as the Basic auth username, with `x` as the password. See Maxio's [API keys guide](https://docs.maxio.com/configuration/advanced-billing/advanced-billing-api-keys) and [authentication](https://developers.maxio.com/http/introduction/authentication). |
| `site` | The site's subdomain: `acme` for `acme.chargify.com`. Use a [test site](https://docs.maxio.com/configuration/advanced-billing/sites/testing-overview) for development. |
| `region` | `"us"` (the default) or `"eu"` for sites hosted in the EU (`acme.ebilling.maxio.com`). |
| `base_url` | Another host, such as a proxy or a mock server. Every operation then goes there, event ingestion included. |

### Retries

Retries are off unless you turn them on, for example with `maxio.with_options(retries=3)`, or with `retries = Retries(...)` in a subclass. Once on, they cover connection failures and `429` rate limiting for every call, waiting at least as long as a `Retry-After` header asks. A read timeout is retried only for `GET`s, because a repeated `POST` could create a second subscription or charge.

For transports, timeouts and other client options, see [apiroute's README](https://github.com/dougyouch/apiroute#readme).

## APIs

<!-- apis:start -->
| API | Import | Docs |
| --- | --- | --- |
| Maxio Advanced Billing API (formerly Chargify) | `from maxio_apiroute.advanced_billing import AdvancedBillingApi` | [docs](https://developers.maxio.com/http/getting-started/overview) |
<!-- apis:end -->

## How this repository stays up to date

Nothing under `src/maxio_apiroute/` is written by hand except `auth.py` and `__init__.py`. Everything else is generated from the spec listed in [`apis.yaml`](apis.yaml):

1. Every Monday, the **[Build](.github/workflows/build.yml)** workflow:
   - Upgrades apiroute to its newest release.
   - Downloads Maxio's OpenAPI 3.1 export into [`specs/`](specs).
   - Regenerates the client with `apiroute generate --pagination`.
   - Runs the lint and tests, then the live tests against a Maxio test site.
2. If anything changed, it commits the result to `main`:
   - `feat(specs): ...` when Maxio changed its spec, which produces a minor release.
   - `fix(codegen): ...` when only a newer apiroute changed the generated code, which produces a patch release.
3. **[Release](.github/workflows/release.yml)** then tests the commit, adds it to [CHANGELOG.md](CHANGELOG.md), tags it, publishes the new version to [PyPI](https://pypi.org/project/maxio-apiroute/) and creates a [GitHub release](https://github.com/dougyouch/maxio-apiroute/releases). No one has to do anything, and every merge to main releases the same way.

[CI](.github/workflows/ci.yml) checks every pull request and every release. It lints, runs the tests on Python 3.10 to 3.14, and regenerates from the committed spec to confirm that the committed code matches it exactly.

Because `specs/` is committed, `git log -p specs/` shows exactly what Maxio changed and when.

## Development

```bash
uv sync
uv run python scripts/generate.py --fetch   # download the latest spec, regenerate
uv run python scripts/generate.py           # regenerate from the committed spec
uv run pytest
MAXIO_API_KEY=... MAXIO_SITE=acme-test uv run pytest tests/live   # against a test site
uv run ruff check . && uv run ruff format --check .
```

The live tests create a few customers and delete them. They refuse to run against a site whose `test` flag isn't set.

## License

MIT
