# Saleor API Compatibility Report

## Purpose
This report compares a target GraphQL API against the official Saleor 3.23.7 reference.
 Test mode: **compatibility** (golden input replay).

## Version glossary
| Label | Value | Meaning |
|-------|-------|---------|
| Target API | 3.23.7 @ http://localhost:8000/graphql/ | Version from `shop { version }` on server under test |
| Catalog baseline | saleor-dashboard 3.23.6 | Static list of operation names we probe |
| Golden corpus | 3.23.7 (414 probes) | Recorded request/response from official Saleor |

## Executive summary
- **Compatibility score** (primary): **88.2%**
- Schema gate: **FAIL** (missing 10 queries, 16 mutations)
- Certified Saleor-compatible: **NO** (requires schema gate + compatibility ≥ 95%)
- Probe outcome rate (informational): **4.3%** returned success-class responses (18/414)
- Incompatible: 49, Warnings: 0, Compatible: 365
- Golden: 365 matched, 49 mismatched, 0 missing

## Schema drift
- Missing queries (10): ordersDraft, languages, users, webhookEvents, paymentGateways, shippingMethods, sales, sale, ordersByUser, meta
- Missing mutations (16): shippingMethodUpdate, warehouseDelete, saleDelete, checkoutUpdate, saleCreate, warehouseUpdate, saleUpdate, orderCreate, resetPassword, shippingMethodCreate (+6 more)
- Extra queries (43): _entities, _service, address, addressValidationRules, app, appExtension, appExtensions, apps, appsInstallations, checkoutLines (+33 more)
- Extra mutations (237): accountAddressCreate, accountAddressDelete, accountAddressUpdate, accountDelete, accountSetDefaultAddress, addressCreate, addressDelete, addressSetDefault, addressUpdate, appActivate (+227 more)

## Behavioral mismatches (action required)

### transaction (QUERY)
- Status: fail, Match: mismatch, Outcome: auth_error
- Diff: Expected family not_found (not_found), got rejection (auth_error)
- **Request:**
```graphql
query { transaction(id: "00000000-0000-0000-0000-000000000000") { id } }
```
- **Expected (golden):**
```json
{
  "errors": [
    {
      "message": "Invalid ID: 00000000-0000-0000-0000-000000000000. Expected: TransactionItem.",
      "locations": [
        {
          "line": 1,
          "column": 9
        }
      ],
      "path": [
        "transaction"
      ],
      "extensions": {
        "exception": {
          "code": "GraphQLError",
          "stacktrace": [
            "Traceback (most recent call last):",
            "  File \"/app/saleor/graphql/core/utils/__init__.py\", line 80, in from_global_id_or_error",
            "    type_, id_ = graphene.Node.from_global_id(global_id)",
            "                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/usr/local/lib/python3.12/site-packages/graphene/relay/node.py\", line 115, in from_global_id",
            "    return from_global_id(global_id)",
            "           ^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/usr/local/lib/python3.12/site-packages/graphql_relay/node/node.py\", line 66, in from_global_id",
            "    unbased_global_id = unbase64(global_id)",
            "                        ^^^^^^^^^^^^^^^^^^^",
            "  File \"/usr/local/lib/python3.12/site-packages/graphql_relay/utils.py\", line 11, in unbase64",
            "    return _unbase64(s).decode('utf-8')",
            "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "UnicodeDecodeError: 'utf-8' codec can't decode byte 0xd3 in position 0: invalid continuation byte",
            "",
            "The above exception was the direct cause of the following exception:",
            "Traceback (most recent call last):",
            "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executor.py\", line 452, in resolve_or_error",
            "    return executor.execute(resolve_fn, source, info, **args)",
            "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executors/sync.py\", line 16, in execute",
            "    return fn(*args, **kwargs)",
            "           ^^^^^^^^^^^^^^^^^^^",
            "  File \"/app/saleor/graphql/decorators.py\", line 32, in wrapper",
            "    return func(info.context, *args, **kwargs)",
            "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/app/saleor/graphql/decorators.py\", line 47, in wrapper",
            "    return f(*args, **kwargs)",
            "           ^^^^^^^^^^^^^^^^^^",
            "  File \"/app/saleor/graphql/payment/schema.py\", line 146, in resolve_transaction",
            "    _, id = from_global_id_or_error(",
            "            ^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/app/saleor/graphql/core/utils/__init__.py\", line 87, in from_global_id_or_error",
            "    raise GraphQLError(",
            "graphql.error.base.GraphQLError: Invalid ID: 00000000-0000-0000-0000-000000000000. Expected: TransactionItem."
          ]
        }
      }
    }
  ],
  "data": {
    "transaction": null
  },
  "extensions": {
    "cost": {
      "requestedQueryCost": 0,
      "maximumAvailable": 50000
    }
  }
}
```
- **Actual:**
```json
{"errors": [{"message": "Invalid token. Create new one by using tokenCreate mutation.", "locations": [{"line": 1, "column": 9}], "path": ["transaction"], "extensions": {"exception": {"code": "InvalidTokenError", "stacktrace": ["Traceback (most recent call last):", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executor.py\", line 452, in resolve_or_error", "    return executor.execute(resolve_fn, source, info, **args)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executors/sync.py\", line 16, in execute", "    return fn(*args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/decorators.py\", line 32, in wrapper", "    return func(info.context, *args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/decorators.py\", line 46, in wrapper", "    test_func(context)", "  File \"/app/saleor/graphql/decorators.py\", line 86, in check_perms", "    if not one_of_permissions_or_auth_filter_required(context, perms):", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 42, in one_of_permissions_or_auth_filter_required", "    perm_results = _get_result_of_permissions_checks(context, permissions)", "                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 60, in _get_result_of_permissions_checks", "    if requestor and permissions:", "       ^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 251, in inner", "    self._setup()", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 404, in _setup", "    self._wrapped = self._setupfunc()", "                    ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 94, in user", "    return get_user(request) or None", "           ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 84, in get_user", "    request._cached_user = cast(User | None, authenticate(request=request))", "                                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/views/decorators/debug.py\", line 75, in sensitive_variables_wrapper", "    return func(*func_args, **func_kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/contrib/auth/__init__.py\", line 114, in authenticate", "    user = backend.authenticate(request, **credentials)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 51, in authenticate", "    return load_user_from_request(request)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 151, in load_user_from_request", "    raise jwt.InvalidTokenError(", "jwt.exceptions.InvalidTokenError: Invalid token. Create new one by using tokenCreate mutation."]}}}], "data": {"transaction": null}, "extensions": {"cost": {"requestedQueryCost": 0, "maximumAvailable": 50000}}}
```
- Error: Invalid token. Create new one by using tokenCreate mutation.

### transactions (QUERY)
- Status: fail, Match: mismatch, Outcome: auth_error
- Diff: Expected family success (success), got rejection (auth_error)
- **Request:**
```graphql
query { transactions(first: 1) { edges { node { id } } } }
```
- **Expected (golden):**
```json
{
  "data": {
    "transactions": {
      "edges": []
    }
  },
  "extensions": {
    "cost": {
      "requestedQueryCost": 0,
      "maximumAvailable": 50000
    }
  }
}
```
- **Actual:**
```json
{"errors": [{"message": "Invalid token. Create new one by using tokenCreate mutation.", "locations": [{"line": 1, "column": 9}], "path": ["transactions"], "extensions": {"exception": {"code": "InvalidTokenError", "stacktrace": ["Traceback (most recent call last):", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executor.py\", line 452, in resolve_or_error", "    return executor.execute(resolve_fn, source, info, **args)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executors/sync.py\", line 16, in execute", "    return fn(*args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/core/fields.py\", line 158, in new_resolver", "    return wrapped_resolver(obj, info, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/decorators.py\", line 32, in wrapper", "    return func(info.context, *args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/decorators.py\", line 46, in wrapper", "    test_func(context)", "  File \"/app/saleor/graphql/decorators.py\", line 86, in check_perms", "    if not one_of_permissions_or_auth_filter_required(context, perms):", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 42, in one_of_permissions_or_auth_filter_required", "    perm_results = _get_result_of_permissions_checks(context, permissions)", "                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 60, in _get_result_of_permissions_checks", "    if requestor and permissions:", "       ^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 251, in inner", "    self._setup()", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 404, in _setup", "    self._wrapped = self._setupfunc()", "                    ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 94, in user", "    return get_user(request) or None", "           ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 84, in get_user", "    request._cached_user = cast(User | None, authenticate(request=request))", "                                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/views/decorators/debug.py\", line 75, in sensitive_variables_wrapper", "    return func(*func_args, **func_kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/contrib/auth/__init__.py\", line 114, in authenticate", "    user = backend.authenticate(request, **credentials)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 51, in authenticate", "    return load_user_from_request(request)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 151, in load_user_from_request", "    raise jwt.InvalidTokenError(", "jwt.exceptions.InvalidTokenError: Invalid token. Create new one by using tokenCreate mutation."]}}}], "data": {"transactions": null}, "extensions": {"cost": {"requestedQueryCost": 0, "maximumAvailable": 50000}}}
```
- Error: Invalid token. Create new one by using tokenCreate mutation.

### app (QUERY)
- Status: fail, Match: mismatch, Outcome: auth_error
- Diff: Expected family not_found (not_found), got rejection (auth_error)
- **Request:**
```graphql
query { app(id: "00000000-0000-0000-0000-000000000000") { id } }
```
- **Expected (golden):**
```json
{
  "errors": [
    {
      "message": "Invalid ID: 00000000-0000-0000-0000-000000000000. Expected: App.",
      "locations": [
        {
          "line": 1,
          "column": 9
        }
      ],
      "path": [
        "app"
      ],
      "extensions": {
        "exception": {
          "code": "GraphQLError",
          "stacktrace": [
            "Traceback (most recent call last):",
            "  File \"/app/saleor/graphql/core/utils/__init__.py\", line 80, in from_global_id_or_error",
            "    type_, id_ = graphene.Node.from_global_id(global_id)",
            "                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/usr/local/lib/python3.12/site-packages/graphene/relay/node.py\", line 115, in from_global_id",
            "    return from_global_id(global_id)",
            "           ^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/usr/local/lib/python3.12/site-packages/graphql_relay/node/node.py\", line 66, in from_global_id",
            "    unbased_global_id = unbase64(global_id)",
            "                        ^^^^^^^^^^^^^^^^^^^",
            "  File \"/usr/local/lib/python3.12/site-packages/graphql_relay/utils.py\", line 11, in unbase64",
            "    return _unbase64(s).decode('utf-8')",
            "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "UnicodeDecodeError: 'utf-8' codec can't decode byte 0xd3 in position 0: invalid continuation byte",
            "",
            "The above exception was the direct cause of the following exception:",
            "Traceback (most recent call last):",
            "  File \"/usr/local/lib/python3.12/site-packages/promise/promise.py\", line 87, in try_catch",
            "    return (handler(*args, **kwargs), None)",
            "            ^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/app/saleor/graphql/app/schema.py\", line 147, in resolve_app",
            "    return resolve_app(info, id)",
            "           ^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/app/saleor/graphql/app/resolvers.py\", line 64, in resolve_app",
            "    _, id = from_global_id_or_error(id, \"App\")",
            "            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/app/saleor/graphql/core/utils/__init__.py\", line 87, in from_global_id_or_error",
            "    raise GraphQLError(",
            "graphql.error.base.GraphQLError: Invalid ID: 00000000-0000-0000-0000-000000000000. Expected: App."
          ]
        }
      }
    }
  ],
  "data": {
    "app": null
  },
  "extensions": {
    "cost": {
      "requestedQueryCost": 1,
      "maximumAvailable": 50000
    }
  }
}
```
- **Actual:**
```json
{"errors": [{"message": "Invalid token. Create new one by using tokenCreate mutation.", "locations": [{"line": 1, "column": 9}], "path": ["app"], "extensions": {"exception": {"code": "InvalidTokenError", "stacktrace": ["Traceback (most recent call last):", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executor.py\", line 452, in resolve_or_error", "    return executor.execute(resolve_fn, source, info, **args)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executors/sync.py\", line 16, in execute", "    return fn(*args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/decorators.py\", line 32, in wrapper", "    return func(info.context, *args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/decorators.py\", line 46, in wrapper", "    test_func(context)", "  File \"/app/saleor/graphql/decorators.py\", line 86, in check_perms", "    if not one_of_permissions_or_auth_filter_required(context, perms):", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 42, in one_of_permissions_or_auth_filter_required", "    perm_results = _get_result_of_permissions_checks(context, permissions)", "                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 60, in _get_result_of_permissions_checks", "    if requestor and permissions:", "       ^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 251, in inner", "    self._setup()", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 404, in _setup", "    self._wrapped = self._setupfunc()", "                    ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 94, in user", "    return get_user(request) or None", "           ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 84, in get_user", "    request._cached_user = cast(User | None, authenticate(request=request))", "                                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/views/decorators/debug.py\", line 75, in sensitive_variables_wrapper", "    return func(*func_args, **func_kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/contrib/auth/__init__.py\", line 114, in authenticate", "    user = backend.authenticate(request, **credentials)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 51, in authenticate", "    return load_user_from_request(request)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 151, in load_user_from_request", "    raise jwt.InvalidTokenError(", "jwt.exceptions.InvalidTokenError: Invalid token. Create new one by using tokenCreate mutation."]}}}], "data": {"app": null}, "extensions": {"cost": {"requestedQueryCost": 1, "maximumAvailable": 50000}}}
```
- Error: Invalid token. Create new one by using tokenCreate mutation.

### appTokenVerify (MUTATION)
- Status: fail, Match: mismatch, Outcome: auth_error
- Diff: Expected family success (success), got rejection (auth_error)
- **Request:**
```graphql
mutation { appTokenVerify(token: "test") { errors { field message } } }
```
- **Expected (golden):**
```json
{
  "data": {
    "appTokenVerify": {
      "errors": []
    }
  },
  "extensions": {
    "cost": {
      "requestedQueryCost": 0,
      "maximumAvailable": 50000
    }
  }
}
```
- **Actual:**
```json
{"errors": [{"message": "Invalid token. Create new one by using tokenCreate mutation.", "locations": [{"line": 1, "column": 12}], "path": ["appTokenVerify"], "extensions": {"exception": {"code": "InvalidTokenError", "stacktrace": ["Traceback (most recent call last):", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executor.py\", line 452, in resolve_or_error", "    return executor.execute(resolve_fn, source, info, **args)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executors/sync.py\", line 16, in execute", "    return fn(*args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/contextlib.py\", line 81, in inner", "    return func(*args, **kwds)", "           ^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/core/mutations.py\", line 520, in mutate", "    setup_context_user(info.context)", "  File \"/app/saleor/graphql/core/context.py\", line 66, in setup_context_user", "    context.user._setup()  # type: ignore[union-attr]", "    ^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 404, in _setup", "    self._wrapped = self._setupfunc()", "                    ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 94, in user", "    return get_user(request) or None", "           ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 84, in get_user", "    request._cached_user = cast(User | None, authenticate(request=request))", "                                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/views/decorators/debug.py\", line 75, in sensitive_variables_wrapper", "    return func(*func_args, **func_kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/contrib/auth/__init__.py\", line 114, in authenticate", "    user = backend.authenticate(request, **credentials)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 51, in authenticate", "    return load_user_from_request(request)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 151, in load_user_from_request", "    raise jwt.InvalidTokenError(", "jwt.exceptions.InvalidTokenError: Invalid token. Create new one by using tokenCreate mutation."]}}}], "data": {"appTokenVerify": null}, "extensions": {"cost": {"requestedQueryCost": 0, "maximumAvailable": 50000}}}
```
- Error: Invalid token. Create new one by using tokenCreate mutation.

### pages (QUERY)
- Status: fail, Match: mismatch, Outcome: auth_error
- Diff: Expected family success (success), got rejection (auth_error)
- **Request:**
```graphql
query { pages(first: 1) { edges { node { id } } } }
```
- **Expected (golden):**
```json
{
  "data": {
    "pages": {
      "edges": []
    }
  },
  "extensions": {
    "cost": {
      "requestedQueryCost": 1,
      "maximumAvailable": 50000
    }
  }
}
```
- **Actual:**
```json
{"errors": [{"message": "Invalid token. Create new one by using tokenCreate mutation.", "locations": [{"line": 1, "column": 9}], "path": ["pages"], "extensions": {"exception": {"code": "InvalidTokenError", "stacktrace": ["Traceback (most recent call last):", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executor.py\", line 452, in resolve_or_error", "    return executor.execute(resolve_fn, source, info, **args)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executors/sync.py\", line 16, in execute", "    return fn(*args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/core/fields.py\", line 158, in new_resolver", "    return wrapped_resolver(obj, info, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/page/schema.py\", line 137, in resolve_pages", "    return _resolve_pages(channel_instance=None)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/page/schema.py\", line 123, in _resolve_pages", "    qs = resolve_pages(info, channel_slug=channel, channel=channel_instance)", "         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/page/resolvers.py\", line 53, in resolve_pages", "    ).visible_to_user(requestor)", "      ^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/page/models.py\", line 20, in visible_to_user", "    if requestor and requestor.has_perm(PagePermissions.MANAGE_PAGES):", "       ^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 251, in inner", "    self._setup()", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 404, in _setup", "    self._wrapped = self._setupfunc()", "                    ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 94, in user", "    return get_user(request) or None", "           ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 84, in get_user", "    request._cached_user = cast(User | None, authenticate(request=request))", "                                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/views/decorators/debug.py\", line 75, in sensitive_variables_wrapper", "    return func(*func_args, **func_kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/contrib/auth/__init__.py\", line 114, in authenticate", "    user = backend.authenticate(request, **credentials)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 51, in authenticate", "    return load_user_from_request(request)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 151, in load_user_from_request", "    raise jwt.InvalidTokenError(", "jwt.exceptions.InvalidTokenError: Invalid token. Create new one by using tokenCreate mutation."]}}}], "data": {"pages": null}, "extensions": {"cost": {"requestedQueryCost": 1, "maximumAvailable": 50000}}}
```
- Error: Invalid token. Create new one by using tokenCreate mutation.

### shippingZone (QUERY)
- Status: fail, Match: mismatch, Outcome: auth_error
- Diff: Expected family not_found (not_found), got rejection (auth_error)
- **Request:**
```graphql
query { shippingZone(id: "00000000-0000-0000-0000-000000000000") { id } }
```
- **Expected (golden):**
```json
{
  "errors": [
    {
      "message": "Invalid ID: 00000000-0000-0000-0000-000000000000. Expected: ShippingZone.",
      "locations": [
        {
          "line": 1,
          "column": 9
        }
      ],
      "path": [
        "shippingZone"
      ],
      "extensions": {
        "exception": {
          "code": "GraphQLError",
          "stacktrace": [
            "Traceback (most recent call last):",
            "  File \"/app/saleor/graphql/core/utils/__init__.py\", line 80, in from_global_id_or_error",
            "    type_, id_ = graphene.Node.from_global_id(global_id)",
            "                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/usr/local/lib/python3.12/site-packages/graphene/relay/node.py\", line 115, in from_global_id",
            "    return from_global_id(global_id)",
            "           ^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/usr/local/lib/python3.12/site-packages/graphql_relay/node/node.py\", line 66, in from_global_id",
            "    unbased_global_id = unbase64(global_id)",
            "                        ^^^^^^^^^^^^^^^^^^^",
            "  File \"/usr/local/lib/python3.12/site-packages/graphql_relay/utils.py\", line 11, in unbase64",
            "    return _unbase64(s).decode('utf-8')",
            "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "UnicodeDecodeError: 'utf-8' codec can't decode byte 0xd3 in position 0: invalid continuation byte",
            "",
            "The above exception was the direct cause of the following exception:",
            "Traceback (most recent call last):",
            "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executor.py\", line 452, in resolve_or_error",
            "    return executor.execute(resolve_fn, source, info, **args)",
            "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executors/sync.py\", line 16, in execute",
            "    return fn(*args, **kwargs)",
            "           ^^^^^^^^^^^^^^^^^^^",
            "  File \"/app/saleor/graphql/decorators.py\", line 32, in wrapper",
            "    return func(info.context, *args, **kwargs)",
            "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/app/saleor/graphql/decorators.py\", line 47, in wrapper",
            "    return f(*args, **kwargs)",
            "           ^^^^^^^^^^^^^^^^^^",
            "  File \"/app/saleor/graphql/shipping/schema.py\", line 60, in resolve_shipping_zone",
            "    _, id = from_global_id_or_error(id, ShippingZone)",
            "            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/app/saleor/graphql/core/utils/__init__.py\", line 87, in from_global_id_or_error",
            "    raise GraphQLError(",
            "graphql.error.base.GraphQLError: Invalid ID: 00000000-0000-0000-0000-000000000000. Expected: ShippingZone."
          ]
        }
      }
    }
  ],
  "data": {
    "shippingZone": null
  },
  "extensions": {
    "cost": {
      "requestedQueryCost": 1,
      "maximumAvailable": 50000
    }
  }
}
```
- **Actual:**
```json
{"errors": [{"message": "Invalid token. Create new one by using tokenCreate mutation.", "locations": [{"line": 1, "column": 9}], "path": ["shippingZone"], "extensions": {"exception": {"code": "InvalidTokenError", "stacktrace": ["Traceback (most recent call last):", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executor.py\", line 452, in resolve_or_error", "    return executor.execute(resolve_fn, source, info, **args)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executors/sync.py\", line 16, in execute", "    return fn(*args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/decorators.py\", line 32, in wrapper", "    return func(info.context, *args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/decorators.py\", line 46, in wrapper", "    test_func(context)", "  File \"/app/saleor/graphql/decorators.py\", line 86, in check_perms", "    if not one_of_permissions_or_auth_filter_required(context, perms):", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 42, in one_of_permissions_or_auth_filter_required", "    perm_results = _get_result_of_permissions_checks(context, permissions)", "                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 60, in _get_result_of_permissions_checks", "    if requestor and permissions:", "       ^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 251, in inner", "    self._setup()", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 404, in _setup", "    self._wrapped = self._setupfunc()", "                    ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 94, in user", "    return get_user(request) or None", "           ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 84, in get_user", "    request._cached_user = cast(User | None, authenticate(request=request))", "                                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/views/decorators/debug.py\", line 75, in sensitive_variables_wrapper", "    return func(*func_args, **func_kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/contrib/auth/__init__.py\", line 114, in authenticate", "    user = backend.authenticate(request, **credentials)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 51, in authenticate", "    return load_user_from_request(request)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 151, in load_user_from_request", "    raise jwt.InvalidTokenError(", "jwt.exceptions.InvalidTokenError: Invalid token. Create new one by using tokenCreate mutation."]}}}], "data": {"shippingZone": null}, "extensions": {"cost": {"requestedQueryCost": 1, "maximumAvailable": 50000}}}
```
- Error: Invalid token. Create new one by using tokenCreate mutation.

