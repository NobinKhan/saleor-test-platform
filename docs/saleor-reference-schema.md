# Saleor API Reference — Test Coverage Schema

> **Source of truth for compatibility testing:** the reference corpus at `reference/corpora/saleor-{VERSION}/` (**387** probes for 3.23.7). This document lists the **dashboard catalog** subset (~108 operations after deprecated-op prune). Schema gate in compatibility mode uses the full corpus operation set (**818+** certification endpoints: 387 L1 + 415 L3 dashboard + 16 L3 storefront bundles on Saleor 3.23.7, plus scenarios, variants, and dynamic probes).
>
> When Saleor deprecates or removes an operation, run `just corpus-diff` and `just patch-corpus --apply-diff` (catalog in `test_runner.py` is synced automatically). See [COMPATIBILITY.md](COMPATIBILITY.md). For Storefront L3, customer JWT, and other planned work, see [COVERAGE-GAPS.md](COVERAGE-GAPS.md).

## Query Endpoints (100+)

### Products
| Endpoint | Kind | Public | Description |
|---|---|---|---|
| `products` | QUERY | ✅ | Paginated product list with first/skip |
| `product` | QUERY | ✅ | Single product by ID |
| `productTypes` | QUERY | ✅ | All product type definitions |
| `productType` | QUERY | ✅ | Single product type |

### Orders
| Endpoint | Kind | Public | Description |
|---|---|---|---|
| `orders` | QUERY | ❌ | Paginated order list (staff) |
| `order` | QUERY | ❌ | Single order by ID |
| `ordersDraft` | QUERY | ❌ | Draft orders only |
| `ordersByUser` | QUERY | ❌ | Orders belonging to authenticated user |

### Checkout
| Endpoint | Kind | Public | Description |
|---|---|---|---|
| `checkout` | QUERY | ✅ | Single checkout by token |
| `checkouts` | QUERY | ✅ | All checkouts list |

### Channels
| Endpoint | Kind | Public | Description |
|---|---|---|---|
| `channels` | QUERY | ✅ | All sales channels |
| `channel` | QUERY | ✅ | Single channel by ID |

### Categories
| Endpoint | Kind | Public | Description |
|---|---|---|---|
| `categories` | QUERY | ✅ | Category tree with levels |
| `category` | QUERY | ✅ | Single category |

### Collections
| Endpoint | Kind | Public | Description |
|---|---|---|---|
| `collections` | QUERY | ✅ | Product collections |
| `collection` | QUERY | ✅ | Single collection |

### Attributes
| Endpoint | Kind | Public | Description |
|---|---|---|---|
| `attributes` | QUERY | ✅ | Attribute definitions for filtering |
| `attribute` | QUERY | ✅ | Single attribute |

### Account
| Endpoint | Kind | Public | Description |
|---|---|---|---|
| `me` | QUERY | ❌ | Current authenticated user |
| `users` | QUERY | ❌ | User list (staff) |
| `user` | QUERY | ❌ | Single user |
| `permissionGroups` | QUERY | ❌ | Staff permission groups |

### Gift Cards
| Endpoint | Kind | Public | Description |
|---|---|---|---|
| `giftCards` | QUERY | ❌ | Gift card list |
| `giftCard` | QUERY | ❌ | Single gift card |

### Shipping
| Endpoint | Kind | Public | Description |
|---|---|---|---|
| `shippingZones` | QUERY | ✅ | Shipping zone definitions |
| `shippingZone` | QUERY | ✅ | Single shipping zone |
| `shippingMethods` | QUERY | ✅ | Available shipping methods |

### Payments
| Endpoint | Kind | Public | Description |
|---|---|---|---|
| `payments` | QUERY | ❌ | Payment list |
| `payment` | QUERY | ❌ | Single payment |

### Discounts
| Endpoint | Kind | Public | Description |
|---|---|---|---|
| `sales` | QUERY | ✅ | Sales (percentage/fixed discounts) |
| `sale` | QUERY | ✅ | Single sale |
| `vouchers` | QUERY | ✅ | Voucher codes |
| `voucher` | QUERY | ✅ | Single voucher |
| `promotions` | QUERY | ✅ | Promotion rules engine |

### Warehouse
| Endpoint | Kind | Public | Description |
|---|---|---|---|
| `warehouses` | QUERY | ❌ | Warehouse list |
| `warehouse` | QUERY | ❌ | Single warehouse |

### Shop / Config
| Endpoint | Kind | Public | Description |
|---|---|---|---|
| `shop` | QUERY | ✅ | Global shop settings (domain, version) |
| `paymentGateways` | QUERY | ✅ | Available payment gateways |
| `languages` | QUERY | ✅ | Available translations |

### Pages
| Endpoint | Kind | Public | Description |
|---|---|---|---|
| `pages` | QUERY | ✅ | CMS pages |
| `page` | QUERY | ✅ | Single page |

### Plugins
| Endpoint | Kind | Public | Description |
|---|---|---|---|
| `plugins` | QUERY | ❌ | Active plugins |
| `plugin` | QUERY | ❌ | Single plugin |

