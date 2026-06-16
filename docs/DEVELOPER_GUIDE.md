**EyeRate** | Version: **v0.0.4** | Copyright (c) 2026 Patrick James Tallman

# EyeRate Developer Guide

Reference for developers working on EyeRate or using it as a model for building new AppLugs.

---

## Prerequisites

EyeRate is a **Matika AppLug** — it runs *inside* Matika and cannot run standalone. You need:

- A working Matika installation (see `matika/docs/DEVELOPER_GUIDE.md`)
- Python 3.12+ with the `eyerate` virtualenv active (or `../matika/.venv`)
- Node.js 18+ and npm

Both repos must be cloned as siblings:
```
~/dev/projects/
  matika/    ← framework (required)
  eyerate/   ← this repo
```

---

## Running Tests

Tests require `../matika` as a sibling directory.

```bash
export PYTHONPATH=src:../matika/src
python -m pytest tests/
```

Single test:
```bash
python -m pytest tests/integration/test_securities.py::test_securities_crud
```

All tests must pass (`0 failed, 0 skipped, 0 xfail`) before opening a PR.

---

## TypeScript

Source lives under `src/eyerate/ts/`. Compiled output goes to `src/eyerate/static/js/` and is committed alongside source.

```bash
npm install     # one-time
npm run build   # compile after any .ts change
```

Always commit both `.ts` source and the compiled `.js` output together.

---

## `*_menus.json` Schema

The consolidated menu file (`eyerate_menus.json`) is the sole source of truth for every menu EyeRate contributes to Matika. Menu structure is never stored in the database — it is loaded from this file at startup and cached in memory.

The file must be named `<plugin_id>_menus.json` and placed in the plugin root directory.

### Schema version

```json
{ "schema_version": "1.0", "menus": { ... } }
```

`schema_version` must be `"1.0"`. Files with other versions are skipped at startup with a warning.

### Top-level sections (all optional)

| Key | Shape | Purpose |
|---|---|---|
| `application` | single dict | App-wide menu visible to all authenticated users (Applications section of the selector) |
| `roles` | array of role entries | Per-role menus; each entry targets one role by name (Roles section, shown only to users who hold that role) |
| `system` | single dict | Framework-level menu rendered last in every hub (e.g. Help). Reserved for framework use; AppLugs may omit it. |

### `application` section

Single dict with `id`, `label_key`, and `items`. Items can be `Link`, `Menu`, or `Separator` type.

```json
"application": {
  "id": "eyerate-main",
  "label_key": "menu_eyerate",
  "items": [
    { "type": "Link", "label_key": "item_securities", "href": "/eyerate/securities" }
  ]
}
```

### `roles` section

Array of role entries. Each entry targets one role:

```json
"roles": [
  {
    "role": "RoleName",
    "id": "unique-role-id",
    "label_key": "i18n_key",
    "items": [ ... ]
  }
]
```

**Critical rule — item wrapping differs by role:**

- **User role (and any non-Admin role):** Items must be wrapped in a `Menu` object. This produces a named dropdown in the User hub.

  ```json
  {
    "role": "User",
    "id": "eyerate-user",
    "label_key": "menu_eyerate",
    "items": [
      {
        "type": "Menu",
        "label_key": "menu_eyerate",
        "items": [
          { "type": "Link", "label_key": "item_securities", "href": "/eyerate/securities" }
        ]
      }
    ]
  }
  ```

- **Admin role:** Items must be **flat `Link` entries with no `Menu` wrapper**. They are aggregated directly into the Admin dropdown alongside items from other sources. Wrapping Admin items in a `Menu` object is incorrect and will produce nested menus that do not match the Admin hub layout.

  ```json
  {
    "role": "Admin",
    "id": "eyerate-admin",
    "label_key": "menu_eyerate",
    "items": [
      { "type": "Link", "label_key": "item_eyerate_admin", "href": "/eyerate/admin" }
    ]
  }
  ```