### shippingZones (QUERY)
- Status: fail, Match: mismatch, Outcome: auth_error
- Diff: Expected family success (success), got rejection (auth_error)
- **Request:**
```graphql
query { shippingZones(first: 1) { edges { node { id } } } }
```
- **Expected (golden):**
```json
{
  "data": {
    "shippingZones": {
      "edges": [
        {
          "node": {
            "id": "U2hpcHBpbmdab25lOjE="
          }
        }
      ]
    }
  },
  "extensions": {
    "cost": {
      "requestedQueryCost": 1,
      "maximumAvailable": 50000
    }
  }
}
```
- **Actual:**
```json
{"errors": [{"message": "Invalid token. Create new one by using tokenCreate mutation.", "locations": [{"line": 1, "column": 9}], "path": ["shippingZones"], "extensions": {"exception": {"code": "InvalidTokenError", "stacktrace": ["Traceback (most recent call last):", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executor.py\", line 452, in resolve_or_error", "    return executor.execute(resolve_fn, source, info, **args)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executors/sync.py\", line 16, in execute", "    return fn(*args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/core/fields.py\", line 158, in new_resolver", "    return wrapped_resolver(obj, info, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/decorators.py\", line 32, in wrapper", "    return func(info.context, *args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/decorators.py\", line 46, in wrapper", "    test_func(context)", "  File \"/app/saleor/graphql/decorators.py\", line 86, in check_perms", "    if not one_of_permissions_or_auth_filter_required(context, perms):", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 42, in one_of_permissions_or_auth_filter_required", "    perm_results = _get_result_of_permissions_checks(context, permissions)", "                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 60, in _get_result_of_permissions_checks", "    if requestor and permissions:", "       ^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 251, in inner", "    self._setup()", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 404, in _setup", "    self._wrapped = self._setupfunc()", "                    ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 94, in user", "    return get_user(request) or None", "           ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 84, in get_user", "    request._cached_user = cast(User | None, authenticate(request=request))", "                                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/views/decorators/debug.py\", line 75, in sensitive_variables_wrapper", "    return func(*func_args, **func_kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/contrib/auth/__init__.py\", line 114, in authenticate", "    user = backend.authenticate(request, **credentials)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 51, in authenticate", "    return load_user_from_request(request)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 151, in load_user_from_request", "    raise jwt.InvalidTokenError(", "jwt.exceptions.InvalidTokenError: Invalid token. Create new one by using tokenCreate mutation."]}}}], "data": {"shippingZones": null}, "extensions": {"cost": {"requestedQueryCost": 1, "maximumAvailable": 50000}}}
```
- Error: Invalid token. Create new one by using tokenCreate mutation.

### user (QUERY)
- Status: fail, Match: mismatch, Outcome: auth_error
- Diff: Expected family not_found (not_found), got rejection (auth_error)
- **Request:**
```graphql
query { user(id: "00000000-0000-0000-0000-000000000000") { id } }
```
- **Expected (golden):**
```json
{
  "errors": [
    {
      "message": "Invalid ID: 00000000-0000-0000-0000-000000000000. Expected: User.",
      "locations": [
        {
          "line": 1,
          "column": 9
        }
      ],
      "path": [
        "user"
      ],
      "extensions": {
        "exception": {
          "code": "GraphQLError",
          "stacktrace": [
            "Traceback (most recent call last):",
            "  File \"/app/saleor/graphql/core/utils/__init__.py\", line 80, in from_global_id_or_error",
            "    type_, id_ = graphene.Node.from_global_id(global_id)",
            "                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/usr/local/lib/python3.12/site-packages/graphene/relay/node.py\", line 115, in from_global_id",
            "    return from_global_id(global_id)",
            "           ^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/usr/local/lib/python3.12/site-packages/graphql_relay/node/node.py\", line 66, in from_global_id",
            "    unbased_global_id = unbase64(global_id)",
            "                        ^^^^^^^^^^^^^^^^^^^",
            "  File \"/usr/local/lib/python3.12/site-packages/graphql_relay/utils.py\", line 11, in unbase64",
            "    return _unbase64(s).decode('utf-8')",
            "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "UnicodeDecodeError: 'utf-8' codec can't decode byte 0xd3 in position 0: invalid continuation byte",
            "",
            "The above exception was the direct cause of the following exception:",
            "Traceback (most recent call last):",
            "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executor.py\", line 452, in resolve_or_error",
            "    return executor.execute(resolve_fn, source, info, **args)",
            "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executors/sync.py\", line 16, in execute",
            "    return fn(*args, **kwargs)",
            "           ^^^^^^^^^^^^^^^^^^^",
            "  File \"/app/saleor/graphql/decorators.py\", line 32, in wrapper",
            "    return func(info.context, *args, **kwargs)",
            "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/app/saleor/graphql/decorators.py\", line 47, in wrapper",
            "    return f(*args, **kwargs)",
            "           ^^^^^^^^^^^^^^^^^^",
            "  File \"/app/saleor/graphql/account/schema.py\", line 278, in resolve_user",
            "    return resolve_user(info, id, email, external_reference)",
            "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/app/saleor/graphql/core/tracing.py\", line 19, in wrapper",
            "    return func(*args, **kwargs)",
            "           ^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/app/saleor/graphql/account/resolvers.py\", line 68, in resolve_user",
            "    _model, filter_kwargs[\"pk\"] = from_global_id_or_error(id, User)",
            "                                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/app/saleor/graphql/core/utils/__init__.py\", line 87, in from_global_id_or_error",
            "    raise GraphQLError(",
            "graphql.error.base.GraphQLError: Invalid ID: 00000000-0000-0000-0000-000000000000. Expected: User."
          ]
        }
      }
    }
  ],
  "data": {
    "user": null
  },
  "extensions": {
    "cost": {
      "requestedQueryCost": 1,
      "maximumAvailable": 50000
    }
  }
}
```
- **Actual:**
```json
{"errors": [{"message": "Invalid token. Create new one by using tokenCreate mutation.", "locations": [{"line": 1, "column": 9}], "path": ["user"], "extensions": {"exception": {"code": "InvalidTokenError", "stacktrace": ["Traceback (most recent call last):", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executor.py\", line 452, in resolve_or_error", "    return executor.execute(resolve_fn, source, info, **args)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executors/sync.py\", line 16, in execute", "    return fn(*args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/decorators.py\", line 32, in wrapper", "    return func(info.context, *args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/decorators.py\", line 46, in wrapper", "    test_func(context)", "  File \"/app/saleor/graphql/decorators.py\", line 86, in check_perms", "    if not one_of_permissions_or_auth_filter_required(context, perms):", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 42, in one_of_permissions_or_auth_filter_required", "    perm_results = _get_result_of_permissions_checks(context, permissions)", "                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 60, in _get_result_of_permissions_checks", "    if requestor and permissions:", "       ^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 251, in inner", "    self._setup()", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 404, in _setup", "    self._wrapped = self._setupfunc()", "                    ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 94, in user", "    return get_user(request) or None", "           ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 84, in get_user", "    request._cached_user = cast(User | None, authenticate(request=request))", "                                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/views/decorators/debug.py\", line 75, in sensitive_variables_wrapper", "    return func(*func_args, **func_kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/contrib/auth/__init__.py\", line 114, in authenticate", "    user = backend.authenticate(request, **credentials)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 51, in authenticate", "    return load_user_from_request(request)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 151, in load_user_from_request", "    raise jwt.InvalidTokenError(", "jwt.exceptions.InvalidTokenError: Invalid token. Create new one by using tokenCreate mutation."]}}}], "data": {"user": null}, "extensions": {"cost": {"requestedQueryCost": 1, "maximumAvailable": 50000}}}
```
- Error: Invalid token. Create new one by using tokenCreate mutation.

### shopDomainUpdate (MUTATION)
- Status: fail, Match: mismatch, Outcome: auth_error
- Diff: Expected family success (success), got rejection (auth_error)
- **Request:**
```graphql
mutation { shopDomainUpdate(input: {}) { errors { field message code } } }
```
- **Expected (golden):**
```json
{
  "data": {
    "shopDomainUpdate": {
      "errors": []
    }
  },
  "extensions": {
    "cost": {
      "requestedQueryCost": 0,
      "maximumAvailable": 50000
    }
  }
}
```
- **Actual:**
```json
{"errors": [{"message": "Invalid token. Create new one by using tokenCreate mutation.", "locations": [{"line": 1, "column": 12}], "path": ["shopDomainUpdate"], "extensions": {"exception": {"code": "InvalidTokenError", "stacktrace": ["Traceback (most recent call last):", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executor.py\", line 452, in resolve_or_error", "    return executor.execute(resolve_fn, source, info, **args)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executors/sync.py\", line 16, in execute", "    return fn(*args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/api.py\", line 83, in _wrapper", "    return original(*args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/contextlib.py\", line 81, in inner", "    return func(*args, **kwds)", "           ^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/core/mutations.py\", line 520, in mutate", "    setup_context_user(info.context)", "  File \"/app/saleor/graphql/core/context.py\", line 66, in setup_context_user", "    context.user._setup()  # type: ignore[union-attr]", "    ^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 404, in _setup", "    self._wrapped = self._setupfunc()", "                    ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 94, in user", "    return get_user(request) or None", "           ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 84, in get_user", "    request._cached_user = cast(User | None, authenticate(request=request))", "                                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/views/decorators/debug.py\", line 75, in sensitive_variables_wrapper", "    return func(*func_args, **func_kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/contrib/auth/__init__.py\", line 114, in authenticate", "    user = backend.authenticate(request, **credentials)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 51, in authenticate", "    return load_user_from_request(request)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 151, in load_user_from_request", "    raise jwt.InvalidTokenError(", "jwt.exceptions.InvalidTokenError: Invalid token. Create new one by using tokenCreate mutation."]}}}], "data": {"shopDomainUpdate": null}, "extensions": {"cost": {"requestedQueryCost": 0, "maximumAvailable": 50000}}}
```
- Error: Invalid token. Create new one by using tokenCreate mutation.

### paymentGatewayInitialize (MUTATION)
- Status: fail, Match: mismatch, Outcome: auth_error
- Diff: Expected family not_found (not_found), got rejection (auth_error)
- **Request:**
```graphql
mutation { paymentGatewayInitialize(id: "00000000-0000-0000-0000-000000000000") { errors { field message } } }
```
- **Expected (golden):**
```json
{
  "errors": [
    {
      "message": "Invalid ID: 00000000-0000-0000-0000-000000000000.",
      "locations": [
        {
          "line": 1,
          "column": 12
        }
      ],
      "path": [
        "paymentGatewayInitialize"
      ],
      "extensions": {
        "exception": {
          "code": "GraphQLError",
          "stacktrace": [
            "Traceback (most recent call last):",
            "  File \"/app/saleor/graphql/core/utils/__init__.py\", line 80, in from_global_id_or_error",
            "    type_, id_ = graphene.Node.from_global_id(global_id)",
            "                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/usr/local/lib/python3.12/site-packages/graphene/relay/node.py\", line 115, in from_global_id",
            "    return from_global_id(global_id)",
            "           ^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/usr/local/lib/python3.12/site-packages/graphql_relay/node/node.py\", line 66, in from_global_id",
            "    unbased_global_id = unbase64(global_id)",
            "                        ^^^^^^^^^^^^^^^^^^^",
            "  File \"/usr/local/lib/python3.12/site-packages/graphql_relay/utils.py\", line 11, in unbase64",
            "    return _unbase64(s).decode('utf-8')",
            "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "UnicodeDecodeError: 'utf-8' codec can't decode byte 0xd3 in position 0: invalid continuation byte",
            "",
            "The above exception was the direct cause of the following exception:",
            "Traceback (most recent call last):",
            "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executor.py\", line 452, in resolve_or_error",
            "    return executor.execute(resolve_fn, source, info, **args)",
            "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executors/sync.py\", line 16, in execute",
            "    return fn(*args, **kwargs)",
            "           ^^^^^^^^^^^^^^^^^^^",
            "  File \"/usr/local/lib/python3.12/contextlib.py\", line 81, in inner",
            "    return func(*args, **kwds)",
            "           ^^^^^^^^^^^^^^^^^^^",
            "  File \"/app/saleor/graphql/core/mutations.py\", line 526, in mutate",
            "    response = cls.perform_mutation(root, info, **data)",
            "               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/app/saleor/graphql/payment/mutations/transaction/payment_gateway_initialize.py\", line 129, in perform_mutation",
            "    source_object = cls.clean_source_object(",
            "                    ^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/app/saleor/graphql/payment/mutations/base.py\", line 35, in clean_source_object",
            "    source_object_type, source_object_id = from_global_id_or_error(",
            "                                           ^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/app/saleor/graphql/core/utils/__init__.py\", line 90, in from_global_id_or_error",
            "    raise GraphQLError(f\"Invalid ID: {global_id}.\") from e",
            "graphql.error.base.GraphQLError: Invalid ID: 00000000-0000-0000-0000-000000000000."
          ]
        }
      }
    }
  ],
  "data": {
    "paymentGatewayInitialize": null
  },
  "extensions": {
    "cost": {
      "requestedQueryCost": 0,
      "maximumAvailable": 50000
    }
  }
}
```
- **Actual:**
```json
{"errors": [{"message": "Invalid token. Create new one by using tokenCreate mutation.", "locations": [{"line": 1, "column": 12}], "path": ["paymentGatewayInitialize"], "extensions": {"exception": {"code": "InvalidTokenError", "stacktrace": ["Traceback (most recent call last):", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executor.py\", line 452, in resolve_or_error", "    return executor.execute(resolve_fn, source, info, **args)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executors/sync.py\", line 16, in execute", "    return fn(*args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/contextlib.py\", line 81, in inner", "    return func(*args, **kwds)", "           ^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/core/mutations.py\", line 520, in mutate", "    setup_context_user(info.context)", "  File \"/app/saleor/graphql/core/context.py\", line 66, in setup_context_user", "    context.user._setup()  # type: ignore[union-attr]", "    ^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 404, in _setup", "    self._wrapped = self._setupfunc()", "                    ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 94, in user", "    return get_user(request) or None", "           ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 84, in get_user", "    request._cached_user = cast(User | None, authenticate(request=request))", "                                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/views/decorators/debug.py\", line 75, in sensitive_variables_wrapper", "    return func(*func_args, **func_kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/contrib/auth/__init__.py\", line 114, in authenticate", "    user = backend.authenticate(request, **credentials)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 51, in authenticate", "    return load_user_from_request(request)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 151, in load_user_from_request", "    raise jwt.InvalidTokenError(", "jwt.exceptions.InvalidTokenError: Invalid token. Create new one by using tokenCreate mutation."]}}}], "data": {"paymentGatewayInitialize": null}, "extensions": {"cost": {"requestedQueryCost": 0, "maximumAvailable": 50000}}}
```
- Error: Invalid token. Create new one by using tokenCreate mutation.

### appExtension (QUERY)
- Status: fail, Match: mismatch, Outcome: auth_error
- Diff: Expected family not_found (not_found), got rejection (auth_error)
- **Request:**
```graphql
query { appExtension(id: "00000000-0000-0000-0000-000000000000") { id } }
```
- **Expected (golden):**
```json
{
  "errors": [
    {
      "message": "Invalid ID: 00000000-0000-0000-0000-000000000000. Expected: AppExtension.",
      "locations": [
        {
          "line": 1,
          "column": 9
        }
      ],
      "path": [
        "appExtension"
      ],
      "extensions": {
        "exception": {
          "code": "GraphQLError",
          "stacktrace": [
            "Traceback (most recent call last):",
            "  File \"/app/saleor/graphql/core/utils/__init__.py\", line 80, in from_global_id_or_error",
            "    type_, id_ = graphene.Node.from_global_id(global_id)",
            "                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/usr/local/lib/python3.12/site-packages/graphene/relay/node.py\", line 115, in from_global_id",
            "    return from_global_id(global_id)",
            "           ^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/usr/local/lib/python3.12/site-packages/graphql_relay/node/node.py\", line 66, in from_global_id",
            "    unbased_global_id = unbase64(global_id)",
            "                        ^^^^^^^^^^^^^^^^^^^",
            "  File \"/usr/local/lib/python3.12/site-packages/graphql_relay/utils.py\", line 11, in unbase64",
            "    return _unbase64(s).decode('utf-8')",
            "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "UnicodeDecodeError: 'utf-8' codec can't decode byte 0xd3 in position 0: invalid continuation byte",
            "",
            "The above exception was the direct cause of the following exception:",
            "Traceback (most recent call last):",
            "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executor.py\", line 452, in resolve_or_error",
            "    return executor.execute(resolve_fn, source, info, **args)",
            "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executors/sync.py\", line 16, in execute",
            "    return fn(*args, **kwargs)",
            "           ^^^^^^^^^^^^^^^^^^^",
            "  File \"/app/saleor/graphql/decorators.py\", line 32, in wrapper",
            "    return func(info.context, *args, **kwargs)",
            "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/app/saleor/graphql/decorators.py\", line 47, in wrapper",
            "    return f(*args, **kwargs)",
            "           ^^^^^^^^^^^^^^^^^^",
            "  File \"/app/saleor/graphql/app/schema.py\", line 174, in resolve_app_extension",
            "    _, id = from_global_id_or_error(id, \"AppExtension\")",
            "            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/app/saleor/graphql/core/utils/__init__.py\", line 87, in from_global_id_or_error",
            "    raise GraphQLError(",
            "graphql.error.base.GraphQLError: Invalid ID: 00000000-0000-0000-0000-000000000000. Expected: AppExtension."
          ]
        }
      }
    }
  ],
  "data": {
    "appExtension": null
  },
  "extensions": {
    "cost": {
      "requestedQueryCost": 1,
      "maximumAvailable": 50000
    }
  }
}
```
- **Actual:**
```json
{"errors": [{"message": "Invalid token. Create new one by using tokenCreate mutation.", "locations": [{"line": 1, "column": 9}], "path": ["appExtension"], "extensions": {"exception": {"code": "InvalidTokenError", "stacktrace": ["Traceback (most recent call last):", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executor.py\", line 452, in resolve_or_error", "    return executor.execute(resolve_fn, source, info, **args)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executors/sync.py\", line 16, in execute", "    return fn(*args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/decorators.py\", line 32, in wrapper", "    return func(info.context, *args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/decorators.py\", line 46, in wrapper", "    test_func(context)", "  File \"/app/saleor/graphql/decorators.py\", line 86, in check_perms", "    if not one_of_permissions_or_auth_filter_required(context, perms):", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 42, in one_of_permissions_or_auth_filter_required", "    perm_results = _get_result_of_permissions_checks(context, permissions)", "                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 60, in _get_result_of_permissions_checks", "    if requestor and permissions:", "       ^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 251, in inner", "    self._setup()", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 404, in _setup", "    self._wrapped = self._setupfunc()", "                    ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 94, in user", "    return get_user(request) or None", "           ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 84, in get_user", "    request._cached_user = cast(User | None, authenticate(request=request))", "                                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/views/decorators/debug.py\", line 75, in sensitive_variables_wrapper", "    return func(*func_args, **func_kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/contrib/auth/__init__.py\", line 114, in authenticate", "    user = backend.authenticate(request, **credentials)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 51, in authenticate", "    return load_user_from_request(request)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 151, in load_user_from_request", "    raise jwt.InvalidTokenError(", "jwt.exceptions.InvalidTokenError: Invalid token. Create new one by using tokenCreate mutation."]}}}], "data": {"appExtension": null}, "extensions": {"cost": {"requestedQueryCost": 1, "maximumAvailable": 50000}}}
```
- Error: Invalid token. Create new one by using tokenCreate mutation.

### shopSettingsUpdate (MUTATION)
- Status: fail, Match: mismatch, Outcome: auth_error
- Diff: Expected family success (success), got rejection (auth_error)
- **Request:**
```graphql
mutation { shopSettingsUpdate(input: {}) { errors { field message code } } }
```
- **Expected (golden):**
```json
{
  "data": {
    "shopSettingsUpdate": {
      "errors": []
    }
  },
  "extensions": {
    "cost": {
      "requestedQueryCost": 0,
      "maximumAvailable": 50000
    }
  }
}
```
- **Actual:**
```json
{"errors": [{"message": "Invalid token. Create new one by using tokenCreate mutation.", "locations": [{"line": 1, "column": 12}], "path": ["shopSettingsUpdate"], "extensions": {"exception": {"code": "InvalidTokenError", "stacktrace": ["Traceback (most recent call last):", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executor.py\", line 452, in resolve_or_error", "    return executor.execute(resolve_fn, source, info, **args)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executors/sync.py\", line 16, in execute", "    return fn(*args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/contextlib.py\", line 81, in inner", "    return func(*args, **kwds)", "           ^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/core/mutations.py\", line 520, in mutate", "    setup_context_user(info.context)", "  File \"/app/saleor/graphql/core/context.py\", line 66, in setup_context_user", "    context.user._setup()  # type: ignore[union-attr]", "    ^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 404, in _setup", "    self._wrapped = self._setupfunc()", "                    ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 94, in user", "    return get_user(request) or None", "           ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 84, in get_user", "    request._cached_user = cast(User | None, authenticate(request=request))", "                                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/views/decorators/debug.py\", line 75, in sensitive_variables_wrapper", "    return func(*func_args, **func_kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/contrib/auth/__init__.py\", line 114, in authenticate", "    user = backend.authenticate(request, **credentials)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 51, in authenticate", "    return load_user_from_request(request)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 151, in load_user_from_request", "    raise jwt.InvalidTokenError(", "jwt.exceptions.InvalidTokenError: Invalid token. Create new one by using tokenCreate mutation."]}}}], "data": {"shopSettingsUpdate": null}, "extensions": {"cost": {"requestedQueryCost": 0, "maximumAvailable": 50000}}}
```
- Error: Invalid token. Create new one by using tokenCreate mutation.

### appExtensions (QUERY)
- Status: fail, Match: mismatch, Outcome: auth_error
- Diff: Expected family success (success), got rejection (auth_error)
- **Request:**
```graphql
query { appExtensions(first: 1) { edges { node { id } } } }
```
- **Expected (golden):**
```json
{
  "data": {
    "appExtensions": {
      "edges": []
    }
  },
  "extensions": {
    "cost": {
      "requestedQueryCost": 1,
      "maximumAvailable": 50000
    }
  }
}
```
- **Actual:**
```json
{"errors": [{"message": "Invalid token. Create new one by using tokenCreate mutation.", "locations": [{"line": 1, "column": 9}], "path": ["appExtensions"], "extensions": {"exception": {"code": "InvalidTokenError", "stacktrace": ["Traceback (most recent call last):", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executor.py\", line 452, in resolve_or_error", "    return executor.execute(resolve_fn, source, info, **args)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executors/sync.py\", line 16, in execute", "    return fn(*args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/core/fields.py\", line 158, in new_resolver", "    return wrapped_resolver(obj, info, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/decorators.py\", line 32, in wrapper", "    return func(info.context, *args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/decorators.py\", line 46, in wrapper", "    test_func(context)", "  File \"/app/saleor/graphql/decorators.py\", line 86, in check_perms", "    if not one_of_permissions_or_auth_filter_required(context, perms):", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 42, in one_of_permissions_or_auth_filter_required", "    perm_results = _get_result_of_permissions_checks(context, permissions)", "                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 60, in _get_result_of_permissions_checks", "    if requestor and permissions:", "       ^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 251, in inner", "    self._setup()", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 404, in _setup", "    self._wrapped = self._setupfunc()", "                    ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 94, in user", "    return get_user(request) or None", "           ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 84, in get_user", "    request._cached_user = cast(User | None, authenticate(request=request))", "                                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/views/decorators/debug.py\", line 75, in sensitive_variables_wrapper", "    return func(*func_args, **func_kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/contrib/auth/__init__.py\", line 114, in authenticate", "    user = backend.authenticate(request, **credentials)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 51, in authenticate", "    return load_user_from_request(request)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 151, in load_user_from_request", "    raise jwt.InvalidTokenError(", "jwt.exceptions.InvalidTokenError: Invalid token. Create new one by using tokenCreate mutation."]}}}], "data": {"appExtensions": null}, "extensions": {"cost": {"requestedQueryCost": 1, "maximumAvailable": 50000}}}
```
- Error: Invalid token. Create new one by using tokenCreate mutation.