### Webhooks
| Endpoint | Kind | Public | Description |
|---|---|---|---|
| `webhookEvents` | QUERY | ❌ | Available webhook event types |

---

## Mutation Endpoints (80+)

### Products
| Mutation | Kind | Public | Description |
|---|---|---|---|
| `productCreate` | MUTATION | ❌ | Create product |
| `productUpdate` | MUTATION | ❌ | Update product |
| `productDelete` | MUTATION | ❌ | Delete product |
| `productVariantCreate` | MUTATION | ❌ | Create variant |
| `productVariantUpdate` | MUTATION | ❌ | Update variant |
| `productVariantDelete` | MUTATION | ❌ | Delete variant |
| `productTypeCreate` | MUTATION | ❌ | Create product type |
| `productTypeUpdate` | MUTATION | ❌ | Update product type |
| `productTypeDelete` | MUTATION | ❌ | Delete product type |

### Orders
| Mutation | Kind | Public | Description |
|---|---|---|---|
| `orderCreate` | MUTATION | ❌ | Create order |
| `orderUpdate` | MUTATION | ❌ | Update order |
| `orderDelete` | MUTATION | ❌ | Delete order |
| `orderConfirm` | MUTATION | ❌ | Confirm order |
| `orderCancel` | MUTATION | ❌ | Cancel order |
| `orderFulfill` | MUTATION | ❌ | Mark as fulfilled |
| `orderRefund` | MUTATION | ❌ | Refund order |
| `orderLineDelete` | MUTATION | ❌ | Remove line item |
| `orderLineUpdate` | MUTATION | ❌ | Update line item |
| `orderLineAdd` | MUTATION | ❌ | Add line item |

### Checkout
| Mutation | Kind | Public | Description |
|---|---|---|---|
| `checkoutCreate` | MUTATION | ✅ | Create checkout |
| `checkoutUpdate` | MUTATION | ✅ | Update checkout |
| `checkoutDelete` | MUTATION | ❌ | Delete checkout |
| `checkoutComplete` | MUTATION | ✅ | Complete checkout |
| `checkoutAddPromoCode` | MUTATION | ✅ | Apply promo code |
| `checkoutRemovePromoCode` | MUTATION | ✅ | Remove promo code |
| `checkoutEmailUpdate` | MUTATION | ✅ | Update email |
| `checkoutShippingAddressUpdate` | MUTATION | ✅ | Update shipping address |
| `checkoutShippingMethodUpdate` | MUTATION | ✅ | Select shipping method |
| `checkoutPaymentCreate` | MUTATION | ✅ | Create payment |

### Channels
| Mutation | Kind | Public | Description |
|---|---|---|---|
| `channelCreate` | MUTATION | ❌ | Create channel |
| `channelUpdate` | MUTATION | ❌ | Update channel |
| `channelDelete` | MUTATION | ❌ | Delete channel |

### Categories
| Mutation | Kind | Public | Description |
|---|---|---|---|
| `categoryCreate` | MUTATION | ❌ | Create category |
| `categoryUpdate` | MUTATION | ❌ | Update category |
| `categoryDelete` | MUTATION | ❌ | Delete category |

### Collections
| Mutation | Kind | Public | Description |
|---|---|---|---|
| `collectionCreate` | MUTATION | ❌ | Create collection |
| `collectionUpdate` | MUTATION | ❌ | Update collection |
| `collectionDelete` | MUTATION | ❌ | Delete collection |
| `collectionAddProducts` | MUTATION | ❌ | Add products |
| `collectionRemoveProducts` | MUTATION | ❌ | Remove products |

### Attributes
| Mutation | Kind | Public | Description |
|---|---|---|---|
| `attributeCreate` | MUTATION | ❌ | Create attribute |
| `attributeUpdate` | MUTATION | ❌ | Update attribute |
| `attributeDelete` | MUTATION | ❌ | Delete attribute |

### Account
| Mutation | Kind | Public | Description |
|---|---|---|---|
| `accountRegister` | MUTATION | ✅ | Register new user |
| `accountUpdate` | MUTATION | ❌ | Update account |
| `accountRequestDeletion` | MUTATION | ❌ | Request account deletion |
| `confirmAccount` | MUTATION | ✅ | Confirm email |
| `requestPasswordReset` | MUTATION | ✅ | Request password reset |
| `resetPassword` | MUTATION | ✅ | Reset with token |
| `passwordChange` | MUTATION | ❌ | Change password |

### Gift Cards
| Mutation | Kind | Public | Description |
|---|---|---|---|
| `giftCardCreate` | MUTATION | ❌ | Create gift card |
| `giftCardUpdate` | MUTATION | ❌ | Update gift card |
| `giftCardDelete` | MUTATION | ❌ | Delete gift card |
| `giftCardResend` | MUTATION | ❌ | Resend email |