### Admin dropdown — SectionHeader injection

Matika's Admin dropdown aggregates items from all sources: core admin menus and every loaded AppLug's Admin role entry. When **two or more sources** contribute items, Matika automatically injects `SectionHeader` items to visually separate each source in the dropdown. A single-source dropdown never shows section headers.

This means:
- When EyeRate is the only AppLug, the Admin dropdown shows EyeRate's items with no headers.
- When multiple AppLugs are loaded, each source's items are grouped under an auto-generated header labelled with that source's `label_key`.

No special configuration is needed in `*_menus.json` to trigger this behaviour — Matika handles it at runtime.

### `system` section

Same shape as `application`. Renders last in every hub. Used by Matika core for the Help menu. AppLugs may omit this section.

### Item types

| Type | Fields | Notes |
|---|---|---|
| `Link` | `label_key`, `href`, optional `open_new_tab` | Navigates to `href`. Set `open_new_tab: true` to open in a new tab. |
| `Menu` | `label_key`, `items` (array of `Link` or `Separator`) | Produces a named dropdown. Used in non-Admin role entries only. |
| `Separator` | _(none)_ | Visual divider between items. |

### Complete example (all three sections)

```json
{
  "schema_version": "1.0",
  "menus": {
    "application": {
      "id": "myplugin-main",
      "label_key": "menu_myplugin",
      "items": [
        { "type": "Link", "label_key": "item_dashboard", "href": "/myplugin/dashboard" },
        { "type": "Separator" },
        { "type": "Link", "label_key": "item_reports", "href": "/myplugin/reports", "open_new_tab": false }
      ]
    },
    "roles": [
      {
        "role": "User",
        "id": "myplugin-user",
        "label_key": "menu_myplugin",
        "items": [
          {
            "type": "Menu",
            "label_key": "menu_myplugin",
            "items": [
              { "type": "Link", "label_key": "item_dashboard", "href": "/myplugin/dashboard" }
            ]
          }
        ]
      },
      {
        "role": "Admin",
        "id": "myplugin-admin",
        "label_key": "menu_myplugin",
        "items": [
          { "type": "Link", "label_key": "item_myplugin_admin", "href": "/myplugin/admin" }
        ]
      }
    ],
    "system": {
      "id": "myplugin-help",
      "label_key": "menu_help",
      "items": [
        { "type": "Link", "label_key": "item_help_docs", "href": "/myplugin/help" }
      ]
    }
  }
}
```

---

## Security Requirements

All EyeRate POST routes must include:

```python
_auth: User = Depends(check_page_permission)
_csrf = Depends(validate_csrf)
```

GET routes that call external APIs (search, lookup) must include `Depends(login_required)`.

Bulk JSON-body routes (`bulk_create`, `bulk_delete`) use `check_page_permission` only — JSON requests are not CSRF-vulnerable.

---

## Release Pipeline

See `CLAUDE.md` for the full release procedure. Key points:

- `VERSION` is the single source of truth. Never edit `applug.json` version fields by hand.
- A version is a **core** (`X.Y.Z`) plus an optional pre-release suffix on the ladder `X.Y.Z-dev < X.Y.Z-rc.N < X.Y.Z`. The suffix lives only on `VERSION`, tags, and release titles; manifest fields hold **bare core** (everything before the first `-`).
- `scripts/release.py <version>` accepts a final core or a pre-release target (`0.0.4-rc.1`, `0.0.4-dev`), propagates the bare core into `applug.json`, and commits. Does not push or tag.
- `scripts/sync_version.py --check` verifies no drift between `VERSION` and `applug.json`.

---

## Further Reading

- `matika/docs/DEVELOPER_GUIDE.md` — full AppLug contract, compatibility rules, and cold-start instructions
- `matika/docs/DEPLOYMENT.md` — server deployment patterns
- `matika/docs/ARCHITECTURE.md` — framework architecture