### payment (QUERY)
- Status: fail, Match: mismatch, Outcome: auth_error
- Diff: Expected family not_found (not_found), got rejection (auth_error)
- **Request:**
```graphql
query { payment(id: "00000000-0000-0000-0000-000000000000") { id } }
```
- **Expected (golden):**
```json
{
  "errors": [
    {
      "message": "Invalid ID: 00000000-0000-0000-0000-000000000000. Expected: Payment.",
      "locations": [
        {
          "line": 1,
          "column": 9
        }
      ],
      "path": [
        "payment"
      ],
      "extensions": {
        "exception": {
          "code": "GraphQLError",
          "stacktrace": [
            "Traceback (most recent call last):",
            "  File \"/app/saleor/graphql/core/utils/__init__.py\", line 80, in from_global_id_or_error",
            "    type_, id_ = graphene.Node.from_global_id(global_id)",
            "                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/usr/local/lib/python3.12/site-packages/graphene/relay/node.py\", line 115, in from_global_id",
            "    return from_global_id(global_id)",
            "           ^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/usr/local/lib/python3.12/site-packages/graphql_relay/node/node.py\", line 66, in from_global_id",
            "    unbased_global_id = unbase64(global_id)",
            "                        ^^^^^^^^^^^^^^^^^^^",
            "  File \"/usr/local/lib/python3.12/site-packages/graphql_relay/utils.py\", line 11, in unbase64",
            "    return _unbase64(s).decode('utf-8')",
            "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "UnicodeDecodeError: 'utf-8' codec can't decode byte 0xd3 in position 0: invalid continuation byte",
            "",
            "The above exception was the direct cause of the following exception:",
            "Traceback (most recent call last):",
            "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executor.py\", line 452, in resolve_or_error",
            "    return executor.execute(resolve_fn, source, info, **args)",
            "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executors/sync.py\", line 16, in execute",
            "    return fn(*args, **kwargs)",
            "           ^^^^^^^^^^^^^^^^^^^",
            "  File \"/app/saleor/graphql/decorators.py\", line 32, in wrapper",
            "    return func(info.context, *args, **kwargs)",
            "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/app/saleor/graphql/decorators.py\", line 47, in wrapper",
            "    return f(*args, **kwargs)",
            "           ^^^^^^^^^^^^^^^^^^",
            "  File \"/app/saleor/graphql/payment/schema.py\", line 126, in resolve_payment",
            "    _, id = from_global_id_or_error(data[\"id\"], Payment)",
            "            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/app/saleor/graphql/core/utils/__init__.py\", line 87, in from_global_id_or_error",
            "    raise GraphQLError(",
            "graphql.error.base.GraphQLError: Invalid ID: 00000000-0000-0000-0000-000000000000. Expected: Payment."
          ]
        }
      }
    }
  ],
  "data": {
    "payment": null
  },
  "extensions": {
    "cost": {
      "requestedQueryCost": 1,
      "maximumAvailable": 50000
    }
  }
}
```
- **Actual:**
```json
{"errors": [{"message": "Invalid token. Create new one by using tokenCreate mutation.", "locations": [{"line": 1, "column": 9}], "path": ["payment"], "extensions": {"exception": {"code": "InvalidTokenError", "stacktrace": ["Traceback (most recent call last):", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executor.py\", line 452, in resolve_or_error", "    return executor.execute(resolve_fn, source, info, **args)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executors/sync.py\", line 16, in execute", "    return fn(*args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/decorators.py\", line 32, in wrapper", "    return func(info.context, *args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/decorators.py\", line 46, in wrapper", "    test_func(context)", "  File \"/app/saleor/graphql/decorators.py\", line 86, in check_perms", "    if not one_of_permissions_or_auth_filter_required(context, perms):", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 42, in one_of_permissions_or_auth_filter_required", "    perm_results = _get_result_of_permissions_checks(context, permissions)", "                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 60, in _get_result_of_permissions_checks", "    if requestor and permissions:", "       ^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 251, in inner", "    self._setup()", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 404, in _setup", "    self._wrapped = self._setupfunc()", "                    ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 94, in user", "    return get_user(request) or None", "           ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 84, in get_user", "    request._cached_user = cast(User | None, authenticate(request=request))", "                                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/views/decorators/debug.py\", line 75, in sensitive_variables_wrapper", "    return func(*func_args, **func_kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/contrib/auth/__init__.py\", line 114, in authenticate", "    user = backend.authenticate(request, **credentials)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 51, in authenticate", "    return load_user_from_request(request)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 151, in load_user_from_request", "    raise jwt.InvalidTokenError(", "jwt.exceptions.InvalidTokenError: Invalid token. Create new one by using tokenCreate mutation."]}}}], "data": {"payment": null}, "extensions": {"cost": {"requestedQueryCost": 1, "maximumAvailable": 50000}}}
```
- Error: Invalid token. Create new one by using tokenCreate mutation.

### payments (QUERY)
- Status: fail, Match: mismatch, Outcome: auth_error
- Diff: Expected family success (success), got rejection (auth_error)
- **Request:**
```graphql
query { payments(first: 1) { edges { node { id } } } }
```
- **Expected (golden):**
```json
{
  "data": {
    "payments": {
      "edges": []
    }
  },
  "extensions": {
    "cost": {
      "requestedQueryCost": 1,
      "maximumAvailable": 50000
    }
  }
}
```
- **Actual:**
```json
{"errors": [{"message": "Invalid token. Create new one by using tokenCreate mutation.", "locations": [{"line": 1, "column": 9}], "path": ["payments"], "extensions": {"exception": {"code": "InvalidTokenError", "stacktrace": ["Traceback (most recent call last):", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executor.py\", line 452, in resolve_or_error", "    return executor.execute(resolve_fn, source, info, **args)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executors/sync.py\", line 16, in execute", "    return fn(*args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/core/fields.py\", line 158, in new_resolver", "    return wrapped_resolver(obj, info, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/decorators.py\", line 32, in wrapper", "    return func(info.context, *args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/decorators.py\", line 46, in wrapper", "    test_func(context)", "  File \"/app/saleor/graphql/decorators.py\", line 86, in check_perms", "    if not one_of_permissions_or_auth_filter_required(context, perms):", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 42, in one_of_permissions_or_auth_filter_required", "    perm_results = _get_result_of_permissions_checks(context, permissions)", "                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 60, in _get_result_of_permissions_checks", "    if requestor and permissions:", "       ^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 251, in inner", "    self._setup()", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 404, in _setup", "    self._wrapped = self._setupfunc()", "                    ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 94, in user", "    return get_user(request) or None", "           ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 84, in get_user", "    request._cached_user = cast(User | None, authenticate(request=request))", "                                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/views/decorators/debug.py\", line 75, in sensitive_variables_wrapper", "    return func(*func_args, **func_kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/contrib/auth/__init__.py\", line 114, in authenticate", "    user = backend.authenticate(request, **credentials)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 51, in authenticate", "    return load_user_from_request(request)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 151, in load_user_from_request", "    raise jwt.InvalidTokenError(", "jwt.exceptions.InvalidTokenError: Invalid token. Create new one by using tokenCreate mutation."]}}}], "data": {"payments": null}, "extensions": {"cost": {"requestedQueryCost": 1, "maximumAvailable": 50000}}}
```
- Error: Invalid token. Create new one by using tokenCreate mutation.

### staffUsers (QUERY)
- Status: fail, Match: mismatch, Outcome: auth_error
- Diff: Expected family success (success), got rejection (auth_error)
- **Request:**
```graphql
query { staffUsers(first: 1) { edges { node { id } } } }
```
- **Expected (golden):**
```json
{
  "data": {
    "staffUsers": {
      "edges": [
        {
          "node": {
            "id": "VXNlcjox"
          }
        }
      ]
    }
  },
  "extensions": {
    "cost": {
      "requestedQueryCost": 1,
      "maximumAvailable": 50000
    }
  }
}
```
- **Actual:**
```json
{"errors": [{"message": "Invalid token. Create new one by using tokenCreate mutation.", "locations": [{"line": 1, "column": 9}], "path": ["staffUsers"], "extensions": {"exception": {"code": "InvalidTokenError", "stacktrace": ["Traceback (most recent call last):", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executor.py\", line 452, in resolve_or_error", "    return executor.execute(resolve_fn, source, info, **args)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executors/sync.py\", line 16, in execute", "    return fn(*args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/core/fields.py\", line 158, in new_resolver", "    return wrapped_resolver(obj, info, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/decorators.py\", line 32, in wrapper", "    return func(info.context, *args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/decorators.py\", line 46, in wrapper", "    test_func(context)", "  File \"/app/saleor/graphql/decorators.py\", line 86, in check_perms", "    if not one_of_permissions_or_auth_filter_required(context, perms):", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 42, in one_of_permissions_or_auth_filter_required", "    perm_results = _get_result_of_permissions_checks(context, permissions)", "                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 60, in _get_result_of_permissions_checks", "    if requestor and permissions:", "       ^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 251, in inner", "    self._setup()", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 404, in _setup", "    self._wrapped = self._setupfunc()", "                    ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 94, in user", "    return get_user(request) or None", "           ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 84, in get_user", "    request._cached_user = cast(User | None, authenticate(request=request))", "                                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/views/decorators/debug.py\", line 75, in sensitive_variables_wrapper", "    return func(*func_args, **func_kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/contrib/auth/__init__.py\", line 114, in authenticate", "    user = backend.authenticate(request, **credentials)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 51, in authenticate", "    return load_user_from_request(request)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 151, in load_user_from_request", "    raise jwt.InvalidTokenError(", "jwt.exceptions.InvalidTokenError: Invalid token. Create new one by using tokenCreate mutation."]}}}], "data": {"staffUsers": null}, "extensions": {"cost": {"requestedQueryCost": 1, "maximumAvailable": 50000}}}
```
- Error: Invalid token. Create new one by using tokenCreate mutation.

### voucher (QUERY)
- Status: fail, Match: mismatch, Outcome: auth_error
- Diff: Expected family not_found (not_found), got rejection (auth_error)
- **Request:**
```graphql
query { voucher(id: "00000000-0000-0000-0000-000000000000") { id } }
```
- **Expected (golden):**
```json
{
  "errors": [
    {
      "message": "Invalid ID: 00000000-0000-0000-0000-000000000000. Expected: Voucher.",
      "locations": [
        {
          "line": 1,
          "column": 9
        }
      ],
      "path": [
        "voucher"
      ],
      "extensions": {
        "exception": {
          "code": "GraphQLError",
          "stacktrace": [
            "Traceback (most recent call last):",
            "  File \"/app/saleor/graphql/core/utils/__init__.py\", line 80, in from_global_id_or_error",
            "    type_, id_ = graphene.Node.from_global_id(global_id)",
            "                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/usr/local/lib/python3.12/site-packages/graphene/relay/node.py\", line 115, in from_global_id",
            "    return from_global_id(global_id)",
            "           ^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/usr/local/lib/python3.12/site-packages/graphql_relay/node/node.py\", line 66, in from_global_id",
            "    unbased_global_id = unbase64(global_id)",
            "                        ^^^^^^^^^^^^^^^^^^^",
            "  File \"/usr/local/lib/python3.12/site-packages/graphql_relay/utils.py\", line 11, in unbase64",
            "    return _unbase64(s).decode('utf-8')",
            "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "UnicodeDecodeError: 'utf-8' codec can't decode byte 0xd3 in position 0: invalid continuation byte",
            "",
            "The above exception was the direct cause of the following exception:",
            "Traceback (most recent call last):",
            "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executor.py\", line 452, in resolve_or_error",
            "    return executor.execute(resolve_fn, source, info, **args)",
            "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executors/sync.py\", line 16, in execute",
            "    return fn(*args, **kwargs)",
            "           ^^^^^^^^^^^^^^^^^^^",
            "  File \"/app/saleor/graphql/decorators.py\", line 32, in wrapper",
            "    return func(info.context, *args, **kwargs)",
            "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/app/saleor/graphql/decorators.py\", line 47, in wrapper",
            "    return f(*args, **kwargs)",
            "           ^^^^^^^^^^^^^^^^^^",
            "  File \"/app/saleor/graphql/discount/schema.py\", line 179, in resolve_voucher",
            "    _, id = from_global_id_or_error(id, Voucher)",
            "            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/app/saleor/graphql/core/utils/__init__.py\", line 87, in from_global_id_or_error",
            "    raise GraphQLError(",
            "graphql.error.base.GraphQLError: Invalid ID: 00000000-0000-0000-0000-000000000000. Expected: Voucher."
          ]
        }
      }
    }
  ],
  "data": {
    "voucher": null
  },
  "extensions": {
    "cost": {
      "requestedQueryCost": 1,
      "maximumAvailable": 50000
    }
  }
}
```
- **Actual:**
```json
{"errors": [{"message": "Invalid token. Create new one by using tokenCreate mutation.", "locations": [{"line": 1, "column": 9}], "path": ["voucher"], "extensions": {"exception": {"code": "InvalidTokenError", "stacktrace": ["Traceback (most recent call last):", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executor.py\", line 452, in resolve_or_error", "    return executor.execute(resolve_fn, source, info, **args)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executors/sync.py\", line 16, in execute", "    return fn(*args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/decorators.py\", line 32, in wrapper", "    return func(info.context, *args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/decorators.py\", line 46, in wrapper", "    test_func(context)", "  File \"/app/saleor/graphql/decorators.py\", line 86, in check_perms", "    if not one_of_permissions_or_auth_filter_required(context, perms):", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 42, in one_of_permissions_or_auth_filter_required", "    perm_results = _get_result_of_permissions_checks(context, permissions)", "                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 60, in _get_result_of_permissions_checks", "    if requestor and permissions:", "       ^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 251, in inner", "    self._setup()", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 404, in _setup", "    self._wrapped = self._setupfunc()", "                    ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 94, in user", "    return get_user(request) or None", "           ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 84, in get_user", "    request._cached_user = cast(User | None, authenticate(request=request))", "                                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/views/decorators/debug.py\", line 75, in sensitive_variables_wrapper", "    return func(*func_args, **func_kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/contrib/auth/__init__.py\", line 114, in authenticate", "    user = backend.authenticate(request, **credentials)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 51, in authenticate", "    return load_user_from_request(request)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 151, in load_user_from_request", "    raise jwt.InvalidTokenError(", "jwt.exceptions.InvalidTokenError: Invalid token. Create new one by using tokenCreate mutation."]}}}], "data": {"voucher": null}, "extensions": {"cost": {"requestedQueryCost": 1, "maximumAvailable": 50000}}}
```
- Error: Invalid token. Create new one by using tokenCreate mutation.

### vouchers (QUERY)
- Status: fail, Match: mismatch, Outcome: auth_error
- Diff: Expected family success (success), got rejection (auth_error)
- **Request:**
```graphql
query { vouchers(first: 1) { edges { node { id } } } }
```
- **Expected (golden):**
```json
{
  "data": {
    "vouchers": {
      "edges": []
    }
  },
  "extensions": {
    "cost": {
      "requestedQueryCost": 1,
      "maximumAvailable": 50000
    }
  }
}
```
- **Actual:**
```json
{"errors": [{"message": "Invalid token. Create new one by using tokenCreate mutation.", "locations": [{"line": 1, "column": 9}], "path": ["vouchers"], "extensions": {"exception": {"code": "InvalidTokenError", "stacktrace": ["Traceback (most recent call last):", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executor.py\", line 452, in resolve_or_error", "    return executor.execute(resolve_fn, source, info, **args)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executors/sync.py\", line 16, in execute", "    return fn(*args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/core/fields.py\", line 158, in new_resolver", "    return wrapped_resolver(obj, info, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/decorators.py\", line 32, in wrapper", "    return func(info.context, *args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/decorators.py\", line 46, in wrapper", "    test_func(context)", "  File \"/app/saleor/graphql/decorators.py\", line 86, in check_perms", "    if not one_of_permissions_or_auth_filter_required(context, perms):", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 42, in one_of_permissions_or_auth_filter_required", "    perm_results = _get_result_of_permissions_checks(context, permissions)", "                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 60, in _get_result_of_permissions_checks", "    if requestor and permissions:", "       ^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 251, in inner", "    self._setup()", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 404, in _setup", "    self._wrapped = self._setupfunc()", "                    ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 94, in user", "    return get_user(request) or None", "           ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 84, in get_user", "    request._cached_user = cast(User | None, authenticate(request=request))", "                                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/views/decorators/debug.py\", line 75, in sensitive_variables_wrapper", "    return func(*func_args, **func_kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/contrib/auth/__init__.py\", line 114, in authenticate", "    user = backend.authenticate(request, **credentials)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 51, in authenticate", "    return load_user_from_request(request)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 151, in load_user_from_request", "    raise jwt.InvalidTokenError(", "jwt.exceptions.InvalidTokenError: Invalid token. Create new one by using tokenCreate mutation."]}}}], "data": {"vouchers": null}, "extensions": {"cost": {"requestedQueryCost": 1, "maximumAvailable": 50000}}}
```
- Error: Invalid token. Create new one by using tokenCreate mutation.

### permissionGroup (QUERY)
- Status: fail, Match: mismatch, Outcome: auth_error
- Diff: Expected family not_found (not_found), got rejection (auth_error)
- **Request:**
```graphql
query { permissionGroup(id: "00000000-0000-0000-0000-000000000000") { id } }
```
- **Expected (golden):**
```json
{
  "errors": [
    {
      "message": "Invalid ID: 00000000-0000-0000-0000-000000000000. Expected: Group.",
      "locations": [
        {
          "line": 1,
          "column": 9
        }
      ],
      "path": [
        "permissionGroup"
      ],
      "extensions": {
        "exception": {
          "code": "GraphQLError",
          "stacktrace": [
            "Traceback (most recent call last):",
            "  File \"/app/saleor/graphql/core/utils/__init__.py\", line 80, in from_global_id_or_error",
            "    type_, id_ = graphene.Node.from_global_id(global_id)",
            "                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/usr/local/lib/python3.12/site-packages/graphene/relay/node.py\", line 115, in from_global_id",
            "    return from_global_id(global_id)",
            "           ^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/usr/local/lib/python3.12/site-packages/graphql_relay/node/node.py\", line 66, in from_global_id",
            "    unbased_global_id = unbase64(global_id)",
            "                        ^^^^^^^^^^^^^^^^^^^",
            "  File \"/usr/local/lib/python3.12/site-packages/graphql_relay/utils.py\", line 11, in unbase64",
            "    return _unbase64(s).decode('utf-8')",
            "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "UnicodeDecodeError: 'utf-8' codec can't decode byte 0xd3 in position 0: invalid continuation byte",
            "",
            "The above exception was the direct cause of the following exception:",
            "Traceback (most recent call last):",
            "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executor.py\", line 452, in resolve_or_error",
            "    return executor.execute(resolve_fn, source, info, **args)",
            "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executors/sync.py\", line 16, in execute",
            "    return fn(*args, **kwargs)",
            "           ^^^^^^^^^^^^^^^^^^^",
            "  File \"/app/saleor/graphql/decorators.py\", line 32, in wrapper",
            "    return func(info.context, *args, **kwargs)",
            "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/app/saleor/graphql/decorators.py\", line 47, in wrapper",
            "    return f(*args, **kwargs)",
            "           ^^^^^^^^^^^^^^^^^^",
            "  File \"/app/saleor/graphql/account/schema.py\", line 255, in resolve_permission_group",
            "    _, id = from_global_id_or_error(id, Group)",
            "            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/app/saleor/graphql/core/utils/__init__.py\", line 87, in from_global_id_or_error",
            "    raise GraphQLError(",
            "graphql.error.base.GraphQLError: Invalid ID: 00000000-0000-0000-0000-000000000000. Expected: Group."
          ]
        }
      }
    }
  ],
  "data": {
    "permissionGroup": null
  },
  "extensions": {
    "cost": {
      "requestedQueryCost": 1,
      "maximumAvailable": 50000
    }
  }
}
```
- **Actual:**
```json
{"errors": [{"message": "Invalid token. Create new one by using tokenCreate mutation.", "locations": [{"line": 1, "column": 9}], "path": ["permissionGroup"], "extensions": {"exception": {"code": "InvalidTokenError", "stacktrace": ["Traceback (most recent call last):", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executor.py\", line 452, in resolve_or_error", "    return executor.execute(resolve_fn, source, info, **args)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executors/sync.py\", line 16, in execute", "    return fn(*args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/decorators.py\", line 32, in wrapper", "    return func(info.context, *args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/decorators.py\", line 46, in wrapper", "    test_func(context)", "  File \"/app/saleor/graphql/decorators.py\", line 86, in check_perms", "    if not one_of_permissions_or_auth_filter_required(context, perms):", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 42, in one_of_permissions_or_auth_filter_required", "    perm_results = _get_result_of_permissions_checks(context, permissions)", "                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 60, in _get_result_of_permissions_checks", "    if requestor and permissions:", "       ^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 251, in inner", "    self._setup()", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 404, in _setup", "    self._wrapped = self._setupfunc()", "                    ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 94, in user", "    return get_user(request) or None", "           ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 84, in get_user", "    request._cached_user = cast(User | None, authenticate(request=request))", "                                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/views/decorators/debug.py\", line 75, in sensitive_variables_wrapper", "    return func(*func_args, **func_kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/contrib/auth/__init__.py\", line 114, in authenticate", "    user = backend.authenticate(request, **credentials)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 51, in authenticate", "    return load_user_from_request(request)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 151, in load_user_from_request", "    raise jwt.InvalidTokenError(", "jwt.exceptions.InvalidTokenError: Invalid token. Create new one by using tokenCreate mutation."]}}}], "data": {"permissionGroup": null}, "extensions": {"cost": {"requestedQueryCost": 1, "maximumAvailable": 50000}}}
```
- Error: Invalid token. Create new one by using tokenCreate mutation.

