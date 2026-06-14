# Dynamic Probes — Anti-Static-Response Testing

## Overview

Dynamic probes generate fresh inputs at runtime to prove the target backend
is computing responses, not serving canned golden JSON keyed on operation name.

## How it works

1. At test-run start, the harness generates unique values (UUIDs, slugs, timestamps)
2. These values are injected into GraphQL documents via `{{run_slug}}`, `{{nonce}}`, `{{uuid}}` placeholders
3. After receiving a response, the harness validates that generated values appear in the response
4. If the response does not contain the generated values, it is flagged as a possible static response

## Comparison modes

| Mode | Description |
|------|-------------|
| `echo` | Response must contain the generated runtime values (e.g., product name, slug) |
| `structural` | Response must have expected shape after substituting generated IDs |
| `semantic_error` | Error response must reference the generated input, not a static placeholder |

## Registered dynamic probes

| Probe | Operation | Mode | Why dynamic |
|-------|-----------|------|-------------|
| `dynamic_product_create` | `productCreate` | echo | Unique name/slug must appear in response |
| `dynamic_category_create` | `categoryCreate` | echo | Unique name/slug must appear in response |
| `dynamic_collection_create` | `collectionCreate` | echo | Unique name/slug must appear in response |
| `dynamic_product_not_found` | `product` (query) | semantic_error | Error must reference generated UUID |

## Adding new dynamic probes

Edit `backend/app/services/dynamic_corpus.py` and add to `DYNAMIC_PROBES`:

```python
DynamicProbe(
    probe_id="my_new_probe",
    operation_name="operationName",
    operation_kind="MUTATION",
    category="category",
    document_template='mutation { operationName(input: { name: "{{run_slug}}" }) { ... } }',
    comparison_mode="echo",
    binding_rules=[
        {"field": "data.operationName.result.name", "expected_input": "input.name"},
    ],
    description="Description of what this probe tests",
)
```

## Placeholders

| Placeholder | Replaced with |
|-------------|---------------|
| `{{run_slug}}` | `harness-{run_id}-{nonce}` |
| `{{nonce}}` | 8-char UUID prefix |
| `{{uuid}}` | Full UUID |

## Configuration

Set `SGRC_ALLOW_ASSERTION_ONLY=false` (default) to require golden evidence
for scenario and variant probes. Dynamic probes always validate runtime values.
