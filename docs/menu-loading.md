# Menu Loading Pipeline

> Back-reference: this file holds the full menu-loading-pipeline detail
> that was previously inline in `CLAUDE.md` (`## Architecture` → `### Menu Loading Pipeline`).

`MenuLoaderService.load_applug_menus()` reads all `*_menus.json` files from loaded plugins. Role hubs are built by merging the `roles` sections from these files with Matika's core `Role`-type menus.

- **Admin dropdown**: aggregates System items and all applug Admin-role items. When two or more sources contribute items, a `SectionHeader` separates each source. A single-source dropdown never shows a section header.
- **Other role hubs**: built from `Menu`-wrapped items in the matching role's `roles` entry.
- `_build_role_menus` has been removed; role hub construction now derives entirely from `*_menus.json` roles sections plus core menus.
- The `fresh_login` session flag ensures users land on the Default hub immediately after login.