### stock (QUERY)
- Status: fail, Match: mismatch, Outcome: auth_error
- Diff: Expected family not_found (not_found), got rejection (auth_error)
- **Request:**
```graphql
query { stock(id: "00000000-0000-0000-0000-000000000000") { id } }
```
- **Expected (golden):**
```json
{
  "errors": [
    {
      "message": "Invalid ID: 00000000-0000-0000-0000-000000000000. Expected: Stock.",
      "locations": [
        {
          "line": 1,
          "column": 9
        }
      ],
      "path": [
        "stock"
      ],
      "extensions": {
        "exception": {
          "code": "GraphQLError",
          "stacktrace": [
            "Traceback (most recent call last):",
            "  File \"/app/saleor/graphql/core/utils/__init__.py\", line 80, in from_global_id_or_error",
            "    type_, id_ = graphene.Node.from_global_id(global_id)",
            "                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/usr/local/lib/python3.12/site-packages/graphene/relay/node.py\", line 115, in from_global_id",
            "    return from_global_id(global_id)",
            "           ^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/usr/local/lib/python3.12/site-packages/graphql_relay/node/node.py\", line 66, in from_global_id",
            "    unbased_global_id = unbase64(global_id)",
            "                        ^^^^^^^^^^^^^^^^^^^",
            "  File \"/usr/local/lib/python3.12/site-packages/graphql_relay/utils.py\", line 11, in unbase64",
            "    return _unbase64(s).decode('utf-8')",
            "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "UnicodeDecodeError: 'utf-8' codec can't decode byte 0xd3 in position 0: invalid continuation byte",
            "",
            "The above exception was the direct cause of the following exception:",
            "Traceback (most recent call last):",
            "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executor.py\", line 452, in resolve_or_error",
            "    return executor.execute(resolve_fn, source, info, **args)",
            "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executors/sync.py\", line 16, in execute",
            "    return fn(*args, **kwargs)",
            "           ^^^^^^^^^^^^^^^^^^^",
            "  File \"/app/saleor/graphql/decorators.py\", line 32, in wrapper",
            "    return func(info.context, *args, **kwargs)",
            "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/app/saleor/graphql/decorators.py\", line 47, in wrapper",
            "    return f(*args, **kwargs)",
            "           ^^^^^^^^^^^^^^^^^^",
            "  File \"/app/saleor/graphql/warehouse/schema.py\", line 105, in resolve_stock",
            "    _, id = from_global_id_or_error(id, Stock)",
            "            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/app/saleor/graphql/core/utils/__init__.py\", line 87, in from_global_id_or_error",
            "    raise GraphQLError(",
            "graphql.error.base.GraphQLError: Invalid ID: 00000000-0000-0000-0000-000000000000. Expected: Stock."
          ]
        }
      }
    }
  ],
  "data": {
    "stock": null
  },
  "extensions": {
    "cost": {
      "requestedQueryCost": 1,
      "maximumAvailable": 50000
    }
  }
}
```
- **Actual:**
```json
{"errors": [{"message": "Invalid token. Create new one by using tokenCreate mutation.", "locations": [{"line": 1, "column": 9}], "path": ["stock"], "extensions": {"exception": {"code": "InvalidTokenError", "stacktrace": ["Traceback (most recent call last):", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executor.py\", line 452, in resolve_or_error", "    return executor.execute(resolve_fn, source, info, **args)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executors/sync.py\", line 16, in execute", "    return fn(*args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/decorators.py\", line 32, in wrapper", "    return func(info.context, *args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/decorators.py\", line 46, in wrapper", "    test_func(context)", "  File \"/app/saleor/graphql/decorators.py\", line 86, in check_perms", "    if not one_of_permissions_or_auth_filter_required(context, perms):", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 42, in one_of_permissions_or_auth_filter_required", "    perm_results = _get_result_of_permissions_checks(context, permissions)", "                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 60, in _get_result_of_permissions_checks", "    if requestor and permissions:", "       ^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 251, in inner", "    self._setup()", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 404, in _setup", "    self._wrapped = self._setupfunc()", "                    ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 94, in user", "    return get_user(request) or None", "           ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 84, in get_user", "    request._cached_user = cast(User | None, authenticate(request=request))", "                                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/views/decorators/debug.py\", line 75, in sensitive_variables_wrapper", "    return func(*func_args, **func_kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/contrib/auth/__init__.py\", line 114, in authenticate", "    user = backend.authenticate(request, **credentials)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 51, in authenticate", "    return load_user_from_request(request)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 151, in load_user_from_request", "    raise jwt.InvalidTokenError(", "jwt.exceptions.InvalidTokenError: Invalid token. Create new one by using tokenCreate mutation."]}}}], "data": {"stock": null}, "extensions": {"cost": {"requestedQueryCost": 1, "maximumAvailable": 50000}}}
```
- Error: Invalid token. Create new one by using tokenCreate mutation.

### permissionGroups (QUERY)
- Status: fail, Match: mismatch, Outcome: auth_error
- Diff: Expected family success (success), got rejection (auth_error)
- **Request:**
```graphql
query { permissionGroups(first: 1) { edges { node { id } } } }
```
- **Expected (golden):**
```json
{
  "data": {
    "permissionGroups": {
      "edges": []
    }
  },
  "extensions": {
    "cost": {
      "requestedQueryCost": 1,
      "maximumAvailable": 50000
    }
  }
}
```
- **Actual:**
```json
{"errors": [{"message": "Invalid token. Create new one by using tokenCreate mutation.", "locations": [{"line": 1, "column": 9}], "path": ["permissionGroups"], "extensions": {"exception": {"code": "InvalidTokenError", "stacktrace": ["Traceback (most recent call last):", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executor.py\", line 452, in resolve_or_error", "    return executor.execute(resolve_fn, source, info, **args)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executors/sync.py\", line 16, in execute", "    return fn(*args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/core/fields.py\", line 158, in new_resolver", "    return wrapped_resolver(obj, info, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/decorators.py\", line 32, in wrapper", "    return func(info.context, *args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/decorators.py\", line 46, in wrapper", "    test_func(context)", "  File \"/app/saleor/graphql/decorators.py\", line 86, in check_perms", "    if not one_of_permissions_or_auth_filter_required(context, perms):", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 42, in one_of_permissions_or_auth_filter_required", "    perm_results = _get_result_of_permissions_checks(context, permissions)", "                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 60, in _get_result_of_permissions_checks", "    if requestor and permissions:", "       ^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 251, in inner", "    self._setup()", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 404, in _setup", "    self._wrapped = self._setupfunc()", "                    ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 94, in user", "    return get_user(request) or None", "           ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 84, in get_user", "    request._cached_user = cast(User | None, authenticate(request=request))", "                                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/views/decorators/debug.py\", line 75, in sensitive_variables_wrapper", "    return func(*func_args, **func_kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/contrib/auth/__init__.py\", line 114, in authenticate", "    user = backend.authenticate(request, **credentials)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 51, in authenticate", "    return load_user_from_request(request)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 151, in load_user_from_request", "    raise jwt.InvalidTokenError(", "jwt.exceptions.InvalidTokenError: Invalid token. Create new one by using tokenCreate mutation."]}}}], "data": {"permissionGroups": null}, "extensions": {"cost": {"requestedQueryCost": 1, "maximumAvailable": 50000}}}
```
- Error: Invalid token. Create new one by using tokenCreate mutation.

### stocks (QUERY)
- Status: fail, Match: mismatch, Outcome: auth_error
- Diff: Expected family success (success), got rejection (auth_error)
- **Request:**
```graphql
query { stocks(first: 1) { edges { node { id } } } }
```
- **Expected (golden):**
```json
{
  "data": {
    "stocks": {
      "edges": []
    }
  },
  "extensions": {
    "cost": {
      "requestedQueryCost": 1,
      "maximumAvailable": 50000
    }
  }
}
```
- **Actual:**
```json
{"errors": [{"message": "Invalid token. Create new one by using tokenCreate mutation.", "locations": [{"line": 1, "column": 9}], "path": ["stocks"], "extensions": {"exception": {"code": "InvalidTokenError", "stacktrace": ["Traceback (most recent call last):", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executor.py\", line 452, in resolve_or_error", "    return executor.execute(resolve_fn, source, info, **args)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executors/sync.py\", line 16, in execute", "    return fn(*args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/core/fields.py\", line 158, in new_resolver", "    return wrapped_resolver(obj, info, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/decorators.py\", line 32, in wrapper", "    return func(info.context, *args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/decorators.py\", line 46, in wrapper", "    test_func(context)", "  File \"/app/saleor/graphql/decorators.py\", line 86, in check_perms", "    if not one_of_permissions_or_auth_filter_required(context, perms):", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 42, in one_of_permissions_or_auth_filter_required", "    perm_results = _get_result_of_permissions_checks(context, permissions)", "                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 60, in _get_result_of_permissions_checks", "    if requestor and permissions:", "       ^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 251, in inner", "    self._setup()", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 404, in _setup", "    self._wrapped = self._setupfunc()", "                    ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 94, in user", "    return get_user(request) or None", "           ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 84, in get_user", "    request._cached_user = cast(User | None, authenticate(request=request))", "                                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/views/decorators/debug.py\", line 75, in sensitive_variables_wrapper", "    return func(*func_args, **func_kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/contrib/auth/__init__.py\", line 114, in authenticate", "    user = backend.authenticate(request, **credentials)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 51, in authenticate", "    return load_user_from_request(request)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 151, in load_user_from_request", "    raise jwt.InvalidTokenError(", "jwt.exceptions.InvalidTokenError: Invalid token. Create new one by using tokenCreate mutation."]}}}], "data": {"stocks": null}, "extensions": {"cost": {"requestedQueryCost": 1, "maximumAvailable": 50000}}}
```
- Error: Invalid token. Create new one by using tokenCreate mutation.

### plugin (QUERY)
- Status: fail, Match: mismatch, Outcome: auth_error
- Diff: Expected family success (success), got rejection (auth_error)
- **Request:**
```graphql
query { plugin(id: "00000000-0000-0000-0000-000000000000") { id } }
```
- **Expected (golden):**
```json
{
  "data": {
    "plugin": null
  },
  "extensions": {
    "cost": {
      "requestedQueryCost": 1,
      "maximumAvailable": 50000
    }
  }
}
```
- **Actual:**
```json
{"errors": [{"message": "Invalid token. Create new one by using tokenCreate mutation.", "locations": [{"line": 1, "column": 9}], "path": ["plugin"], "extensions": {"exception": {"code": "InvalidTokenError", "stacktrace": ["Traceback (most recent call last):", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executor.py\", line 452, in resolve_or_error", "    return executor.execute(resolve_fn, source, info, **args)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executors/sync.py\", line 16, in execute", "    return fn(*args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/decorators.py\", line 32, in wrapper", "    return func(info.context, *args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/decorators.py\", line 46, in wrapper", "    test_func(context)", "  File \"/app/saleor/graphql/decorators.py\", line 86, in check_perms", "    if not one_of_permissions_or_auth_filter_required(context, perms):", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 42, in one_of_permissions_or_auth_filter_required", "    perm_results = _get_result_of_permissions_checks(context, permissions)", "                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 60, in _get_result_of_permissions_checks", "    if requestor and permissions:", "       ^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 251, in inner", "    self._setup()", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 404, in _setup", "    self._wrapped = self._setupfunc()", "                    ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 94, in user", "    return get_user(request) or None", "           ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 84, in get_user", "    request._cached_user = cast(User | None, authenticate(request=request))", "                                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/views/decorators/debug.py\", line 75, in sensitive_variables_wrapper", "    return func(*func_args, **func_kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/contrib/auth/__init__.py\", line 114, in authenticate", "    user = backend.authenticate(request, **credentials)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 51, in authenticate", "    return load_user_from_request(request)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 151, in load_user_from_request", "    raise jwt.InvalidTokenError(", "jwt.exceptions.InvalidTokenError: Invalid token. Create new one by using tokenCreate mutation."]}}}], "data": {"plugin": null}, "extensions": {"cost": {"requestedQueryCost": 1, "maximumAvailable": 50000}}}
```
- Error: Invalid token. Create new one by using tokenCreate mutation.

### warehouse (QUERY)
- Status: fail, Match: mismatch, Outcome: auth_error
- Diff: Expected family not_found (not_found), got rejection (auth_error)
- **Request:**
```graphql
query { warehouse(id: "00000000-0000-0000-0000-000000000000") { id } }
```
- **Expected (golden):**
```json
{
  "errors": [
    {
      "message": "Invalid ID: 00000000-0000-0000-0000-000000000000. Expected: Warehouse.",
      "locations": [
        {
          "line": 1,
          "column": 9
        }
      ],
      "path": [
        "warehouse"
      ],
      "extensions": {
        "exception": {
          "code": "GraphQLError",
          "stacktrace": [
            "Traceback (most recent call last):",
            "  File \"/app/saleor/graphql/core/utils/__init__.py\", line 80, in from_global_id_or_error",
            "    type_, id_ = graphene.Node.from_global_id(global_id)",
            "                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/usr/local/lib/python3.12/site-packages/graphene/relay/node.py\", line 115, in from_global_id",
            "    return from_global_id(global_id)",
            "           ^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/usr/local/lib/python3.12/site-packages/graphql_relay/node/node.py\", line 66, in from_global_id",
            "    unbased_global_id = unbase64(global_id)",
            "                        ^^^^^^^^^^^^^^^^^^^",
            "  File \"/usr/local/lib/python3.12/site-packages/graphql_relay/utils.py\", line 11, in unbase64",
            "    return _unbase64(s).decode('utf-8')",
            "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "UnicodeDecodeError: 'utf-8' codec can't decode byte 0xd3 in position 0: invalid continuation byte",
            "",
            "The above exception was the direct cause of the following exception:",
            "Traceback (most recent call last):",
            "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executor.py\", line 452, in resolve_or_error",
            "    return executor.execute(resolve_fn, source, info, **args)",
            "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executors/sync.py\", line 16, in execute",
            "    return fn(*args, **kwargs)",
            "           ^^^^^^^^^^^^^^^^^^^",
            "  File \"/app/saleor/graphql/decorators.py\", line 32, in wrapper",
            "    return func(info.context, *args, **kwargs)",
            "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/app/saleor/graphql/decorators.py\", line 47, in wrapper",
            "    return f(*args, **kwargs)",
            "           ^^^^^^^^^^^^^^^^^^",
            "  File \"/app/saleor/graphql/warehouse/schema.py\", line 66, in resolve_warehouse",
            "    return resolve_by_global_id_or_ext_ref(",
            "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/app/saleor/graphql/core/utils/resolvers.py\", line 9, in resolve_by_global_id_or_ext_ref",
            "    _, id = from_global_id_or_error(id, model.__name__)",
            "            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/app/saleor/graphql/core/utils/__init__.py\", line 87, in from_global_id_or_error",
            "    raise GraphQLError(",
            "graphql.error.base.GraphQLError: Invalid ID: 00000000-0000-0000-0000-000000000000. Expected: Warehouse."
          ]
        }
      }
    }
  ],
  "data": {
    "warehouse": null
  },
  "extensions": {
    "cost": {
      "requestedQueryCost": 1,
      "maximumAvailable": 50000
    }
  }
}
```
- **Actual:**
```json
{"errors": [{"message": "Invalid token. Create new one by using tokenCreate mutation.", "locations": [{"line": 1, "column": 9}], "path": ["warehouse"], "extensions": {"exception": {"code": "InvalidTokenError", "stacktrace": ["Traceback (most recent call last):", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executor.py\", line 452, in resolve_or_error", "    return executor.execute(resolve_fn, source, info, **args)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executors/sync.py\", line 16, in execute", "    return fn(*args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/decorators.py\", line 32, in wrapper", "    return func(info.context, *args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/decorators.py\", line 46, in wrapper", "    test_func(context)", "  File \"/app/saleor/graphql/decorators.py\", line 86, in check_perms", "    if not one_of_permissions_or_auth_filter_required(context, perms):", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 42, in one_of_permissions_or_auth_filter_required", "    perm_results = _get_result_of_permissions_checks(context, permissions)", "                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 60, in _get_result_of_permissions_checks", "    if requestor and permissions:", "       ^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 251, in inner", "    self._setup()", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 404, in _setup", "    self._wrapped = self._setupfunc()", "                    ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 94, in user", "    return get_user(request) or None", "           ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 84, in get_user", "    request._cached_user = cast(User | None, authenticate(request=request))", "                                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/views/decorators/debug.py\", line 75, in sensitive_variables_wrapper", "    return func(*func_args, **func_kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/contrib/auth/__init__.py\", line 114, in authenticate", "    user = backend.authenticate(request, **credentials)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 51, in authenticate", "    return load_user_from_request(request)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 151, in load_user_from_request", "    raise jwt.InvalidTokenError(", "jwt.exceptions.InvalidTokenError: Invalid token. Create new one by using tokenCreate mutation."]}}}], "data": {"warehouse": null}, "extensions": {"cost": {"requestedQueryCost": 1, "maximumAvailable": 50000}}}
```
- Error: Invalid token. Create new one by using tokenCreate mutation.

### appsInstallations (QUERY)
- Status: fail, Match: mismatch, Outcome: auth_error
- Diff: Expected family success (success), got rejection (auth_error)
- **Request:**
```graphql
query { appsInstallations { __typename } }
```
- **Expected (golden):**
```json
{
  "data": {
    "appsInstallations": []
  },
  "extensions": {
    "cost": {
      "requestedQueryCost": 1,
      "maximumAvailable": 50000
    }
  }
}
```
- **Actual:**
```json
{"errors": [{"message": "Invalid token. Create new one by using tokenCreate mutation.", "locations": [{"line": 1, "column": 9}], "path": ["appsInstallations"], "extensions": {"exception": {"code": "InvalidTokenError", "stacktrace": ["Traceback (most recent call last):", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executor.py\", line 452, in resolve_or_error", "    return executor.execute(resolve_fn, source, info, **args)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executors/sync.py\", line 16, in execute", "    return fn(*args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/decorators.py\", line 32, in wrapper", "    return func(info.context, *args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/decorators.py\", line 46, in wrapper", "    test_func(context)", "  File \"/app/saleor/graphql/decorators.py\", line 86, in check_perms", "    if not one_of_permissions_or_auth_filter_required(context, perms):", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 42, in one_of_permissions_or_auth_filter_required", "    perm_results = _get_result_of_permissions_checks(context, permissions)", "                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 60, in _get_result_of_permissions_checks", "    if requestor and permissions:", "       ^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 251, in inner", "    self._setup()", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 404, in _setup", "    self._wrapped = self._setupfunc()", "                    ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 94, in user", "    return get_user(request) or None", "           ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 84, in get_user", "    request._cached_user = cast(User | None, authenticate(request=request))", "                                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/views/decorators/debug.py\", line 75, in sensitive_variables_wrapper", "    return func(*func_args, **func_kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/contrib/auth/__init__.py\", line 114, in authenticate", "    user = backend.authenticate(request, **credentials)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 51, in authenticate", "    return load_user_from_request(request)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 151, in load_user_from_request", "    raise jwt.InvalidTokenError(", "jwt.exceptions.InvalidTokenError: Invalid token. Create new one by using tokenCreate mutation."]}}}], "data": null, "extensions": {"cost": {"requestedQueryCost": 1, "maximumAvailable": 50000}}}
```
- Error: Invalid token. Create new one by using tokenCreate mutation.

### plugins (QUERY)
- Status: fail, Match: mismatch, Outcome: auth_error
- Diff: Expected family success (success), got rejection (auth_error)
- **Request:**
```graphql
query { plugins(first: 1) { edges { node { id } } } }
```
- **Expected (golden):**
```json
{
  "data": {
    "plugins": {
      "edges": [
        {
          "node": {
            "id": "mirumee.notifications.admin_email"
          }
        }
      ]
    }
  },
  "extensions": {
    "cost": {
      "requestedQueryCost": 1,
      "maximumAvailable": 50000
    }
  }
}
```
- **Actual:**
```json
{"errors": [{"message": "Invalid token. Create new one by using tokenCreate mutation.", "locations": [{"line": 1, "column": 9}], "path": ["plugins"], "extensions": {"exception": {"code": "InvalidTokenError", "stacktrace": ["Traceback (most recent call last):", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executor.py\", line 452, in resolve_or_error", "    return executor.execute(resolve_fn, source, info, **args)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executors/sync.py\", line 16, in execute", "    return fn(*args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/decorators.py\", line 32, in wrapper", "    return func(info.context, *args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/decorators.py\", line 46, in wrapper", "    test_func(context)", "  File \"/app/saleor/graphql/decorators.py\", line 86, in check_perms", "    if not one_of_permissions_or_auth_filter_required(context, perms):", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 42, in one_of_permissions_or_auth_filter_required", "    perm_results = _get_result_of_permissions_checks(context, permissions)", "                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 60, in _get_result_of_permissions_checks", "    if requestor and permissions:", "       ^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 251, in inner", "    self._setup()", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 404, in _setup", "    self._wrapped = self._setupfunc()", "                    ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 94, in user", "    return get_user(request) or None", "           ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 84, in get_user", "    request._cached_user = cast(User | None, authenticate(request=request))", "                                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/views/decorators/debug.py\", line 75, in sensitive_variables_wrapper", "    return func(*func_args, **func_kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/contrib/auth/__init__.py\", line 114, in authenticate", "    user = backend.authenticate(request, **credentials)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 51, in authenticate", "    return load_user_from_request(request)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 151, in load_user_from_request", "    raise jwt.InvalidTokenError(", "jwt.exceptions.InvalidTokenError: Invalid token. Create new one by using tokenCreate mutation."]}}}], "data": {"plugins": null}, "extensions": {"cost": {"requestedQueryCost": 1, "maximumAvailable": 50000}}}
```
- Error: Invalid token. Create new one by using tokenCreate mutation.

### warehouses (QUERY)
- Status: fail, Match: mismatch, Outcome: auth_error
- Diff: Expected family success (success), got rejection (auth_error)
- **Request:**
```graphql
query { warehouses(first: 1) { edges { node { id } } } }
```
- **Expected (golden):**
```json
{
  "data": {
    "warehouses": {
      "edges": [
        {
          "node": {
            "id": "V2FyZWhvdXNlOmM0ZjMxMjYwLTk1YzEtNDIyOC1iMTdkLTM5YWU3ZDE5NmQ5Yg=="
          }
        }
      ]
    }
  },
  "extensions": {
    "cost": {
      "requestedQueryCost": 1,
      "maximumAvailable": 50000
    }
  }
}
```
- **Actual:**
```json
{"errors": [{"message": "Invalid token. Create new one by using tokenCreate mutation.", "locations": [{"line": 1, "column": 9}], "path": ["warehouses"], "extensions": {"exception": {"code": "InvalidTokenError", "stacktrace": ["Traceback (most recent call last):", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executor.py\", line 452, in resolve_or_error", "    return executor.execute(resolve_fn, source, info, **args)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executors/sync.py\", line 16, in execute", "    return fn(*args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/core/fields.py\", line 158, in new_resolver", "    return wrapped_resolver(obj, info, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/decorators.py\", line 32, in wrapper", "    return func(info.context, *args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/decorators.py\", line 46, in wrapper", "    test_func(context)", "  File \"/app/saleor/graphql/decorators.py\", line 86, in check_perms", "    if not one_of_permissions_or_auth_filter_required(context, perms):", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 42, in one_of_permissions_or_auth_filter_required", "    perm_results = _get_result_of_permissions_checks(context, permissions)", "                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 60, in _get_result_of_permissions_checks", "    if requestor and permissions:", "       ^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 251, in inner", "    self._setup()", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 404, in _setup", "    self._wrapped = self._setupfunc()", "                    ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 94, in user", "    return get_user(request) or None", "           ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 84, in get_user", "    request._cached_user = cast(User | None, authenticate(request=request))", "                                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/views/decorators/debug.py\", line 75, in sensitive_variables_wrapper", "    return func(*func_args, **func_kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/contrib/auth/__init__.py\", line 114, in authenticate", "    user = backend.authenticate(request, **credentials)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 51, in authenticate", "    return load_user_from_request(request)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 151, in load_user_from_request", "    raise jwt.InvalidTokenError(", "jwt.exceptions.InvalidTokenError: Invalid token. Create new one by using tokenCreate mutation."]}}}], "data": {"warehouses": null}, "extensions": {"cost": {"requestedQueryCost": 1, "maximumAvailable": 50000}}}
```
- Error: Invalid token. Create new one by using tokenCreate mutation.