### Shipping
| Mutation | Kind | Public | Description |
|---|---|---|---|
| `shippingZoneCreate` | MUTATION | ❌ | Create shipping zone |
| `shippingZoneUpdate` | MUTATION | ❌ | Update shipping zone |
| `shippingZoneDelete` | MUTATION | ❌ | Delete shipping zone |
| `shippingMethodCreate` | MUTATION | ❌ | Create shipping method |
| `shippingMethodUpdate` | MUTATION | ❌ | Update shipping method |
| `shippingMethodDelete` | MUTATION | ❌ | Delete shipping method |

### Payments
| Mutation | Kind | Public | Description |
|---|---|---|---|
| `paymentInitialize` | MUTATION | ❌ | Initialize payment |
| `paymentCapture` | MUTATION | ❌ | Capture payment |
| `paymentRefund` | MUTATION | ❌ | Refund payment |
| `paymentVoid` | MUTATION | ❌ | Void payment |

### Discounts
| Mutation | Kind | Public | Description |
|---|---|---|---|
| `saleCreate` | MUTATION | ❌ | Create sale |
| `saleUpdate` | MUTATION | ❌ | Update sale |
| `saleDelete` | MUTATION | ❌ | Delete sale |
| `voucherCreate` | MUTATION | ❌ | Create voucher |
| `voucherUpdate` | MUTATION | ❌ | Update voucher |
| `voucherDelete` | MUTATION | ❌ | Delete voucher |
| `promotionCreate` | MUTATION | ❌ | Create promotion |
| `promotionUpdate` | MUTATION | ❌ | Update promotion |
| `promotionDelete` | MUTATION | ❌ | Delete promotion |

### Warehouse
| Mutation | Kind | Public | Description |
|---|---|---|---|
| `warehouseCreate` | MUTATION | ❌ | Create warehouse |
| `warehouseUpdate` | MUTATION | ❌ | Update warehouse |
| `warehouseDelete` | MUTATION | ❌ | Delete warehouse |

### Pages
| Mutation | Kind | Public | Description |
|---|---|---|---|
| `pageCreate` | MUTATION | ❌ | Create page |
| `pageUpdate` | MUTATION | ❌ | Update page |
| `pageDelete` | MUTATION | ❌ | Delete page |

### Shop
| Mutation | Kind | Public | Description |
|---|---|---|---|
| `shopDomainUpdate` | MUTATION | ❌ | Update shop domain |
| `shopSettingsUpdate` | MUTATION | ❌ | Update shop settings |
| `shopAddressUpdate` | MUTATION | ❌ | Update shop address |

### Webhooks
| Mutation | Kind | Public | Description |
|---|---|---|---|
| `webhookCreate` | MUTATION | ❌ | Create webhook |
| `webhookUpdate` | MUTATION | ❌ | Update webhook |
| `webhookDelete` | MUTATION | ❌ | Delete webhook |

### Metadata
| Mutation | Kind | Public | Description |
|---|---|---|---|
| `updateMetadata` | MUTATION | ❌ | Update public metadata |
| `deleteMetadata` | MUTATION | ❌ | Delete public metadata |
| `updatePrivateMetadata` | MUTATION | ❌ | Update private metadata |
| `deletePrivateMetadata` | MUTATION | ❌ | Delete private metadata |

---

## Reference baseline

The harness compares each target API against a **static catalog** aligned with **Saleor Dashboard 3.23.6** (see `REFERENCE_BASELINE_VERSION` / `REFERENCE_BASELINE_SOURCE`). This is a dashboard-style compatibility check, not a live clone of every dashboard GraphQL document.

## Test Result Classification

| Status | Meaning | HTTP/GraphQL Criteria |
|---|---|---|
| `pass` | Available | HTTP 200, success or acceptable probe (e.g. not-found on placeholder IDs) |
| `fail` | Missing/Broken | HTTP non-200, timeout, or schema error (undefined field/type) |
| `warn` | Expected friction | Auth denied, or mutation/validation errors on dummy probe input |
| `skip` | Skipped | Run stopped or endpoint skipped |

### Outcome labels (Phase A)

| Outcome | Typical status | Meaning |
|---|---|---|
| `success_with_data` | pass | HTTP 200, `data` present, no errors |
| `schema_error` | fail | Field/type missing vs reference schema |
| `auth_denied` | warn | Permission or JWT error |
| `validation_error` | warn | Business/validation error on dummy mutation input |
| `not_found_probe` | pass | Resource not found — acceptable for probe IDs |
| `http_error` | fail | Non-200 HTTP |
| `timeout` | fail | Request timed out |
| `unexpected_error` | pass/warn | Other GraphQL error (classified conservatively) |

## Key GraphQL Error Codes
| Code | Meaning |
|---|---|
| `permission` | User lacks permission |
| `authentication` | Not authenticated |
| `forbidden` | Forbidden access |
| `jwt-error` | JWT token problem |
| `not found` | Resource doesn't exist — passes if error is just "not found" |

## Saleor Version Detection
Test runner queries `shop { version }` to detect Saleor version and records it on the TestRun for report comparison across versions.