# Saleor Backend Issues

Custom Saleor instance at `http://192.168.31.237:8000/graphql/`
Version: 3.23.7
Reported: 2026-06-18

These issues are on the **Saleor backend side** and block harness certification.
Each issue includes reproduction steps.

---

## Issue S1: `productVariantCreate` returns database error (CRITICAL)

**Severity:** Critical — blocks 18+ certification probes

### Description

All `productVariantCreate` mutations fail with:

```json
{
  "data": null,
  "errors": [{
    "message": "database error",
    "extensions": {
      "code": "provider_error",
      "retryable": false,
      "source": "database",
      "status": 502
    }
  }]
}
```

This happens even with minimal input:

```graphql
mutation {
  productVariantCreate(input: {
    product: "UHJvZHVjdDox",
    sku: "test-sku",
    name: "Test Variant",
    attributes: []
  }) {
    productVariant { id }
    errors { field message code }
  }
}
```

### Impact

- Cannot create any product variants
- Checkout creation fails (requires a variant)
- All storefront checkout probes are blocked
- Scenario `checkout-lifecycle` steps 01-06 are blocked

### Possible causes

1. Missing database migration for the `productVariant` table
2. Missing warehouse/stock table relationship (variant creation may require a warehouse assignment)
3. Product type `Default` (ptp_3680b23dc08746faa257b81780d64acd) has `hasVariants: false`
4. Database permission or constraint issue

### Additional context

- `categoryCreate` works fine
- `collectionCreate` works fine
- `accountRegister` works fine
- `productCreate` works fine (but the created product has no variants)
- Only `productVariantCreate` and `productTypeUpdate` fail with database error

---

## Issue S2: `productTypeUpdate` returns database error

**Severity:** High

### Description

Updating a product type fails with the same database error:

```graphql
mutation {
  productTypeUpdate(
    id: "ptp_3680b23dc08746faa257b81780d64acd",
    input: { hasVariants: true }
  ) {
    productType { id hasVariants }
    errors { field message code }
  }
}
```

Response: `"database error"` with `code: "provider_error"`, status 502.

### Impact

- Cannot enable `hasVariants` on product types
- Cannot modify product type attributes

---

## Issue S3: `warehouseCreate` mutation does not exist

**Severity:** Medium

### Description

The `warehouseCreate` mutation is not available on this Saleor instance:

```graphql
mutation {
  warehouseCreate(input: {
    name: "Test Warehouse",
    slug: "test-wh",
    email: "wh@test.com"
  }) {
    warehouse { id }
    errors { field message }
  }
}
```

Response:
```json
{
  "errors": [{
    "message": "Cannot query field \"warehouseCreate\" on type \"Mutation\". Did you mean \"webhookCreate\", \"categoryCreate\", \"pageTypeCreate\", \"taxClassCreate\" or \"productCreate\"?"
  }]
}
```

### Impact

- Cannot create warehouses
- Stock management features unavailable
- May affect checkout flow if warehouses are required for shipping calculations

---

## Issue S4: `Attribute` type missing `attribute` sub-field

**Severity:** Low

### Description

Querying `productType.variantAttributes.attribute` fails:

```graphql
query {
  productType(id: "ptp_3680b23dc08746faa257b81780d64acd") {
    variantAttributes { attribute { id name } }
  }
}
```

Response:
```json
{
  "errors": [{
    "message": "Cannot query field \"attribute\" on type \"Attribute\"."
  }]
}
```

### Impact

- Cannot introspect product type attribute details
- Harness introspection may produce incorrect schema

---

## Issue S5: `channelCreate` expects String for `currencyCode`

**Severity:** Low

### Description

```graphql
mutation {
  channelCreate(input: {
    name: "Test",
    slug: "test-ch",
    currencyCode: USD,
    defaultCountry: US
  }) {
    channel { id }
    errors { field message }
  }
}
```

Response:
```json
{
  "errors": [{
    "message": "Invalid value for argument \"input.currencyCode\", expected type \"String\""
  }]
}
```

The standard Saleor 3.23.7 schema expects `currencyCode` as an enum,
but this instance expects it as a `String`.

### Impact

- Channel creation with enum syntax fails
- Harness seed may fail to create channels

---

## Issue S6: Product `isPublished: false` by default

**Severity:** Low

### Description

Products created via `productCreate` are not published by default, and
`productChannelListingUpdate` is needed to publish them. The product
`Harness Reference Product` (Product:1) has:

```json
{
  "channelListings": [{
    "channel": { "slug": "default" },
    "isPublished": false,
    "isAvailableForPurchase": false
  }]
}
```

### Impact

- Products not visible in storefront queries filtered by channel
- Checkout may not find products to add to cart

---

## Reproduction steps

1. Start the custom Saleor backend
2. Get a staff token:
   ```graphql
   mutation {
     tokenCreate(email: "merchant@demo.basmalahub.local", password: "changeme") {
       token
     }
   }
   ```
3. Try creating a variant:
   ```graphql
   mutation {
     productVariantCreate(input: {
       product: "UHJvZHVjdDox",
       sku: "test-sku",
       name: "Test Variant",
       attributes: []
     }) {
       productVariant { id }
       errors { field message code }
     }
   }
   ```
4. Observe `database error` response

---

## Environment

- Saleor version: 3.23.7
- GraphQL URL: `http://192.168.31.237:8000/graphql/`
- Admin: `merchant@demo.basmalahub.local` / `changeme`
- Database: Unknown (check Saleor config)