### apps (QUERY)
- Status: fail, Match: mismatch, Outcome: auth_error
- Diff: Expected family success (success), got rejection (auth_error)
- **Request:**
```graphql
query { apps(first: 1) { edges { node { id } } } }
```
- **Expected (golden):**
```json
{
  "data": {
    "apps": {
      "edges": []
    }
  },
  "extensions": {
    "cost": {
      "requestedQueryCost": 1,
      "maximumAvailable": 50000
    }
  }
}
```
- **Actual:**
```json
{"errors": [{"message": "Invalid token. Create new one by using tokenCreate mutation.", "locations": [{"line": 1, "column": 9}], "path": ["apps"], "extensions": {"exception": {"code": "InvalidTokenError", "stacktrace": ["Traceback (most recent call last):", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executor.py\", line 452, in resolve_or_error", "    return executor.execute(resolve_fn, source, info, **args)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executors/sync.py\", line 16, in execute", "    return fn(*args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/core/fields.py\", line 158, in new_resolver", "    return wrapped_resolver(obj, info, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/decorators.py\", line 32, in wrapper", "    return func(info.context, *args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/decorators.py\", line 46, in wrapper", "    test_func(context)", "  File \"/app/saleor/graphql/decorators.py\", line 86, in check_perms", "    if not one_of_permissions_or_auth_filter_required(context, perms):", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 42, in one_of_permissions_or_auth_filter_required", "    perm_results = _get_result_of_permissions_checks(context, permissions)", "                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 60, in _get_result_of_permissions_checks", "    if requestor and permissions:", "       ^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 251, in inner", "    self._setup()", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 404, in _setup", "    self._wrapped = self._setupfunc()", "                    ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 94, in user", "    return get_user(request) or None", "           ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 84, in get_user", "    request._cached_user = cast(User | None, authenticate(request=request))", "                                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/views/decorators/debug.py\", line 75, in sensitive_variables_wrapper", "    return func(*func_args, **func_kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/contrib/auth/__init__.py\", line 114, in authenticate", "    user = backend.authenticate(request, **credentials)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 51, in authenticate", "    return load_user_from_request(request)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 151, in load_user_from_request", "    raise jwt.InvalidTokenError(", "jwt.exceptions.InvalidTokenError: Invalid token. Create new one by using tokenCreate mutation."]}}}], "data": {"apps": null}, "extensions": {"cost": {"requestedQueryCost": 1, "maximumAvailable": 50000}}}
```
- Error: Invalid token. Create new one by using tokenCreate mutation.

### giftCardSettingsUpdate (MUTATION)
- Status: fail, Match: mismatch, Outcome: auth_error
- Diff: Expected family success (success), got rejection (auth_error)
- **Request:**
```graphql
mutation { giftCardSettingsUpdate(input: {}) { errors { field message code } } }
```
- **Expected (golden):**
```json
{
  "data": {
    "giftCardSettingsUpdate": {
      "errors": []
    }
  },
  "extensions": {
    "cost": {
      "requestedQueryCost": 0,
      "maximumAvailable": 50000
    }
  }
}
```
- **Actual:**
```json
{"errors": [{"message": "Invalid token. Create new one by using tokenCreate mutation.", "locations": [{"line": 1, "column": 12}], "path": ["giftCardSettingsUpdate"], "extensions": {"exception": {"code": "InvalidTokenError", "stacktrace": ["Traceback (most recent call last):", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executor.py\", line 452, in resolve_or_error", "    return executor.execute(resolve_fn, source, info, **args)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executors/sync.py\", line 16, in execute", "    return fn(*args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/contextlib.py\", line 81, in inner", "    return func(*args, **kwds)", "           ^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/core/mutations.py\", line 520, in mutate", "    setup_context_user(info.context)", "  File \"/app/saleor/graphql/core/context.py\", line 66, in setup_context_user", "    context.user._setup()  # type: ignore[union-attr]", "    ^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 404, in _setup", "    self._wrapped = self._setupfunc()", "                    ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 94, in user", "    return get_user(request) or None", "           ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 84, in get_user", "    request._cached_user = cast(User | None, authenticate(request=request))", "                                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/views/decorators/debug.py\", line 75, in sensitive_variables_wrapper", "    return func(*func_args, **func_kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/contrib/auth/__init__.py\", line 114, in authenticate", "    user = backend.authenticate(request, **credentials)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 51, in authenticate", "    return load_user_from_request(request)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 151, in load_user_from_request", "    raise jwt.InvalidTokenError(", "jwt.exceptions.InvalidTokenError: Invalid token. Create new one by using tokenCreate mutation."]}}}], "data": {"giftCardSettingsUpdate": null}, "extensions": {"cost": {"requestedQueryCost": 0, "maximumAvailable": 50000}}}
```
- Error: Invalid token. Create new one by using tokenCreate mutation.

### giftCardSettings (QUERY)
- Status: fail, Match: mismatch, Outcome: auth_error
- Diff: Expected family success (success), got rejection (auth_error)
- **Request:**
```graphql
query { giftCardSettings { __typename } }
```
- **Expected (golden):**
```json
{
  "data": {
    "giftCardSettings": {
      "__typename": "GiftCardSettings"
    }
  },
  "extensions": {
    "cost": {
      "requestedQueryCost": 0,
      "maximumAvailable": 50000
    }
  }
}
```
- **Actual:**
```json
{"errors": [{"message": "Invalid token. Create new one by using tokenCreate mutation.", "locations": [{"line": 1, "column": 9}], "path": ["giftCardSettings"], "extensions": {"exception": {"code": "InvalidTokenError", "stacktrace": ["Traceback (most recent call last):", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executor.py\", line 452, in resolve_or_error", "    return executor.execute(resolve_fn, source, info, **args)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executors/sync.py\", line 16, in execute", "    return fn(*args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/decorators.py\", line 32, in wrapper", "    return func(info.context, *args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/decorators.py\", line 46, in wrapper", "    test_func(context)", "  File \"/app/saleor/graphql/decorators.py\", line 86, in check_perms", "    if not one_of_permissions_or_auth_filter_required(context, perms):", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 42, in one_of_permissions_or_auth_filter_required", "    perm_results = _get_result_of_permissions_checks(context, permissions)", "                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 60, in _get_result_of_permissions_checks", "    if requestor and permissions:", "       ^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 251, in inner", "    self._setup()", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 404, in _setup", "    self._wrapped = self._setupfunc()", "                    ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 94, in user", "    return get_user(request) or None", "           ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 84, in get_user", "    request._cached_user = cast(User | None, authenticate(request=request))", "                                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/views/decorators/debug.py\", line 75, in sensitive_variables_wrapper", "    return func(*func_args, **func_kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/contrib/auth/__init__.py\", line 114, in authenticate", "    user = backend.authenticate(request, **credentials)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 51, in authenticate", "    return load_user_from_request(request)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 151, in load_user_from_request", "    raise jwt.InvalidTokenError(", "jwt.exceptions.InvalidTokenError: Invalid token. Create new one by using tokenCreate mutation."]}}}], "data": null, "extensions": {"cost": {"requestedQueryCost": 0, "maximumAvailable": 50000}}}
```
- Error: Invalid token. Create new one by using tokenCreate mutation.

### checkouts (QUERY)
- Status: fail, Match: mismatch, Outcome: auth_error
- Diff: Expected family success (success), got rejection (auth_error)
- **Request:**
```graphql
query { checkouts(first: 1) { edges { node { id } } } }
```
- **Expected (golden):**
```json
{
  "data": {
    "checkouts": {
      "edges": []
    }
  },
  "extensions": {
    "cost": {
      "requestedQueryCost": 1,
      "maximumAvailable": 50000
    }
  }
}
```
- **Actual:**
```json
{"errors": [{"message": "Invalid token. Create new one by using tokenCreate mutation.", "locations": [{"line": 1, "column": 9}], "path": ["checkouts"], "extensions": {"exception": {"code": "InvalidTokenError", "stacktrace": ["Traceback (most recent call last):", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executor.py\", line 452, in resolve_or_error", "    return executor.execute(resolve_fn, source, info, **args)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executors/sync.py\", line 16, in execute", "    return fn(*args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/core/fields.py\", line 158, in new_resolver", "    return wrapped_resolver(obj, info, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/decorators.py\", line 32, in wrapper", "    return func(info.context, *args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/decorators.py\", line 46, in wrapper", "    test_func(context)", "  File \"/app/saleor/graphql/decorators.py\", line 86, in check_perms", "    if not one_of_permissions_or_auth_filter_required(context, perms):", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 42, in one_of_permissions_or_auth_filter_required", "    perm_results = _get_result_of_permissions_checks(context, permissions)", "                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 60, in _get_result_of_permissions_checks", "    if requestor and permissions:", "       ^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 251, in inner", "    self._setup()", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 404, in _setup", "    self._wrapped = self._setupfunc()", "                    ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 94, in user", "    return get_user(request) or None", "           ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 84, in get_user", "    request._cached_user = cast(User | None, authenticate(request=request))", "                                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/views/decorators/debug.py\", line 75, in sensitive_variables_wrapper", "    return func(*func_args, **func_kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/contrib/auth/__init__.py\", line 114, in authenticate", "    user = backend.authenticate(request, **credentials)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 51, in authenticate", "    return load_user_from_request(request)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 151, in load_user_from_request", "    raise jwt.InvalidTokenError(", "jwt.exceptions.InvalidTokenError: Invalid token. Create new one by using tokenCreate mutation."]}}}], "data": {"checkouts": null}, "extensions": {"cost": {"requestedQueryCost": 1, "maximumAvailable": 50000}}}
```
- Error: Invalid token. Create new one by using tokenCreate mutation.

### giftCardTags (QUERY)
- Status: fail, Match: mismatch, Outcome: auth_error
- Diff: Expected family success (success), got rejection (auth_error)
- **Request:**
```graphql
query { giftCardTags(first: 1) { edges { node { id } } } }
```
- **Expected (golden):**
```json
{
  "data": {
    "giftCardTags": {
      "edges": []
    }
  },
  "extensions": {
    "cost": {
      "requestedQueryCost": 1,
      "maximumAvailable": 50000
    }
  }
}
```
- **Actual:**
```json
{"errors": [{"message": "Invalid token. Create new one by using tokenCreate mutation.", "locations": [{"line": 1, "column": 9}], "path": ["giftCardTags"], "extensions": {"exception": {"code": "InvalidTokenError", "stacktrace": ["Traceback (most recent call last):", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executor.py\", line 452, in resolve_or_error", "    return executor.execute(resolve_fn, source, info, **args)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executors/sync.py\", line 16, in execute", "    return fn(*args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/core/fields.py\", line 158, in new_resolver", "    return wrapped_resolver(obj, info, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/decorators.py\", line 32, in wrapper", "    return func(info.context, *args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/decorators.py\", line 46, in wrapper", "    test_func(context)", "  File \"/app/saleor/graphql/decorators.py\", line 86, in check_perms", "    if not one_of_permissions_or_auth_filter_required(context, perms):", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 42, in one_of_permissions_or_auth_filter_required", "    perm_results = _get_result_of_permissions_checks(context, permissions)", "                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 60, in _get_result_of_permissions_checks", "    if requestor and permissions:", "       ^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 251, in inner", "    self._setup()", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 404, in _setup", "    self._wrapped = self._setupfunc()", "                    ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 94, in user", "    return get_user(request) or None", "           ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 84, in get_user", "    request._cached_user = cast(User | None, authenticate(request=request))", "                                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/views/decorators/debug.py\", line 75, in sensitive_variables_wrapper", "    return func(*func_args, **func_kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/contrib/auth/__init__.py\", line 114, in authenticate", "    user = backend.authenticate(request, **credentials)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 51, in authenticate", "    return load_user_from_request(request)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 151, in load_user_from_request", "    raise jwt.InvalidTokenError(", "jwt.exceptions.InvalidTokenError: Invalid token. Create new one by using tokenCreate mutation."]}}}], "data": {"giftCardTags": null}, "extensions": {"cost": {"requestedQueryCost": 1, "maximumAvailable": 50000}}}
```
- Error: Invalid token. Create new one by using tokenCreate mutation.

### giftCard (QUERY)
- Status: fail, Match: mismatch, Outcome: auth_error
- Diff: Expected family not_found (not_found), got rejection (auth_error)
- **Request:**
```graphql
query { giftCard(id: "00000000-0000-0000-0000-000000000000") { id } }
```
- **Expected (golden):**
```json
{
  "errors": [
    {
      "message": "Invalid ID: 00000000-0000-0000-0000-000000000000. Expected: GiftCard.",
      "locations": [
        {
          "line": 1,
          "column": 9
        }
      ],
      "path": [
        "giftCard"
      ],
      "extensions": {
        "exception": {
          "code": "GraphQLError",
          "stacktrace": [
            "Traceback (most recent call last):",
            "  File \"/app/saleor/graphql/core/utils/__init__.py\", line 80, in from_global_id_or_error",
            "    type_, id_ = graphene.Node.from_global_id(global_id)",
            "                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/usr/local/lib/python3.12/site-packages/graphene/relay/node.py\", line 115, in from_global_id",
            "    return from_global_id(global_id)",
            "           ^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/usr/local/lib/python3.12/site-packages/graphql_relay/node/node.py\", line 66, in from_global_id",
            "    unbased_global_id = unbase64(global_id)",
            "                        ^^^^^^^^^^^^^^^^^^^",
            "  File \"/usr/local/lib/python3.12/site-packages/graphql_relay/utils.py\", line 11, in unbase64",
            "    return _unbase64(s).decode('utf-8')",
            "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "UnicodeDecodeError: 'utf-8' codec can't decode byte 0xd3 in position 0: invalid continuation byte",
            "",
            "The above exception was the direct cause of the following exception:",
            "Traceback (most recent call last):",
            "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executor.py\", line 452, in resolve_or_error",
            "    return executor.execute(resolve_fn, source, info, **args)",
            "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executors/sync.py\", line 16, in execute",
            "    return fn(*args, **kwargs)",
            "           ^^^^^^^^^^^^^^^^^^^",
            "  File \"/app/saleor/graphql/decorators.py\", line 32, in wrapper",
            "    return func(info.context, *args, **kwargs)",
            "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/app/saleor/graphql/decorators.py\", line 47, in wrapper",
            "    return f(*args, **kwargs)",
            "           ^^^^^^^^^^^^^^^^^^",
            "  File \"/app/saleor/graphql/giftcard/schema.py\", line 87, in resolve_gift_card",
            "    _, id = from_global_id_or_error(id, GiftCard)",
            "            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/app/saleor/graphql/core/utils/__init__.py\", line 87, in from_global_id_or_error",
            "    raise GraphQLError(",
            "graphql.error.base.GraphQLError: Invalid ID: 00000000-0000-0000-0000-000000000000. Expected: GiftCard."
          ]
        }
      }
    }
  ],
  "data": {
    "giftCard": null
  },
  "extensions": {
    "cost": {
      "requestedQueryCost": 1,
      "maximumAvailable": 50000
    }
  }
}
```
- **Actual:**
```json
{"errors": [{"message": "Invalid token. Create new one by using tokenCreate mutation.", "locations": [{"line": 1, "column": 9}], "path": ["giftCard"], "extensions": {"exception": {"code": "InvalidTokenError", "stacktrace": ["Traceback (most recent call last):", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executor.py\", line 452, in resolve_or_error", "    return executor.execute(resolve_fn, source, info, **args)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executors/sync.py\", line 16, in execute", "    return fn(*args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/decorators.py\", line 32, in wrapper", "    return func(info.context, *args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/decorators.py\", line 46, in wrapper", "    test_func(context)", "  File \"/app/saleor/graphql/decorators.py\", line 86, in check_perms", "    if not one_of_permissions_or_auth_filter_required(context, perms):", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 42, in one_of_permissions_or_auth_filter_required", "    perm_results = _get_result_of_permissions_checks(context, permissions)", "                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 60, in _get_result_of_permissions_checks", "    if requestor and permissions:", "       ^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 251, in inner", "    self._setup()", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 404, in _setup", "    self._wrapped = self._setupfunc()", "                    ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 94, in user", "    return get_user(request) or None", "           ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 84, in get_user", "    request._cached_user = cast(User | None, authenticate(request=request))", "                                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/views/decorators/debug.py\", line 75, in sensitive_variables_wrapper", "    return func(*func_args, **func_kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/contrib/auth/__init__.py\", line 114, in authenticate", "    user = backend.authenticate(request, **credentials)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 51, in authenticate", "    return load_user_from_request(request)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 151, in load_user_from_request", "    raise jwt.InvalidTokenError(", "jwt.exceptions.InvalidTokenError: Invalid token. Create new one by using tokenCreate mutation."]}}}], "data": {"giftCard": null}, "extensions": {"cost": {"requestedQueryCost": 1, "maximumAvailable": 50000}}}
```
- Error: Invalid token. Create new one by using tokenCreate mutation.

### giftCards (QUERY)
- Status: fail, Match: mismatch, Outcome: auth_error
- Diff: Expected family success (success), got rejection (auth_error)
- **Request:**
```graphql
query { giftCards(first: 1) { edges { node { id } } } }
```
- **Expected (golden):**
```json
{
  "data": {
    "giftCards": {
      "edges": []
    }
  },
  "extensions": {
    "cost": {
      "requestedQueryCost": 1,
      "maximumAvailable": 50000
    }
  }
}
```
- **Actual:**
```json
{"errors": [{"message": "Invalid token. Create new one by using tokenCreate mutation.", "locations": [{"line": 1, "column": 9}], "path": ["giftCards"], "extensions": {"exception": {"code": "InvalidTokenError", "stacktrace": ["Traceback (most recent call last):", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executor.py\", line 452, in resolve_or_error", "    return executor.execute(resolve_fn, source, info, **args)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executors/sync.py\", line 16, in execute", "    return fn(*args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/core/fields.py\", line 158, in new_resolver", "    return wrapped_resolver(obj, info, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/decorators.py\", line 32, in wrapper", "    return func(info.context, *args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/decorators.py\", line 46, in wrapper", "    test_func(context)", "  File \"/app/saleor/graphql/decorators.py\", line 86, in check_perms", "    if not one_of_permissions_or_auth_filter_required(context, perms):", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 42, in one_of_permissions_or_auth_filter_required", "    perm_results = _get_result_of_permissions_checks(context, permissions)", "                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 60, in _get_result_of_permissions_checks", "    if requestor and permissions:", "       ^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 251, in inner", "    self._setup()", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 404, in _setup", "    self._wrapped = self._setupfunc()", "                    ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 94, in user", "    return get_user(request) or None", "           ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 84, in get_user", "    request._cached_user = cast(User | None, authenticate(request=request))", "                                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/views/decorators/debug.py\", line 75, in sensitive_variables_wrapper", "    return func(*func_args, **func_kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/contrib/auth/__init__.py\", line 114, in authenticate", "    user = backend.authenticate(request, **credentials)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 51, in authenticate", "    return load_user_from_request(request)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 151, in load_user_from_request", "    raise jwt.InvalidTokenError(", "jwt.exceptions.InvalidTokenError: Invalid token. Create new one by using tokenCreate mutation."]}}}], "data": {"giftCards": null}, "extensions": {"cost": {"requestedQueryCost": 1, "maximumAvailable": 50000}}}
```
- Error: Invalid token. Create new one by using tokenCreate mutation.

### collection (QUERY)
- Status: fail, Match: mismatch, Outcome: auth_error
- Diff: Expected family not_found (not_found), got rejection (auth_error)
- **Request:**
```graphql
query { collection(id: "00000000-0000-0000-0000-000000000000") { id } }
```
- **Expected (golden):**
```json
{
  "errors": [
    {
      "message": "Invalid ID: 00000000-0000-0000-0000-000000000000. Expected: Collection.",
      "locations": [
        {
          "line": 1,
          "column": 9
        }
      ],
      "path": [
        "collection"
      ],
      "extensions": {
        "exception": {
          "code": "GraphQLError",
          "stacktrace": [
            "Traceback (most recent call last):",
            "  File \"/app/saleor/graphql/core/utils/__init__.py\", line 80, in from_global_id_or_error",
            "    type_, id_ = graphene.Node.from_global_id(global_id)",
            "                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/usr/local/lib/python3.12/site-packages/graphene/relay/node.py\", line 115, in from_global_id",
            "    return from_global_id(global_id)",
            "           ^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/usr/local/lib/python3.12/site-packages/graphql_relay/node/node.py\", line 66, in from_global_id",
            "    unbased_global_id = unbase64(global_id)",
            "                        ^^^^^^^^^^^^^^^^^^^",
            "  File \"/usr/local/lib/python3.12/site-packages/graphql_relay/utils.py\", line 11, in unbase64",
            "    return _unbase64(s).decode('utf-8')",
            "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "UnicodeDecodeError: 'utf-8' codec can't decode byte 0xd3 in position 0: invalid continuation byte",
            "",
            "The above exception was the direct cause of the following exception:",
            "Traceback (most recent call last):",
            "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executor.py\", line 452, in resolve_or_error",
            "    return executor.execute(resolve_fn, source, info, **args)",
            "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executors/sync.py\", line 16, in execute",
            "    return fn(*args, **kwargs)",
            "           ^^^^^^^^^^^^^^^^^^^",
            "  File \"/app/saleor/graphql/core/tracing.py\", line 19, in wrapper",
            "    return func(*args, **kwargs)",
            "           ^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/app/saleor/graphql/product/schema.py\", line 390, in resolve_collection",
            "    _, id = from_global_id_or_error(id, Collection)",
            "            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/app/saleor/graphql/core/utils/__init__.py\", line 87, in from_global_id_or_error",
            "    raise GraphQLError(",
            "graphql.error.base.GraphQLError: Invalid ID: 00000000-0000-0000-0000-000000000000. Expected: Collection."
          ]
        }
      }
    }
  ],
  "data": {
    "collection": null
  },
  "extensions": {
    "cost": {
      "requestedQueryCost": 1,
      "maximumAvailable": 50000
    }
  }
}
```
- **Actual:**
```json
{"errors": [{"message": "Invalid token. Create new one by using tokenCreate mutation.", "locations": [{"line": 1, "column": 9}], "path": ["collection"], "extensions": {"exception": {"code": "InvalidTokenError", "stacktrace": ["Traceback (most recent call last):", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executor.py\", line 452, in resolve_or_error", "    return executor.execute(resolve_fn, source, info, **args)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executors/sync.py\", line 16, in execute", "    return fn(*args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/core/tracing.py\", line 19, in wrapper", "    return func(*args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/product/schema.py\", line 381, in resolve_collection", "    has_required_permissions = has_one_of_permissions(", "                               ^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 102, in has_one_of_permissions", "    if not requestor:", "           ^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 251, in inner", "    self._setup()", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 404, in _setup", "    self._wrapped = self._setupfunc()", "                    ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 94, in user", "    return get_user(request) or None", "           ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 84, in get_user", "    request._cached_user = cast(User | None, authenticate(request=request))", "                                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/views/decorators/debug.py\", line 75, in sensitive_variables_wrapper", "    return func(*func_args, **func_kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/contrib/auth/__init__.py\", line 114, in authenticate", "    user = backend.authenticate(request, **credentials)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 51, in authenticate", "    return load_user_from_request(request)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 151, in load_user_from_request", "    raise jwt.InvalidTokenError(", "jwt.exceptions.InvalidTokenError: Invalid token. Create new one by using tokenCreate mutation."]}}}], "data": {"collection": null}, "extensions": {"cost": {"requestedQueryCost": 1, "maximumAvailable": 50000}}}
```
- Error: Invalid token. Create new one by using tokenCreate mutation.

