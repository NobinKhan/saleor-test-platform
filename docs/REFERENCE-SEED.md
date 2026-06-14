# Reference seed (L3 fixtures)

L3 dashboard bundles replay real GraphQL documents with `{{fixtures.*}}` placeholders (product IDs, order IDs, channel IDs, etc.). Golden capture requires a Saleor database with those entities present.

## What `just seed-reference` does

After `just fresh` (migrate + `populatedb` demo data + admin user), the harness:

1. Queries live Saleor for channel, product, variant, order, customer, collection, warehouse, category IDs
2. Creates a reference customer/collection if still missing
3. Writes `fixtures.json` into the harness **named volume** at `/app/reference/client-bundles/dashboard-{VERSION}/` (not a host bind mount)

## Docker reference storage

The **harness** stack uses **Chainguard Python + Chainguard Postgres** — no host bind mounts for reference data:

- Golden corpus is **baked into** the `harness-backend` image at `/app/reference-baked/`
- On first start, a **named volume** (`harness_reference`) is seeded at `/app/reference/`
- `just patch-corpus`, `just seed-reference`, and `just record-reference` write to that volume

Persist volume changes back to git:

```bash
just export-reference    # docker cp volume → ./reference/
```

After pulling corpus updates from git:

```bash
just import-reference    # rebuild image with new ./reference/
# optional: remove stale volume so entrypoint re-seeds from new image
docker volume rm saleor-test-platform_harness_reference
just up
```

Fixture keys used by dashboard bundles:

| Key | Used for |
|-----|----------|
| `default_channel_id` | Channel-scoped mutations (plugins, reorder warehouses, …) |
| `default_product_id` | Product media, variant reorder, attribute assignment |
| `default_variant_id` | Variant media assign/unassign |
| `default_order_id` | Order discounts, fulfillments, notes, transactions |
| `default_customer_id` | Customer addresses, gift cards, permission groups |
| `default_collection_id` | Collection product assign/unassign/reorder |

## Workflow

```bash
just up
just fresh              # includes populatedb + seed-reference
just patch-corpus --client-bundles all   # after corpus changes
just export-reference    # if you changed golden JSON and want to commit
just baseline
```

Manual re-seed on an existing stack:

```bash
just seed-reference
just patch-corpus --client-bundles all
```

## Certifying external backends

For **`full+client`** certification, the target backend should expose entities matching the seeded fixture IDs — or equivalent records reachable with the same GraphQL variable values after substitution.

If a backend passes L1 (stateless probes) but fails L3 bundles with **missing data** (not SGRC mismatch), seed your backend similarly before claiming certification failure:

- At least one channel, product with variant, customer, order, and collection
- Staff admin with permissions to run dashboard operations

L1 probes do **not** require seeded data; L3 bundles **do**.

## Runtime fixture resolver (certification replay)

At **test-run start** (after staff auth), the harness queries the **target** Saleor and resolves live entity IDs into the same keys as `fixtures.json` (`default_product_id`, `default_variant_id`, `default_channel_id`, …). Static IDs from capture-time `fixtures.json` are used only as fallback when the target has no matching entities.

When **`RUNTIME_SEED=true`** (default in the harness), missing entities are **created via admin mutations** before probes run — channel, product type (if needed), reference product + variant, customer, collection, and checkout. This exercises create mutations on the target and avoids requiring a pre-seeded catalog identical to official Saleor.

Harness reference slugs (idempotent re-runs): `harness-channel`, `harness-reference-type`, `harness-reference-product`, `harness-reference-collection`, `harness-reference-customer@example.com`.

```text
just seed-reference     → capture-time (record L3 golden on official Saleor; writes fixtures.json)
TestRunner.run()        → runtime resolve_fixtures() + optional ensure_runtime_fixture_entities()
POST /api/runs/validate → pre-flight: version gate + same fixture resolution/seed preview
```

Set `RUNTIME_SEED=false` for read-only audits against production-like targets where mutations are not allowed.

### Docker URL rewrite (UI localhost)

When the harness runs inside Docker (`DATABASE_URL` contains `@harness-db:`), the UI may show `http://localhost:8000/graphql/` while Saleor listens on the host. All harness paths — auth, pre-flight (`POST /api/runs/validate`), fixture capture/seed, and `TestRunner` — rewrite localhost to `SALEOR_GRAPHQL_URL` (typically `http://host.docker.internal:8000/graphql/`). The validate response includes `requested_saleor_url` and `resolved_saleor_url` when they differ.

If L3 still fails with **missing data**, check admin permissions for channel/product/customer mutations. See [docs/DYNAMIC-PROBES.md](DYNAMIC-PROBES.md) for anti-static dynamic probes (unique slugs/UUIDs per run).

Short list — full gap analysis (Storefront L3, customer JWT, excluded bundles, runtime limits): **[COVERAGE-GAPS.md](COVERAGE-GAPS.md)**.

Planned corpus work:

- **Storefront L3** — vendor `saleor-storefront`, bundle import/record, storefront fixtures (largest gap for Storefront parity)
- **Customer JWT replay** — customer-context ops under real customer tokens, not staff-only golden
- Dedicated product CRUD scenario chains (create → read → update → delete)
- Dedicated order lifecycle scenario chains
- Stock management L3 parity (`productVariantStocks*`)
- `exportProducts` L1 probe when the mutation exists on the pinned Saleor release (not present on 3.23.7 introspection)

See [COMPATIBILITY.md](COMPATIBILITY.md) for the certification standard.