### collections (QUERY)
- Status: fail, Match: mismatch, Outcome: auth_error
- Diff: Expected family success (success), got rejection (auth_error)
- **Request:**
```graphql
query { collections(first: 1) { edges { node { id } } } }
```
- **Expected (golden):**
```json
{
  "data": {
    "collections": {
      "edges": []
    }
  },
  "extensions": {
    "cost": {
      "requestedQueryCost": 1,
      "maximumAvailable": 50000
    }
  }
}
```
- **Actual:**
```json
{"errors": [{"message": "Invalid token. Create new one by using tokenCreate mutation.", "locations": [{"line": 1, "column": 9}], "path": ["collections"], "extensions": {"exception": {"code": "InvalidTokenError", "stacktrace": ["Traceback (most recent call last):", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executor.py\", line 452, in resolve_or_error", "    return executor.execute(resolve_fn, source, info, **args)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executors/sync.py\", line 16, in execute", "    return fn(*args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/core/fields.py\", line 158, in new_resolver", "    return wrapped_resolver(obj, info, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/product/schema.py\", line 414, in resolve_collections", "    has_required_permissions = has_one_of_permissions(", "                               ^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 102, in has_one_of_permissions", "    if not requestor:", "           ^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 251, in inner", "    self._setup()", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 404, in _setup", "    self._wrapped = self._setupfunc()", "                    ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 94, in user", "    return get_user(request) or None", "           ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 84, in get_user", "    request._cached_user = cast(User | None, authenticate(request=request))", "                                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/views/decorators/debug.py\", line 75, in sensitive_variables_wrapper", "    return func(*func_args, **func_kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/contrib/auth/__init__.py\", line 114, in authenticate", "    user = backend.authenticate(request, **credentials)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 51, in authenticate", "    return load_user_from_request(request)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 151, in load_user_from_request", "    raise jwt.InvalidTokenError(", "jwt.exceptions.InvalidTokenError: Invalid token. Create new one by using tokenCreate mutation."]}}}], "data": {"collections": null}, "extensions": {"cost": {"requestedQueryCost": 1, "maximumAvailable": 50000}}}
```
- Error: Invalid token. Create new one by using tokenCreate mutation.

### me (QUERY)
- Status: fail, Match: mismatch, Outcome: auth_error
- Diff: Expected family success (success), got rejection (auth_error)
- **Request:**
```graphql
query { me { __typename } }
```
- **Expected (golden):**
```json
{
  "data": {
    "me": {
      "__typename": "User"
    }
  },
  "extensions": {
    "cost": {
      "requestedQueryCost": 1,
      "maximumAvailable": 50000
    }
  }
}
```
- **Actual:**
```json
{"errors": [{"message": "Invalid token. Create new one by using tokenCreate mutation.", "locations": [{"line": 1, "column": 9}], "path": ["me"], "extensions": {"exception": {"code": "InvalidTokenError", "stacktrace": ["Traceback (most recent call last):", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executor.py\", line 452, in resolve_or_error", "    return executor.execute(resolve_fn, source, info, **args)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executors/sync.py\", line 16, in execute", "    return fn(*args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/account/schema.py\", line 261, in resolve_me", "    return user if user else None", "                   ^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 251, in inner", "    self._setup()", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 404, in _setup", "    self._wrapped = self._setupfunc()", "                    ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 94, in user", "    return get_user(request) or None", "           ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 84, in get_user", "    request._cached_user = cast(User | None, authenticate(request=request))", "                                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/views/decorators/debug.py\", line 75, in sensitive_variables_wrapper", "    return func(*func_args, **func_kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/contrib/auth/__init__.py\", line 114, in authenticate", "    user = backend.authenticate(request, **credentials)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 51, in authenticate", "    return load_user_from_request(request)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 151, in load_user_from_request", "    raise jwt.InvalidTokenError(", "jwt.exceptions.InvalidTokenError: Invalid token. Create new one by using tokenCreate mutation."]}}}], "data": {"me": null}, "extensions": {"cost": {"requestedQueryCost": 1, "maximumAvailable": 50000}}}
```
- Error: Invalid token. Create new one by using tokenCreate mutation.

### attributes (QUERY)
- Status: fail, Match: mismatch, Outcome: auth_error
- Diff: Expected family success (success), got rejection (auth_error)
- **Request:**
```graphql
query { attributes(first: 1) { edges { node { id } } } }
```
- **Expected (golden):**
```json
{
  "data": {
    "attributes": {
      "edges": []
    }
  },
  "extensions": {
    "cost": {
      "requestedQueryCost": 1,
      "maximumAvailable": 50000
    }
  }
}
```
- **Actual:**
```json
{"errors": [{"message": "Invalid token. Create new one by using tokenCreate mutation.", "locations": [{"line": 1, "column": 9}], "path": ["attributes"], "extensions": {"exception": {"code": "InvalidTokenError", "stacktrace": ["Traceback (most recent call last):", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executor.py\", line 452, in resolve_or_error", "    return executor.execute(resolve_fn, source, info, **args)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executors/sync.py\", line 16, in execute", "    return fn(*args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/core/fields.py\", line 158, in new_resolver", "    return wrapped_resolver(obj, info, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/attribute/schema.py\", line 67, in resolve_attributes", "    qs = resolve_attributes(info)", "         ^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/attribute/resolvers.py\", line 10, in resolve_attributes", "    ).get_visible_to_user(requestor)", "      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/attribute/models/base.py\", line 42, in get_visible_to_user", "    if has_one_of_permissions(", "       ^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 102, in has_one_of_permissions", "    if not requestor:", "           ^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 251, in inner", "    self._setup()", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 404, in _setup", "    self._wrapped = self._setupfunc()", "                    ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 94, in user", "    return get_user(request) or None", "           ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 84, in get_user", "    request._cached_user = cast(User | None, authenticate(request=request))", "                                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/views/decorators/debug.py\", line 75, in sensitive_variables_wrapper", "    return func(*func_args, **func_kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/contrib/auth/__init__.py\", line 114, in authenticate", "    user = backend.authenticate(request, **credentials)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 51, in authenticate", "    return load_user_from_request(request)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 151, in load_user_from_request", "    raise jwt.InvalidTokenError(", "jwt.exceptions.InvalidTokenError: Invalid token. Create new one by using tokenCreate mutation."]}}}], "data": {"attributes": null}, "extensions": {"cost": {"requestedQueryCost": 1, "maximumAvailable": 50000}}}
```
- Error: Invalid token. Create new one by using tokenCreate mutation.

### customers (QUERY)
- Status: fail, Match: mismatch, Outcome: auth_error
- Diff: Expected family success (success), got rejection (auth_error)
- **Request:**
```graphql
query { customers(first: 1) { edges { node { id } } } }
```
- **Expected (golden):**
```json
{
  "data": {
    "customers": {
      "edges": []
    }
  },
  "extensions": {
    "cost": {
      "requestedQueryCost": 1,
      "maximumAvailable": 50000
    }
  }
}
```
- **Actual:**
```json
{"errors": [{"message": "Invalid token. Create new one by using tokenCreate mutation.", "locations": [{"line": 1, "column": 9}], "path": ["customers"], "extensions": {"exception": {"code": "InvalidTokenError", "stacktrace": ["Traceback (most recent call last):", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executor.py\", line 452, in resolve_or_error", "    return executor.execute(resolve_fn, source, info, **args)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executors/sync.py\", line 16, in execute", "    return fn(*args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/core/fields.py\", line 158, in new_resolver", "    return wrapped_resolver(obj, info, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/decorators.py\", line 32, in wrapper", "    return func(info.context, *args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/decorators.py\", line 46, in wrapper", "    test_func(context)", "  File \"/app/saleor/graphql/decorators.py\", line 86, in check_perms", "    if not one_of_permissions_or_auth_filter_required(context, perms):", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 42, in one_of_permissions_or_auth_filter_required", "    perm_results = _get_result_of_permissions_checks(context, permissions)", "                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 60, in _get_result_of_permissions_checks", "    if requestor and permissions:", "       ^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 251, in inner", "    self._setup()", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 404, in _setup", "    self._wrapped = self._setupfunc()", "                    ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 94, in user", "    return get_user(request) or None", "           ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 84, in get_user", "    request._cached_user = cast(User | None, authenticate(request=request))", "                                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/views/decorators/debug.py\", line 75, in sensitive_variables_wrapper", "    return func(*func_args, **func_kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/contrib/auth/__init__.py\", line 114, in authenticate", "    user = backend.authenticate(request, **credentials)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 51, in authenticate", "    return load_user_from_request(request)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 151, in load_user_from_request", "    raise jwt.InvalidTokenError(", "jwt.exceptions.InvalidTokenError: Invalid token. Create new one by using tokenCreate mutation."]}}}], "data": {"customers": null}, "extensions": {"cost": {"requestedQueryCost": 1, "maximumAvailable": 50000}}}
```
- Error: Invalid token. Create new one by using tokenCreate mutation.

### accountUpdate (MUTATION)
- Status: fail, Match: mismatch, Outcome: auth_error
- Diff: Expected family success (success), got rejection (auth_error)
- **Request:**
```graphql
mutation { accountUpdate(input: {}) { errors { field message code } } }
```
- **Expected (golden):**
```json
{
  "data": {
    "accountUpdate": {
      "errors": []
    }
  },
  "extensions": {
    "cost": {
      "requestedQueryCost": 0,
      "maximumAvailable": 50000
    }
  }
}
```
- **Actual:**
```json
{"errors": [{"message": "Invalid token. Create new one by using tokenCreate mutation.", "locations": [{"line": 1, "column": 12}], "path": ["accountUpdate"], "extensions": {"exception": {"code": "InvalidTokenError", "stacktrace": ["Traceback (most recent call last):", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executor.py\", line 452, in resolve_or_error", "    return executor.execute(resolve_fn, source, info, **args)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executors/sync.py\", line 16, in execute", "    return fn(*args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/contextlib.py\", line 81, in inner", "    return func(*args, **kwds)", "           ^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/core/mutations.py\", line 520, in mutate", "    setup_context_user(info.context)", "  File \"/app/saleor/graphql/core/context.py\", line 66, in setup_context_user", "    context.user._setup()  # type: ignore[union-attr]", "    ^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 404, in _setup", "    self._wrapped = self._setupfunc()", "                    ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 94, in user", "    return get_user(request) or None", "           ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 84, in get_user", "    request._cached_user = cast(User | None, authenticate(request=request))", "                                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/views/decorators/debug.py\", line 75, in sensitive_variables_wrapper", "    return func(*func_args, **func_kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/contrib/auth/__init__.py\", line 114, in authenticate", "    user = backend.authenticate(request, **credentials)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 51, in authenticate", "    return load_user_from_request(request)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 151, in load_user_from_request", "    raise jwt.InvalidTokenError(", "jwt.exceptions.InvalidTokenError: Invalid token. Create new one by using tokenCreate mutation."]}}}], "data": {"accountUpdate": null}, "extensions": {"cost": {"requestedQueryCost": 0, "maximumAvailable": 50000}}}
```
- Error: Invalid token. Create new one by using tokenCreate mutation.

### channels (QUERY)
- Status: fail, Match: mismatch, Outcome: auth_error
- Diff: Expected family success (success), got rejection (auth_error)
- **Request:**
```graphql
query { channels { __typename } }
```
- **Expected (golden):**
```json
{
  "data": {
    "channels": [
      {
        "__typename": "Channel"
      }
    ]
  },
  "extensions": {
    "cost": {
      "requestedQueryCost": 1,
      "maximumAvailable": 50000
    }
  }
}
```
- **Actual:**
```json
{"errors": [{"message": "Invalid token. Create new one by using tokenCreate mutation.", "locations": [{"line": 1, "column": 9}], "path": ["channels"], "extensions": {"exception": {"code": "InvalidTokenError", "stacktrace": ["Traceback (most recent call last):", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executor.py\", line 452, in resolve_or_error", "    return executor.execute(resolve_fn, source, info, **args)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executors/sync.py\", line 16, in execute", "    return fn(*args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/decorators.py\", line 32, in wrapper", "    return func(info.context, *args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/decorators.py\", line 46, in wrapper", "    test_func(context)", "  File \"/app/saleor/graphql/decorators.py\", line 86, in check_perms", "    if not one_of_permissions_or_auth_filter_required(context, perms):", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 42, in one_of_permissions_or_auth_filter_required", "    perm_results = _get_result_of_permissions_checks(context, permissions)", "                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 60, in _get_result_of_permissions_checks", "    if requestor and permissions:", "       ^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 251, in inner", "    self._setup()", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 404, in _setup", "    self._wrapped = self._setupfunc()", "                    ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 94, in user", "    return get_user(request) or None", "           ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 84, in get_user", "    request._cached_user = cast(User | None, authenticate(request=request))", "                                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/views/decorators/debug.py\", line 75, in sensitive_variables_wrapper", "    return func(*func_args, **func_kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/contrib/auth/__init__.py\", line 114, in authenticate", "    user = backend.authenticate(request, **credentials)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 51, in authenticate", "    return load_user_from_request(request)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 151, in load_user_from_request", "    raise jwt.InvalidTokenError(", "jwt.exceptions.InvalidTokenError: Invalid token. Create new one by using tokenCreate mutation."]}}}], "data": {"channels": null}, "extensions": {"cost": {"requestedQueryCost": 1, "maximumAvailable": 50000}}}
```
- Error: Invalid token. Create new one by using tokenCreate mutation.

### draftOrders (QUERY)
- Status: fail, Match: mismatch, Outcome: auth_error
- Diff: Expected family success (success), got rejection (auth_error)
- **Request:**
```graphql
query { draftOrders(first: 1) { edges { node { id } } } }
```
- **Expected (golden):**
```json
{
  "data": {
    "draftOrders": {
      "edges": []
    }
  },
  "extensions": {
    "cost": {
      "requestedQueryCost": 1,
      "maximumAvailable": 50000
    }
  }
}
```
- **Actual:**
```json
{"errors": [{"message": "Invalid token. Create new one by using tokenCreate mutation.", "locations": [{"line": 1, "column": 9}], "path": ["draftOrders"], "extensions": {"exception": {"code": "InvalidTokenError", "stacktrace": ["Traceback (most recent call last):", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executor.py\", line 452, in resolve_or_error", "    return executor.execute(resolve_fn, source, info, **args)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executors/sync.py\", line 16, in execute", "    return fn(*args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/core/fields.py\", line 158, in new_resolver", "    return wrapped_resolver(obj, info, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/decorators.py\", line 32, in wrapper", "    return func(info.context, *args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/decorators.py\", line 46, in wrapper", "    test_func(context)", "  File \"/app/saleor/graphql/decorators.py\", line 86, in check_perms", "    if not one_of_permissions_or_auth_filter_required(context, perms):", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 42, in one_of_permissions_or_auth_filter_required", "    perm_results = _get_result_of_permissions_checks(context, permissions)", "                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 60, in _get_result_of_permissions_checks", "    if requestor and permissions:", "       ^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 251, in inner", "    self._setup()", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 404, in _setup", "    self._wrapped = self._setupfunc()", "                    ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 94, in user", "    return get_user(request) or None", "           ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 84, in get_user", "    request._cached_user = cast(User | None, authenticate(request=request))", "                                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/views/decorators/debug.py\", line 75, in sensitive_variables_wrapper", "    return func(*func_args, **func_kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/contrib/auth/__init__.py\", line 114, in authenticate", "    user = backend.authenticate(request, **credentials)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 51, in authenticate", "    return load_user_from_request(request)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 151, in load_user_from_request", "    raise jwt.InvalidTokenError(", "jwt.exceptions.InvalidTokenError: Invalid token. Create new one by using tokenCreate mutation."]}}}], "data": {"draftOrders": null}, "extensions": {"cost": {"requestedQueryCost": 1, "maximumAvailable": 50000}}}
```
- Error: Invalid token. Create new one by using tokenCreate mutation.

### exportFile (QUERY)
- Status: fail, Match: mismatch, Outcome: auth_error
- Diff: Expected family not_found (not_found), got rejection (auth_error)
- **Request:**
```graphql
query { exportFile(id: "00000000-0000-0000-0000-000000000000") { id } }
```
- **Expected (golden):**
```json
{
  "errors": [
    {
      "message": "Invalid ID: 00000000-0000-0000-0000-000000000000. Expected: ExportFile.",
      "locations": [
        {
          "line": 1,
          "column": 9
        }
      ],
      "path": [
        "exportFile"
      ],
      "extensions": {
        "exception": {
          "code": "GraphQLError",
          "stacktrace": [
            "Traceback (most recent call last):",
            "  File \"/app/saleor/graphql/core/utils/__init__.py\", line 80, in from_global_id_or_error",
            "    type_, id_ = graphene.Node.from_global_id(global_id)",
            "                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/usr/local/lib/python3.12/site-packages/graphene/relay/node.py\", line 115, in from_global_id",
            "    return from_global_id(global_id)",
            "           ^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/usr/local/lib/python3.12/site-packages/graphql_relay/node/node.py\", line 66, in from_global_id",
            "    unbased_global_id = unbase64(global_id)",
            "                        ^^^^^^^^^^^^^^^^^^^",
            "  File \"/usr/local/lib/python3.12/site-packages/graphql_relay/utils.py\", line 11, in unbase64",
            "    return _unbase64(s).decode('utf-8')",
            "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "UnicodeDecodeError: 'utf-8' codec can't decode byte 0xd3 in position 0: invalid continuation byte",
            "",
            "The above exception was the direct cause of the following exception:",
            "Traceback (most recent call last):",
            "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executor.py\", line 452, in resolve_or_error",
            "    return executor.execute(resolve_fn, source, info, **args)",
            "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executors/sync.py\", line 16, in execute",
            "    return fn(*args, **kwargs)",
            "           ^^^^^^^^^^^^^^^^^^^",
            "  File \"/app/saleor/graphql/decorators.py\", line 32, in wrapper",
            "    return func(info.context, *args, **kwargs)",
            "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/app/saleor/graphql/decorators.py\", line 47, in wrapper",
            "    return f(*args, **kwargs)",
            "           ^^^^^^^^^^^^^^^^^^",
            "  File \"/app/saleor/graphql/csv/schema.py\", line 34, in resolve_export_file",
            "    _, id = from_global_id_or_error(id, ExportFile)",
            "            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/app/saleor/graphql/core/utils/__init__.py\", line 87, in from_global_id_or_error",
            "    raise GraphQLError(",
            "graphql.error.base.GraphQLError: Invalid ID: 00000000-0000-0000-0000-000000000000. Expected: ExportFile."
          ]
        }
      }
    }
  ],
  "data": {
    "exportFile": null
  },
  "extensions": {
    "cost": {
      "requestedQueryCost": 1,
      "maximumAvailable": 50000
    }
  }
}
```
- **Actual:**
```json
{"errors": [{"message": "Invalid token. Create new one by using tokenCreate mutation.", "locations": [{"line": 1, "column": 9}], "path": ["exportFile"], "extensions": {"exception": {"code": "InvalidTokenError", "stacktrace": ["Traceback (most recent call last):", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executor.py\", line 452, in resolve_or_error", "    return executor.execute(resolve_fn, source, info, **args)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executors/sync.py\", line 16, in execute", "    return fn(*args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/decorators.py\", line 32, in wrapper", "    return func(info.context, *args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/decorators.py\", line 46, in wrapper", "    test_func(context)", "  File \"/app/saleor/graphql/decorators.py\", line 86, in check_perms", "    if not one_of_permissions_or_auth_filter_required(context, perms):", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 42, in one_of_permissions_or_auth_filter_required", "    perm_results = _get_result_of_permissions_checks(context, permissions)", "                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 60, in _get_result_of_permissions_checks", "    if requestor and permissions:", "       ^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 251, in inner", "    self._setup()", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 404, in _setup", "    self._wrapped = self._setupfunc()", "                    ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 94, in user", "    return get_user(request) or None", "           ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 84, in get_user", "    request._cached_user = cast(User | None, authenticate(request=request))", "                                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/views/decorators/debug.py\", line 75, in sensitive_variables_wrapper", "    return func(*func_args, **func_kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/contrib/auth/__init__.py\", line 114, in authenticate", "    user = backend.authenticate(request, **credentials)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 51, in authenticate", "    return load_user_from_request(request)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 151, in load_user_from_request", "    raise jwt.InvalidTokenError(", "jwt.exceptions.InvalidTokenError: Invalid token. Create new one by using tokenCreate mutation."]}}}], "data": {"exportFile": null}, "extensions": {"cost": {"requestedQueryCost": 1, "maximumAvailable": 50000}}}
```
- Error: Invalid token. Create new one by using tokenCreate mutation.

### exportFiles (QUERY)
- Status: fail, Match: mismatch, Outcome: auth_error
- Diff: Expected family success (success), got rejection (auth_error)
- **Request:**
```graphql
query { exportFiles(first: 1) { edges { node { id } } } }
```
- **Expected (golden):**
```json
{
  "data": {
    "exportFiles": {
      "edges": []
    }
  },
  "extensions": {
    "cost": {
      "requestedQueryCost": 1,
      "maximumAvailable": 50000
    }
  }
}
```
- **Actual:**
```json
{"errors": [{"message": "Invalid token. Create new one by using tokenCreate mutation.", "locations": [{"line": 1, "column": 9}], "path": ["exportFiles"], "extensions": {"exception": {"code": "InvalidTokenError", "stacktrace": ["Traceback (most recent call last):", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executor.py\", line 452, in resolve_or_error", "    return executor.execute(resolve_fn, source, info, **args)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executors/sync.py\", line 16, in execute", "    return fn(*args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/core/fields.py\", line 158, in new_resolver", "    return wrapped_resolver(obj, info, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/decorators.py\", line 32, in wrapper", "    return func(info.context, *args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/decorators.py\", line 46, in wrapper", "    test_func(context)", "  File \"/app/saleor/graphql/decorators.py\", line 86, in check_perms", "    if not one_of_permissions_or_auth_filter_required(context, perms):", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 42, in one_of_permissions_or_auth_filter_required", "    perm_results = _get_result_of_permissions_checks(context, permissions)", "                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 60, in _get_result_of_permissions_checks", "    if requestor and permissions:", "       ^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 251, in inner", "    self._setup()", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 404, in _setup", "    self._wrapped = self._setupfunc()", "                    ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 94, in user", "    return get_user(request) or None", "           ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 84, in get_user", "    request._cached_user = cast(User | None, authenticate(request=request))", "                                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/views/decorators/debug.py\", line 75, in sensitive_variables_wrapper", "    return func(*func_args, **func_kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/contrib/auth/__init__.py\", line 114, in authenticate", "    user = backend.authenticate(request, **credentials)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 51, in authenticate", "    return load_user_from_request(request)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 151, in load_user_from_request", "    raise jwt.InvalidTokenError(", "jwt.exceptions.InvalidTokenError: Invalid token. Create new one by using tokenCreate mutation."]}}}], "data": {"exportFiles": null}, "extensions": {"cost": {"requestedQueryCost": 1, "maximumAvailable": 50000}}}
```
- Error: Invalid token. Create new one by using tokenCreate mutation.

### productVariant (QUERY)
- Status: fail, Match: mismatch, Outcome: auth_error
- Diff: Expected family not_found (not_found), got rejection (auth_error)
- **Request:**
```graphql
query { productVariant(id: "00000000-0000-0000-0000-000000000000") { id } }
```
- **Expected (golden):**
```json
{
  "errors": [
    {
      "message": "Invalid ID: 00000000-0000-0000-0000-000000000000. Expected: ProductVariant.",
      "locations": [
        {
          "line": 1,
          "column": 9
        }
      ],
      "path": [
        "productVariant"
      ],
      "extensions": {
        "exception": {
          "code": "GraphQLError",
          "stacktrace": [
            "Traceback (most recent call last):",
            "  File \"/app/saleor/graphql/core/utils/__init__.py\", line 80, in from_global_id_or_error",
            "    type_, id_ = graphene.Node.from_global_id(global_id)",
            "                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/usr/local/lib/python3.12/site-packages/graphene/relay/node.py\", line 115, in from_global_id",
            "    return from_global_id(global_id)",
            "           ^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/usr/local/lib/python3.12/site-packages/graphql_relay/node/node.py\", line 66, in from_global_id",
            "    unbased_global_id = unbase64(global_id)",
            "                        ^^^^^^^^^^^^^^^^^^^",
            "  File \"/usr/local/lib/python3.12/site-packages/graphql_relay/utils.py\", line 11, in unbase64",
            "    return _unbase64(s).decode('utf-8')",
            "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "UnicodeDecodeError: 'utf-8' codec can't decode byte 0xd3 in position 0: invalid continuation byte",
            "",
            "The above exception was the direct cause of the following exception:",
            "Traceback (most recent call last):",
            "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executor.py\", line 452, in resolve_or_error",
            "    return executor.execute(resolve_fn, source, info, **args)",
            "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executors/sync.py\", line 16, in execute",
            "    return fn(*args, **kwargs)",
            "           ^^^^^^^^^^^^^^^^^^^",
            "  File \"/app/saleor/graphql/core/tracing.py\", line 19, in wrapper",
            "    return func(*args, **kwargs)",
            "           ^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/app/saleor/graphql/product/schema.py\", line 576, in resolve_product_variant",
            "    return _resolve_product_variant(None)",
            "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/app/saleor/graphql/product/schema.py\", line 556, in _resolve_product_variant",
            "    variant = resolve_variant(",
            "              ^^^^^^^^^^^^^^^^",
            "  File \"/app/saleor/graphql/core/tracing.py\", line 19, in wrapper",
            "    return func(*args, **kwargs)",
            "           ^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/app/saleor/graphql/product/resolvers.py\", line 180, in resolve_variant",
            "    _, id = from_global_id_or_error(id, \"ProductVariant\")",
            "            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/app/saleor/graphql/core/utils/__init__.py\", line 87, in from_global_id_or_error",
            "    raise GraphQLError(",
            "graphql.error.base.GraphQLError: Invalid ID: 00000000-0000-0000-0000-000000000000. Expected: ProductVariant."
          ]
        }
      }
    }
  ],
  "data": {
    "productVariant": null
  },
  "extensions": {
    "cost": {
      "requestedQueryCost": 1,
      "maximumAvailable": 50000
    }
  }
}
```
- **Actual:**
```json
{"errors": [{"message": "Invalid token. Create new one by using tokenCreate mutation.", "locations": [{"line": 1, "column": 9}], "path": ["productVariant"], "extensions": {"exception": {"code": "InvalidTokenError", "stacktrace": ["Traceback (most recent call last):", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executor.py\", line 452, in resolve_or_error", "    return executor.execute(resolve_fn, source, info, **args)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executors/sync.py\", line 16, in execute", "    return fn(*args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/core/tracing.py\", line 19, in wrapper", "    return func(*args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/product/schema.py\", line 545, in resolve_product_variant", "    has_required_permissions = has_one_of_permissions(", "                               ^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 102, in has_one_of_permissions", "    if not requestor:", "           ^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 251, in inner", "    self._setup()", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 404, in _setup", "    self._wrapped = self._setupfunc()", "                    ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 94, in user", "    return get_user(request) or None", "           ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 84, in get_user", "    request._cached_user = cast(User | None, authenticate(request=request))", "                                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/views/decorators/debug.py\", line 75, in sensitive_variables_wrapper", "    return func(*func_args, **func_kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/contrib/auth/__init__.py\", line 114, in authenticate", "    user = backend.authenticate(request, **credentials)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 51, in authenticate", "    return load_user_from_request(request)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 151, in load_user_from_request", "    raise jwt.InvalidTokenError(", "jwt.exceptions.InvalidTokenError: Invalid token. Create new one by using tokenCreate mutation."]}}}], "data": {"productVariant": null}, "extensions": {"cost": {"requestedQueryCost": 1, "maximumAvailable": 50000}}}
```
- Error: Invalid token. Create new one by using tokenCreate mutation.

### productVariants (QUERY)
- Status: fail, Match: mismatch, Outcome: auth_error
- Diff: Expected family success (success), got rejection (auth_error)
- **Request:**
```graphql
query { productVariants(first: 1) { edges { node { id } } } }
```
- **Expected (golden):**
```json
{
  "data": {
    "productVariants": {
      "edges": []
    }
  },
  "extensions": {
    "cost": {
      "requestedQueryCost": 1,
      "maximumAvailable": 50000
    }
  }
}
```
- **Actual:**
```json
{"errors": [{"message": "Invalid token. Create new one by using tokenCreate mutation.", "locations": [{"line": 1, "column": 9}], "path": ["productVariants"], "extensions": {"exception": {"code": "InvalidTokenError", "stacktrace": ["Traceback (most recent call last):", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executor.py\", line 452, in resolve_or_error", "    return executor.execute(resolve_fn, source, info, **args)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executors/sync.py\", line 16, in execute", "    return fn(*args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/core/fields.py\", line 158, in new_resolver", "    return wrapped_resolver(obj, info, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/product/schema.py\", line 583, in resolve_product_variants", "    has_required_permissions = has_one_of_permissions(", "                               ^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 102, in has_one_of_permissions", "    if not requestor:", "           ^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 251, in inner", "    self._setup()", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 404, in _setup", "    self._wrapped = self._setupfunc()", "                    ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 94, in user", "    return get_user(request) or None", "           ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 84, in get_user", "    request._cached_user = cast(User | None, authenticate(request=request))", "                                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/views/decorators/debug.py\", line 75, in sensitive_variables_wrapper", "    return func(*func_args, **func_kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/contrib/auth/__init__.py\", line 114, in authenticate", "    user = backend.authenticate(request, **credentials)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 51, in authenticate", "    return load_user_from_request(request)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 151, in load_user_from_request", "    raise jwt.InvalidTokenError(", "jwt.exceptions.InvalidTokenError: Invalid token. Create new one by using tokenCreate mutation."]}}}], "data": {"productVariants": null}, "extensions": {"cost": {"requestedQueryCost": 1, "maximumAvailable": 50000}}}
```
- Error: Invalid token. Create new one by using tokenCreate mutation.

### product (QUERY)
- Status: fail, Match: mismatch, Outcome: auth_error
- Diff: Expected family not_found (not_found), got rejection (auth_error)
- **Request:**
```graphql
query { product(id: "00000000-0000-0000-0000-000000000000") { id } }
```
- **Expected (golden):**
```json
{
  "errors": [
    {
      "message": "Invalid ID: 00000000-0000-0000-0000-000000000000. Expected: Product.",
      "locations": [
        {
          "line": 1,
          "column": 9
        }
      ],
      "path": [
        "product"
      ],
      "extensions": {
        "exception": {
          "code": "GraphQLError",
          "stacktrace": [
            "Traceback (most recent call last):",
            "  File \"/app/saleor/graphql/core/utils/__init__.py\", line 80, in from_global_id_or_error",
            "    type_, id_ = graphene.Node.from_global_id(global_id)",
            "                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/usr/local/lib/python3.12/site-packages/graphene/relay/node.py\", line 115, in from_global_id",
            "    return from_global_id(global_id)",
            "           ^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/usr/local/lib/python3.12/site-packages/graphql_relay/node/node.py\", line 66, in from_global_id",
            "    unbased_global_id = unbase64(global_id)",
            "                        ^^^^^^^^^^^^^^^^^^^",
            "  File \"/usr/local/lib/python3.12/site-packages/graphql_relay/utils.py\", line 11, in unbase64",
            "    return _unbase64(s).decode('utf-8')",
            "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "UnicodeDecodeError: 'utf-8' codec can't decode byte 0xd3 in position 0: invalid continuation byte",
            "",
            "The above exception was the direct cause of the following exception:",
            "Traceback (most recent call last):",
            "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executor.py\", line 452, in resolve_or_error",
            "    return executor.execute(resolve_fn, source, info, **args)",
            "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executors/sync.py\", line 16, in execute",
            "    return fn(*args, **kwargs)",
            "           ^^^^^^^^^^^^^^^^^^^",
            "  File \"/app/saleor/graphql/core/tracing.py\", line 19, in wrapper",
            "    return func(*args, **kwargs)",
            "           ^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/app/saleor/graphql/product/schema.py\", line 477, in resolve_product",
            "    return _resolve_product(None)",
            "           ^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/app/saleor/graphql/product/schema.py\", line 456, in _resolve_product",
            "    product = resolve_product(",
            "              ^^^^^^^^^^^^^^^^",
            "  File \"/app/saleor/graphql/product/resolvers.py\", line 103, in resolve_product",
            "    _type, id = from_global_id_or_error(id, \"Product\")",
            "                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "  File \"/app/saleor/graphql/core/utils/__init__.py\", line 87, in from_global_id_or_error",
            "    raise GraphQLError(",
            "graphql.error.base.GraphQLError: Invalid ID: 00000000-0000-0000-0000-000000000000. Expected: Product."
          ]
        }
      }
    }
  ],
  "data": {
    "product": null
  },
  "extensions": {
    "cost": {
      "requestedQueryCost": 1,
      "maximumAvailable": 50000
    }
  }
}
```
- **Actual:**
```json
{"errors": [{"message": "Invalid token. Create new one by using tokenCreate mutation.", "locations": [{"line": 1, "column": 9}], "path": ["product"], "extensions": {"exception": {"code": "InvalidTokenError", "stacktrace": ["Traceback (most recent call last):", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executor.py\", line 452, in resolve_or_error", "    return executor.execute(resolve_fn, source, info, **args)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executors/sync.py\", line 16, in execute", "    return fn(*args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/core/tracing.py\", line 19, in wrapper", "    return func(*args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/product/schema.py\", line 445, in resolve_product", "    has_required_permissions = has_one_of_permissions(", "                               ^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 102, in has_one_of_permissions", "    if not requestor:", "           ^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 251, in inner", "    self._setup()", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 404, in _setup", "    self._wrapped = self._setupfunc()", "                    ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 94, in user", "    return get_user(request) or None", "           ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 84, in get_user", "    request._cached_user = cast(User | None, authenticate(request=request))", "                                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/views/decorators/debug.py\", line 75, in sensitive_variables_wrapper", "    return func(*func_args, **func_kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/contrib/auth/__init__.py\", line 114, in authenticate", "    user = backend.authenticate(request, **credentials)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 51, in authenticate", "    return load_user_from_request(request)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 151, in load_user_from_request", "    raise jwt.InvalidTokenError(", "jwt.exceptions.InvalidTokenError: Invalid token. Create new one by using tokenCreate mutation."]}}}], "data": {"product": null}, "extensions": {"cost": {"requestedQueryCost": 1, "maximumAvailable": 50000}}}
```
- Error: Invalid token. Create new one by using tokenCreate mutation.

### products (QUERY)
- Status: fail, Match: mismatch, Outcome: auth_error
- Diff: Expected family success (success), got rejection (auth_error)
- **Request:**
```graphql
query { products(first: 1) { edges { node { id } } } }
```
- **Expected (golden):**
```json
{
  "data": {
    "products": {
      "edges": []
    }
  },
  "extensions": {
    "cost": {
      "requestedQueryCost": 1,
      "maximumAvailable": 50000
    }
  }
}
```
- **Actual:**
```json
{"errors": [{"message": "Invalid token. Create new one by using tokenCreate mutation.", "locations": [{"line": 1, "column": 9}], "path": ["products"], "extensions": {"exception": {"code": "InvalidTokenError", "stacktrace": ["Traceback (most recent call last):", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executor.py\", line 452, in resolve_or_error", "    return executor.execute(resolve_fn, source, info, **args)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executors/sync.py\", line 16, in execute", "    return fn(*args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/core/fields.py\", line 158, in new_resolver", "    return wrapped_resolver(obj, info, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/core/tracing.py\", line 19, in wrapper", "    return func(*args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/product/schema.py\", line 488, in resolve_products", "    has_required_permissions = has_one_of_permissions(", "                               ^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 102, in has_one_of_permissions", "    if not requestor:", "           ^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 251, in inner", "    self._setup()", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 404, in _setup", "    self._wrapped = self._setupfunc()", "                    ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 94, in user", "    return get_user(request) or None", "           ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 84, in get_user", "    request._cached_user = cast(User | None, authenticate(request=request))", "                                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/views/decorators/debug.py\", line 75, in sensitive_variables_wrapper", "    return func(*func_args, **func_kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/contrib/auth/__init__.py\", line 114, in authenticate", "    user = backend.authenticate(request, **credentials)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 51, in authenticate", "    return load_user_from_request(request)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 151, in load_user_from_request", "    raise jwt.InvalidTokenError(", "jwt.exceptions.InvalidTokenError: Invalid token. Create new one by using tokenCreate mutation."]}}}], "data": {"products": null}, "extensions": {"cost": {"requestedQueryCost": 1, "maximumAvailable": 50000}}}
```
- Error: Invalid token. Create new one by using tokenCreate mutation.

### checkoutLines (QUERY)
- Status: fail, Match: mismatch, Outcome: auth_error
- Diff: Expected family success (success), got rejection (auth_error)
- **Request:**
```graphql
query { checkoutLines(first: 1) { edges { node { id } } } }
```
- **Expected (golden):**
```json
{
  "data": {
    "checkoutLines": {
      "edges": []
    }
  },
  "extensions": {
    "cost": {
      "requestedQueryCost": 1,
      "maximumAvailable": 50000
    }
  }
}
```
- **Actual:**
```json
{"errors": [{"message": "Invalid token. Create new one by using tokenCreate mutation.", "locations": [{"line": 1, "column": 9}], "path": ["checkoutLines"], "extensions": {"exception": {"code": "InvalidTokenError", "stacktrace": ["Traceback (most recent call last):", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executor.py\", line 452, in resolve_or_error", "    return executor.execute(resolve_fn, source, info, **args)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/graphql/execution/executors/sync.py\", line 16, in execute", "    return fn(*args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/decorators.py\", line 32, in wrapper", "    return func(info.context, *args, **kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/decorators.py\", line 46, in wrapper", "    test_func(context)", "  File \"/app/saleor/graphql/decorators.py\", line 86, in check_perms", "    if not one_of_permissions_or_auth_filter_required(context, perms):", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 42, in one_of_permissions_or_auth_filter_required", "    perm_results = _get_result_of_permissions_checks(context, permissions)", "                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/permission/utils.py\", line 60, in _get_result_of_permissions_checks", "    if requestor and permissions:", "       ^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 251, in inner", "    self._setup()", "  File \"/usr/local/lib/python3.12/site-packages/django/utils/functional.py\", line 404, in _setup", "    self._wrapped = self._setupfunc()", "                    ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 94, in user", "    return get_user(request) or None", "           ^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/graphql/context.py\", line 84, in get_user", "    request._cached_user = cast(User | None, authenticate(request=request))", "                                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/views/decorators/debug.py\", line 75, in sensitive_variables_wrapper", "    return func(*func_args, **func_kwargs)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/usr/local/lib/python3.12/site-packages/django/contrib/auth/__init__.py\", line 114, in authenticate", "    user = backend.authenticate(request, **credentials)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 51, in authenticate", "    return load_user_from_request(request)", "           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", "  File \"/app/saleor/core/auth_backend.py\", line 151, in load_user_from_request", "    raise jwt.InvalidTokenError(", "jwt.exceptions.InvalidTokenError: Invalid token. Create new one by using tokenCreate mutation."]}}}], "data": {"checkoutLines": null}, "extensions": {"cost": {"requestedQueryCost": 1, "maximumAvailable": 50000}}}
```
- Error: Invalid token. Create new one by using tokenCreate mutation.

## All results index (compact)
| Endpoint | Kind | Status | Match | Outcome | ms |
|----------|------|--------|-------|---------|-----|
| orderLineDiscountRemove | MUTATION | pass | match | business_error | 29 |
| promotionUpdate | MUTATION | pass | match | graphql_error | 6 |
| taxClassDelete | MUTATION | pass | match | business_error | 27 |
| orderLineDiscountUpdate | MUTATION | pass | match | graphql_error | 6 |
| promotion | QUERY | pass | match | not_found | 28 |
| taxClassUpdate | MUTATION | pass | match | graphql_error | 7 |
| orderLineUpdate | MUTATION | pass | match | graphql_error | 5 |
| promotions | QUERY | pass | match | success | 28 |
| taxClass | QUERY | pass | match | not_found | 26 |
| orderLinesCreate | MUTATION | pass | match | graphql_error | 6 |
| refundReasonReferenceClear | MUTATION | pass | match | success | 27 |
| taxClasses | QUERY | pass | match | success | 27 |
| orderMarkAsPaid | MUTATION | pass | match | business_error | 25 |
| refundSettingsUpdate | MUTATION | pass | match | graphql_error | 5 |
| taxConfigurationUpdate | MUTATION | pass | match | graphql_error | 4 |
| orderNoteAdd | MUTATION | pass | match | graphql_error | 5 |
| refundSettings | QUERY | pass | match | success | 20 |
| taxConfiguration | QUERY | pass | match | not_found | 26 |
| orderNoteUpdate | MUTATION | pass | match | graphql_error | 6 |
| requestEmailChange | MUTATION | pass | match | business_error | 437 |
| taxConfigurations | QUERY | pass | match | success | 28 |
| orderRefund | MUTATION | pass | match | graphql_error | 7 |
| requestPasswordReset | MUTATION | pass | match | business_error | 27 |
| taxCountryConfigurationDelete | MUTATION | pass | match | graphql_error | 7 |
| orderUpdateShipping | MUTATION | pass | match | graphql_error | 6 |
| resetPassword | MUTATION | pass | match | graphql_error | 39 |
| taxCountryConfigurationUpdate | MUTATION | pass | match | graphql_error | 5 |
| orderUpdate | MUTATION | pass | match | business_error | 24 |
| saleBulkDelete | MUTATION | pass | match | not_found | 27 |
| taxCountryConfiguration | QUERY | pass | match | graphql_error | 6 |
| orderVoid | MUTATION | pass | match | business_error | 26 |
| saleCreate | MUTATION | pass | match | success | 70 |
| taxCountryConfigurations | QUERY | pass | match | success | 27 |
| order | QUERY | pass | match | not_found | 7 |
| saleDelete | MUTATION | pass | match | graphql_error | 5 |
| taxExemptionManage | MUTATION | pass | match | business_error | 24 |
| ordersByUser | QUERY | pass | match | graphql_error | 11 |
| saleUpdate | MUTATION | pass | match | graphql_error | 5 |
| tokenCreate | MUTATION | pass | match | business_error | 441 |
| ordersDraft | QUERY | pass | match | graphql_error | 9 |
| sale | QUERY | pass | match | success | 29 |
| tokenRefresh | MUTATION | pass | match | business_error | 26 |
| orders | QUERY | pass | match | success | 33 |
| sales | QUERY | pass | match | success | 31 |
| tokenVerify | MUTATION | pass | match | business_error | 49 |
| pageAttributeAssign | MUTATION | pass | match | business_error | 25 |
| sendConfirmationEmail | MUTATION | pass | match | business_error | 24 |
| tokensDeactivateAll | MUTATION | pass | match | success | 28 |
| pageAttributeUnassign | MUTATION | pass | match | auth_error | 412 |
| setPassword | MUTATION | pass | match | business_error | 44 |
| transactionCreate | MUTATION | pass | match | graphql_error | 8 |
| pageBulkDelete | MUTATION | pass | match | auth_error | 448 |
| shippingMethodChannelListingUpdate | MUTATION | pass | match | graphql_error | 12 |
| transactionEventReport | MUTATION | pass | match | graphql_error | 14 |
| pageBulkPublish | MUTATION | pass | match | auth_error | 425 |
| shippingMethodCreate | MUTATION | pass | match | graphql_error | 91 |
| transactionInitialize | MUTATION | pass | match | graphql_error | 5 |
| pageCreate | MUTATION | pass | match | graphql_error | 7 |
| shippingMethodDelete | MUTATION | pass | match | graphql_error | 57 |
| transactionProcess | MUTATION | pass | match | auth_error | 395 |
| pageDelete | MUTATION | pass | match | auth_error | 411 |
| shippingMethodUpdate | MUTATION | pass | match | graphql_error | 69 |
| transactionRequestAction | MUTATION | pass | match | graphql_error | 7 |
| pageReorderAttributeValues | MUTATION | pass | match | graphql_error | 7 |
| shippingMethods | QUERY | pass | match | graphql_error | 8 |
| transactionRequestRefundForGrantedRefund | MUTATION | pass | match | auth_error | 421 |
| pageTranslate | MUTATION | pass | match | graphql_error | 13 |
| shippingPriceBulkDelete | MUTATION | pass | match | auth_error | 460 |
| transactionUpdate | MUTATION | pass | match | auth_error | 455 |
| pageTypeBulkDelete | MUTATION | pass | match | auth_error | 488 |
| shippingPriceCreate | MUTATION | pass | match | auth_error | 438 |
| transaction | QUERY | fail | mismatch | auth_error | 448 |
| pageTypeCreate | MUTATION | pass | match | auth_error | 477 |
| shippingPriceDelete | MUTATION | pass | match | auth_error | 479 |
| transactions | QUERY | fail | mismatch | auth_error | 464 |
| pageTypeDelete | MUTATION | pass | match | auth_error | 466 |
| shippingPriceExcludeProducts | MUTATION | pass | match | graphql_error | 11 |
| translation | QUERY | pass | match | graphql_error | 6 |
| pageTypeReorderAttributes | MUTATION | pass | match | graphql_error | 7 |
| shippingPriceRemoveProductFromExclude | MUTATION | pass | match | auth_error | 411 |
| translations | QUERY | pass | match | graphql_error | 9 |
| app | QUERY | fail | mismatch | auth_error | 410 |
| pageTypeUpdate | MUTATION | pass | match | auth_error | 474 |
| shippingPriceTranslate | MUTATION | pass | match | graphql_error | 11 |
| unassignWarehouseShippingZone | MUTATION | pass | match | auth_error | 377 |
| pageType | QUERY | pass | match | not_found | 8 |
| shippingPriceUpdate | MUTATION | pass | match | graphql_error | 9 |
| updateMetadata | MUTATION | pass | match | graphql_error | 5 |
| appUpdate | MUTATION | pass | match | graphql_error | 9 |
| pageTypes | QUERY | pass | match | success | 22 |
| shippingZoneBulkDelete | MUTATION | pass | match | auth_error | 457 |
| updatePrivateMetadata | MUTATION | pass | match | graphql_error | 15 |
| appTokenVerify | MUTATION | fail | mismatch | auth_error | 479 |
| pageUpdate | MUTATION | pass | match | graphql_error | 18 |
| shippingZoneCreate | MUTATION | pass | match | auth_error | 464 |
| updateWarehouse | MUTATION | pass | match | auth_error | 470 |
| page | QUERY | pass | match | not_found | 14 |
| shippingZoneDelete | MUTATION | pass | match | auth_error | 451 |
| userAvatarDelete | MUTATION | pass | match | auth_error | 468 |
| appTokenDelete | MUTATION | pass | match | auth_error | 432 |
| pages | QUERY | fail | mismatch | auth_error | 462 |
| shippingZoneUpdate | MUTATION | pass | match | graphql_error | 25 |
| userAvatarUpdate | MUTATION | pass | match | auth_error | 462 |
| appTokenCreate | MUTATION | pass | match | graphql_error | 13 |
| passwordChange | MUTATION | pass | match | auth_error | 456 |
| shippingZone | QUERY | fail | mismatch | auth_error | 431 |
| userBulkSetActive | MUTATION | pass | match | auth_error | 442 |
| appRetryInstall | MUTATION | pass | match | auth_error | 437 |
| paymentCapture | MUTATION | pass | match | auth_error | 448 |
| shippingZones | QUERY | fail | mismatch | auth_error | 455 |
| user | QUERY | fail | mismatch | auth_error | 417 |
| appDelete | MUTATION | pass | match | auth_error | 464 |
| paymentCheckBalance | MUTATION | pass | match | graphql_error | 15 |
| shopAddressUpdate | MUTATION | pass | match | auth_error | 468 |
| users | QUERY | pass | match | graphql_error | 16 |
| appReenableSyncWebhooks | MUTATION | pass | match | auth_error | 479 |
| paymentGatewayInitializeTokenization | MUTATION | pass | match | auth_error | 425 |
| shopDomainUpdate | MUTATION | fail | mismatch | auth_error | 462 |
| variantMediaAssign | MUTATION | pass | match | auth_error | 456 |
| paymentGatewayInitialize | MUTATION | fail | mismatch | auth_error | 463 |
| shopSettingsTranslate | MUTATION | pass | match | graphql_error | 10 |
| variantMediaUnassign | MUTATION | pass | match | auth_error | 372 |
| appExtension | QUERY | fail | mismatch | auth_error | 435 |
| paymentGateways | QUERY | pass | match | graphql_error | 25 |
| shopSettingsUpdate | MUTATION | fail | mismatch | auth_error | 452 |
| voucherBulkDelete | MUTATION | pass | match | auth_error | 477 |
| paymentInitialize | MUTATION | pass | match | auth_error | 420 |
| shop | QUERY | pass | match | success | 12 |
| voucherCataloguesAdd | MUTATION | pass | match | graphql_error | 8 |
| appExtensions | QUERY | fail | mismatch | auth_error | 421 |
| paymentMethodInitializeTokenization | MUTATION | pass | match | graphql_error | 15 |
| staffBulkDelete | MUTATION | pass | match | auth_error | 449 |
| voucherCataloguesRemove | MUTATION | pass | match | graphql_error | 20 |
| paymentMethodProcessTokenization | MUTATION | pass | match | auth_error | 414 |
| staffCreate | MUTATION | pass | match | auth_error | 469 |
| voucherChannelListingUpdate | MUTATION | pass | match | graphql_error | 14 |
| appProblemDismiss | MUTATION | pass | match | auth_error | 452 |
| paymentRefund | MUTATION | pass | match | auth_error | 492 |
| staffDelete | MUTATION | pass | match | auth_error | 447 |
| voucherCodeBulkDelete | MUTATION | pass | match | graphql_error | 21 |
| appFetchManifest | MUTATION | pass | match | auth_error | 446 |
| paymentVoid | MUTATION | pass | match | auth_error | 424 |
| staffNotificationRecipientCreate | MUTATION | pass | match | auth_error | 438 |
| voucherCreate | MUTATION | pass | match | auth_error | 463 |
| appProblemCreate | MUTATION | pass | match | graphql_error | 13 |
| payment | QUERY | fail | mismatch | auth_error | 377 |
| staffNotificationRecipientDelete | MUTATION | pass | match | auth_error | 423 |
| voucherDelete | MUTATION | pass | match | auth_error | 491 |
| appInstall | MUTATION | pass | match | graphql_error | 24 |
| payments | QUERY | fail | mismatch | auth_error | 426 |
| staffNotificationRecipientUpdate | MUTATION | pass | match | graphql_error | 13 |
| voucherTranslate | MUTATION | pass | match | graphql_error | 15 |
| permissionGroupCreate | MUTATION | pass | match | graphql_error | 7 |
| staffUpdate | MUTATION | pass | match | graphql_error | 9 |
| voucherUpdate | MUTATION | pass | match | graphql_error | 5 |
| permissionGroupDelete | MUTATION | pass | match | auth_error | 452 |
| staffUsers | QUERY | fail | mismatch | auth_error | 476 |
| voucher | QUERY | fail | mismatch | auth_error | 444 |
| permissionGroupUpdate | MUTATION | pass | match | graphql_error | 13 |
| stockBulkUpdate | MUTATION | pass | match | graphql_error | 11 |
| vouchers | QUERY | fail | mismatch | auth_error | 433 |
| permissionGroup | QUERY | fail | mismatch | auth_error | 436 |
| stock | QUERY | fail | mismatch | auth_error | 467 |
| warehouseCreate | MUTATION | pass | match | graphql_error | 65 |
| permissionGroups | QUERY | fail | mismatch | auth_error | 396 |
| stocks | QUERY | fail | mismatch | auth_error | 405 |
| warehouseDelete | MUTATION | pass | match | graphql_error | 51 |
| pluginUpdate | MUTATION | pass | match | graphql_error | 6 |
| storedPaymentMethodRequestDelete | MUTATION | pass | match | auth_error | 368 |
| warehouseUpdate | MUTATION | pass | match | graphql_error | 45 |
| plugin | QUERY | fail | mismatch | auth_error | 376 |
| taxClassCreate | MUTATION | pass | match | graphql_error | 7 |
| warehouse | QUERY | fail | mismatch | auth_error | 392 |
| appsInstallations | QUERY | fail | mismatch | auth_error | 377 |
| checkoutRemovePromoCode | MUTATION | pass | match | auth_error | 402 |
| giftCardDeactivate | MUTATION | pass | match | auth_error | 376 |
| plugins | QUERY | fail | mismatch | auth_error | 388 |
| warehouses | QUERY | fail | mismatch | auth_error | 378 |
| apps | QUERY | fail | mismatch | auth_error | 439 |
| checkoutShippingAddressUpdate | MUTATION | pass | match | graphql_error | 11 |
| giftCardDelete | MUTATION | pass | match | auth_error | 440 |
| productAttributeAssign | MUTATION | pass | match | graphql_error | 14 |
| webhookCreate | MUTATION | pass | match | auth_error | 503 |
| assignNavigation | MUTATION | pass | match | graphql_error | 8 |
| checkoutShippingMethodUpdate | MUTATION | pass | match | graphql_error | 13 |
| giftCardResend | MUTATION | pass | match | graphql_error | 6 |
| productAttributeAssignmentUpdate | MUTATION | pass | match | graphql_error | 11 |
| webhookDelete | MUTATION | pass | match | auth_error | 391 |
| productAttributeUnassign | MUTATION | pass | match | auth_error | 421 |
| assignWarehouseShippingZone | MUTATION | pass | match | auth_error | 417 |
| checkoutUpdate | MUTATION | pass | match | graphql_error | 40 |
| giftCardSettingsUpdate | MUTATION | fail | mismatch | auth_error | 420 |
| webhookDryRun | MUTATION | pass | match | auth_error | 433 |
| attributeBulkCreate | MUTATION | pass | match | graphql_error | 5 |
| checkout | QUERY | pass | match | not_found | 16 |
| giftCardSettings | QUERY | fail | mismatch | auth_error | 398 |
| productBulkCreate | MUTATION | pass | match | graphql_error | 7 |
| webhookEvents | QUERY | pass | match | graphql_error | 12 |
| attributeBulkDelete | MUTATION | pass | match | auth_error | 414 |
| checkouts | QUERY | fail | mismatch | auth_error | 443 |
| giftCardTags | QUERY | fail | mismatch | auth_error | 409 |
| productBulkDelete | MUTATION | pass | match | auth_error | 459 |
| webhookSamplePayload | QUERY | pass | match | graphql_error | 13 |
| attributeBulkTranslate | MUTATION | pass | match | graphql_error | 16 |
| collectionAddProducts | MUTATION | pass | match | auth_error | 392 |
| giftCardUpdate | MUTATION | pass | match | graphql_error | 14 |
| productBulkTranslate | MUTATION | pass | match | graphql_error | 7 |
| webhookTrigger | MUTATION | pass | match | auth_error | 424 |
| attributeBulkUpdate | MUTATION | pass | match | graphql_error | 10 |
| collectionBulkDelete | MUTATION | pass | match | auth_error | 412 |
| giftCard | QUERY | fail | mismatch | auth_error | 460 |
| productChannelListingUpdate | MUTATION | pass | match | graphql_error | 7 |
| webhookUpdate | MUTATION | pass | match | graphql_error | 11 |
| attributeCreate | MUTATION | pass | match | graphql_error | 8 |
| collectionChannelListingUpdate | MUTATION | pass | match | graphql_error | 12 |
| giftCards | QUERY | fail | mismatch | auth_error | 434 |
| productCreate | MUTATION | pass | match | graphql_error | 9 |
| webhook | QUERY | pass | match | not_found | 16 |
| productDelete | MUTATION | pass | match | auth_error | 465 |
| attributeDelete | MUTATION | pass | match | auth_error | 385 |
| collectionCreate | MUTATION | pass | match | auth_error | 422 |
| invoiceCreate | MUTATION | pass | match | graphql_error | 5 |
| attributeReorderValues | MUTATION | pass | match | graphql_error | 4 |
| collectionDelete | MUTATION | pass | match | auth_error | 458 |
| invoiceDelete | MUTATION | pass | match | auth_error | 417 |
| productMediaBulkDelete | MUTATION | pass | match | auth_error | 451 |
| appDeleteFailedInstallation | MUTATION | pass | match | auth_error | 375 |
| attributeTranslate | MUTATION | pass | match | graphql_error | 10 |
| collectionRemoveProducts | MUTATION | pass | match | auth_error | 495 |
| invoiceRequestDelete | MUTATION | pass | match | auth_error | 426 |
| productMediaCreate | MUTATION | pass | match | graphql_error | 13 |
| attributeUpdate | MUTATION | pass | match | auth_error | 390 |
| collectionReorderProducts | MUTATION | pass | match | graphql_error | 13 |
| invoiceRequest | MUTATION | pass | match | auth_error | 403 |
| productMediaDelete | MUTATION | pass | match | auth_error | 379 |
| attributeValueBulkDelete | MUTATION | pass | match | auth_error | 423 |
| collectionTranslate | MUTATION | pass | match | graphql_error | 8 |
| invoiceSendNotification | MUTATION | pass | match | auth_error | 391 |
| productMediaReorder | MUTATION | pass | match | auth_error | 376 |
| attributeValueBulkTranslate | MUTATION | pass | match | graphql_error | 6 |
| collectionUpdate | MUTATION | pass | match | graphql_error | 5 |
| invoiceUpdate | MUTATION | pass | match | graphql_error | 4 |
| productMediaUpdate | MUTATION | pass | match | graphql_error | 5 |
| attributeValueCreate | MUTATION | pass | match | graphql_error | 10 |
| collection | QUERY | fail | mismatch | auth_error | 378 |
| languages | QUERY | pass | match | graphql_error | 11 |
| productReorderAttributeValues | MUTATION | pass | match | graphql_error | 61 |
| attributeValueDelete | MUTATION | pass | match | auth_error | 412 |
| collections | QUERY | fail | mismatch | auth_error | 426 |
| me | QUERY | fail | mismatch | auth_error | 372 |
| productTranslate | MUTATION | pass | match | graphql_error | 9 |
| _entities | QUERY | pass | match | graphql_error | 14 |
| attributeValueTranslate | MUTATION | pass | match | graphql_error | 7 |
| confirmAccount | MUTATION | pass | match | auth_error | 381 |
| menuBulkDelete | MUTATION | pass | match | auth_error | 375 |
| productTypeBulkDelete | MUTATION | pass | match | auth_error | 374 |
| attributeValueUpdate | MUTATION | pass | match | auth_error | 364 |
| confirmEmailChange | MUTATION | pass | match | auth_error | 364 |
| menuCreate | MUTATION | pass | match | graphql_error | 11 |
| productTypeCreate | MUTATION | pass | match | auth_error | 364 |
| attribute | QUERY | pass | match | not_found | 15 |
| createWarehouse | MUTATION | pass | match | graphql_error | 8 |
| menuDelete | MUTATION | pass | match | auth_error | 365 |
| productTypeDelete | MUTATION | pass | match | auth_error | 367 |
| attributes | QUERY | fail | mismatch | auth_error | 363 |
| customerBulkDelete | MUTATION | pass | match | auth_error | 367 |
| menuItemBulkDelete | MUTATION | pass | match | auth_error | 363 |
| productTypeReorderAttributes | MUTATION | pass | match | graphql_error | 7 |
| _service | QUERY | pass | match | success | 4 |
| categories | QUERY | pass | match | success | 22 |
| customerBulkUpdate | MUTATION | pass | match | graphql_error | 5 |
| menuItemCreate | MUTATION | pass | match | graphql_error | 10 |
| productTypeUpdate | MUTATION | pass | match | graphql_error | 4 |
| accountAddressCreate | MUTATION | pass | match | auth_error | 365 |
| categoryBulkDelete | MUTATION | pass | match | auth_error | 360 |
| customerCreate | MUTATION | pass | match | auth_error | 363 |
| menuItemDelete | MUTATION | pass | match | auth_error | 362 |
| productType | QUERY | pass | match | not_found | 8 |
| accountAddressDelete | MUTATION | pass | match | auth_error | 408 |
| categoryCreate | MUTATION | pass | match | auth_error | 364 |
| customerDelete | MUTATION | pass | match | auth_error | 361 |
| menuItemMove | MUTATION | pass | match | graphql_error | 5 |
| productTypes | QUERY | pass | match | success | 26 |
| accountAddressUpdate | MUTATION | pass | match | graphql_error | 4 |
| categoryDelete | MUTATION | pass | match | auth_error | 366 |
| customerUpdate | MUTATION | pass | match | auth_error | 361 |
| menuItemTranslate | MUTATION | pass | match | graphql_error | 5 |
| productUpdate | MUTATION | pass | match | auth_error | 366 |
| accountDelete | MUTATION | pass | match | auth_error | 363 |
| categoryTranslate | MUTATION | pass | match | graphql_error | 6 |
| customers | QUERY | fail | mismatch | auth_error | 379 |
| menuItemUpdate | MUTATION | pass | match | graphql_error | 7 |
| productVariantBulkCreate | MUTATION | pass | match | graphql_error | 12 |
| accountRegister | MUTATION | pass | match | graphql_error | 4 |
| categoryUpdate | MUTATION | pass | match | graphql_error | 7 |
| deleteMetadata | MUTATION | pass | match | business_error | 69 |
| menuItem | QUERY | pass | match | not_found | 5 |
| productVariantBulkDelete | MUTATION | pass | match | auth_error | 365 |
| accountRequestDeletion | MUTATION | pass | match | auth_error | 362 |
| category | QUERY | pass | match | not_found | 6 |
| deletePrivateMetadata | MUTATION | pass | match | business_error | 27 |
| menuItems | QUERY | pass | match | success | 20 |
| productVariantBulkTranslate | MUTATION | pass | match | graphql_error | 5 |
| accountSetDefaultAddress | MUTATION | pass | match | graphql_error | 9 |
| channelActivate | MUTATION | pass | match | auth_error | 361 |
| deleteWarehouse | MUTATION | pass | match | auth_error | 367 |
| menuUpdate | MUTATION | pass | match | graphql_error | 6 |
| productVariantBulkUpdate | MUTATION | pass | match | graphql_error | 11 |
| accountUpdate | MUTATION | fail | mismatch | auth_error | 405 |
| channelCreate | MUTATION | pass | match | graphql_error | 6 |
| deliveryOptionsCalculate | MUTATION | pass | match | auth_error | 369 |
| menu | QUERY | pass | match | not_found | 11 |
| productVariantChannelListingUpdate | MUTATION | pass | match | graphql_error | 4 |
| addressCreate | MUTATION | pass | match | graphql_error | 4 |
| channelDeactivate | MUTATION | pass | match | auth_error | 367 |
| draftOrderBulkDelete | MUTATION | pass | match | auth_error | 370 |
| menus | QUERY | pass | match | success | 23 |
| productVariantCreate | MUTATION | pass | match | graphql_error | 6 |
| addressDelete | MUTATION | pass | match | auth_error | 376 |
| channelDelete | MUTATION | pass | match | graphql_error | 6 |
| draftOrderComplete | MUTATION | pass | match | auth_error | 369 |
| meta | QUERY | pass | match | graphql_error | 11 |
| productVariantDelete | MUTATION | pass | match | auth_error | 395 |
| addressSetDefault | MUTATION | pass | match | graphql_error | 5 |
| channelReorderWarehouses | MUTATION | pass | match | graphql_error | 9 |
| draftOrderCreate | MUTATION | pass | match | auth_error | 361 |
| orderBulkCancel | MUTATION | pass | match | auth_error | 361 |
| productVariantPreorderDeactivate | MUTATION | pass | match | auth_error | 368 |
| channelUpdate | MUTATION | pass | match | graphql_error | 6 |
| addressUpdate | MUTATION | pass | match | graphql_error | 18 |
| draftOrderDelete | MUTATION | pass | match | auth_error | 361 |
| orderBulkCreate | MUTATION | pass | match | graphql_error | 5 |
| productVariantReorderAttributeValues | MUTATION | pass | match | graphql_error | 10 |
| addressValidationRules | QUERY | pass | match | graphql_error | 4 |
| channel | QUERY | pass | match | not_found | 6 |
| draftOrderUpdate | MUTATION | pass | match | auth_error | 366 |
| orderCancel | MUTATION | pass | match | auth_error | 361 |
| productVariantReorder | MUTATION | pass | match | graphql_error | 6 |
| address | QUERY | pass | match | not_found | 11 |
| channels | QUERY | fail | mismatch | auth_error | 365 |
| draftOrders | QUERY | fail | mismatch | auth_error | 365 |
| orderCapture | MUTATION | pass | match | graphql_error | 7 |
| productVariantSetDefault | MUTATION | pass | match | auth_error | 368 |
| appActivate | MUTATION | pass | match | auth_error | 363 |
| checkoutAddPromoCode | MUTATION | pass | match | auth_error | 366 |
| eventDeliveryRetry | MUTATION | pass | match | auth_error | 361 |
| orderConfirm | MUTATION | pass | match | auth_error | 397 |
| productVariantStocksCreate | MUTATION | pass | match | graphql_error | 5 |
| appCreate | MUTATION | pass | match | auth_error | 373 |
| checkoutBillingAddressUpdate | MUTATION | pass | match | graphql_error | 8 |
| exportFile | QUERY | fail | mismatch | auth_error | 374 |
| orderCreateFromCheckout | MUTATION | pass | match | auth_error | 363 |
| productVariantStocksDelete | MUTATION | pass | match | auth_error | 361 |
| appDeactivate | MUTATION | pass | match | auth_error | 361 |
| checkoutComplete | MUTATION | pass | match | auth_error | 364 |
| exportFiles | QUERY | fail | mismatch | auth_error | 364 |
| orderCreate | MUTATION | pass | match | graphql_error | 29 |
| productVariantStocksUpdate | MUTATION | pass | match | graphql_error | 5 |
| checkoutCreateFromOrder | MUTATION | pass | match | auth_error | 409 |
| externalAuthenticationUrl | MUTATION | pass | match | graphql_error | 6 |
| orderDelete | MUTATION | pass | match | graphql_error | 35 |
| productVariantTranslate | MUTATION | pass | match | graphql_error | 6 |
| checkoutCreate | MUTATION | pass | match | graphql_error | 7 |
| externalLogout | MUTATION | pass | match | graphql_error | 5 |
| orderDiscountAdd | MUTATION | pass | match | graphql_error | 5 |
| productVariantUpdate | MUTATION | pass | match | auth_error | 364 |
| checkoutCustomerAttach | MUTATION | pass | match | auth_error | 373 |
| externalObtainAccessTokens | MUTATION | pass | match | graphql_error | 9 |
| orderDiscountDelete | MUTATION | pass | match | auth_error | 386 |
| productVariant | QUERY | fail | mismatch | auth_error | 369 |
| productVariants | QUERY | fail | mismatch | auth_error | 398 |
| checkoutCustomerDetach | MUTATION | pass | match | auth_error | 362 |
| externalRefresh | MUTATION | pass | match | graphql_error | 6 |
| orderDiscountUpdate | MUTATION | pass | match | graphql_error | 12 |
| checkoutCustomerNoteUpdate | MUTATION | pass | match | auth_error | 365 |
| externalVerify | MUTATION | pass | match | graphql_error | 5 |
| orderFulfill | MUTATION | pass | match | graphql_error | 11 |
| product | QUERY | fail | mismatch | auth_error | 362 |
| checkoutDelete | MUTATION | pass | match | auth_error | 360 |
| fileUpload | MUTATION | pass | match | auth_error | 366 |
| orderFulfillmentApprove | MUTATION | pass | match | auth_error | 369 |
| products | QUERY | fail | mismatch | auth_error | 431 |
| checkoutDeliveryMethodUpdate | MUTATION | pass | match | auth_error | 366 |
| giftCardActivate | MUTATION | pass | match | auth_error | 368 |
| orderFulfillmentCancel | MUTATION | pass | match | graphql_error | 5 |
| promotionBulkDelete | MUTATION | pass | match | auth_error | 383 |
| checkoutEmailUpdate | MUTATION | pass | match | auth_error | 372 |
| giftCardAddNote | MUTATION | pass | match | graphql_error | 5 |
| orderFulfillmentRefundProducts | MUTATION | pass | match | graphql_error | 16 |
| promotionCreate | MUTATION | pass | match | graphql_error | 5 |
| checkoutLanguageCodeUpdate | MUTATION | pass | match | graphql_error | 9 |
| giftCardBulkActivate | MUTATION | pass | match | auth_error | 376 |
| orderFulfillmentReturnProducts | MUTATION | pass | match | graphql_error | 7 |
| promotionDelete | MUTATION | pass | match | auth_error | 410 |
| checkoutLinesAdd | MUTATION | pass | match | graphql_error | 5 |
| giftCardBulkCreate | MUTATION | pass | match | graphql_error | 14 |
| orderFulfillmentUpdateTracking | MUTATION | pass | match | graphql_error | 4 |
| promotionRuleCreate | MUTATION | pass | match | graphql_error | 7 |
| checkoutLinesDelete | MUTATION | pass | match | auth_error | 376 |
| giftCardBulkDeactivate | MUTATION | pass | match | auth_error | 371 |
| orderGrantRefundCreate | MUTATION | pass | match | graphql_error | 8 |
| promotionRuleDelete | MUTATION | pass | match | auth_error | 396 |
| promotionRuleTranslate | MUTATION | pass | match | graphql_error | 7 |
| checkoutLinesUpdate | MUTATION | pass | match | graphql_error | 17 |
| giftCardBulkDelete | MUTATION | pass | match | auth_error | 372 |
| orderGrantRefundUpdate | MUTATION | pass | match | graphql_error | 7 |
| checkoutLines | QUERY | fail | mismatch | auth_error | 367 |
| giftCardCreate | MUTATION | pass | match | graphql_error | 7 |
| orderLineAdd | MUTATION | pass | match | graphql_error | 56 |
| promotionRuleUpdate | MUTATION | pass | match | graphql_error | 6 |
| checkoutPaymentCreate | MUTATION | pass | match | graphql_error | 14 |
| giftCardCurrencies | QUERY | pass | match | graphql_error | 4 |
| orderLineDelete | MUTATION | pass | match | auth_error | 367 |
| promotionTranslate | MUTATION | pass | match | graphql_error | 6 |
