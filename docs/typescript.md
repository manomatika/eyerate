# TypeScript Layout Convention

> Back-reference: this file holds the full TypeScript layout and compilation detail
> that was previously inline in `CLAUDE.md` (`## Architecture` → `### TypeScript Layout Convention`).

TypeScript source lives under `src/eyerate/ts/` with mandatory subdirectories:

| Directory | Purpose |
|---|---|
| `ts/admin/` | Admin-page-specific scripts (e.g. `admin-securities.ts`) |
| `ts/dialogs/` | Reusable dialog/modal components (e.g. `lookup-dialog.ts`) |
| `ts/shared/` | Types, utilities, and ambient declarations shared across features |

## Naming Rules

- TypeScript source filenames: `kebab-case.ts`
- Python files: `snake_case.py` (unchanged)
- HTML templates: `snake_case.html` (unchanged — Jinja2 template names are Python-realm)

## Compilation

`tsconfig.json` mirrors the `ts/` subdirectory structure into `src/eyerate/static/js/`:
- `ts/admin/admin-securities.ts` → `static/js/admin/admin-securities.js`
- `ts/dialogs/lookup-dialog.ts` → `static/js/dialogs/lookup-dialog.js`

**Committed output:** Compiled JS is committed to git. The repo is self-contained; no build step is required to run in dev or CI. Run `npm run build` after editing any `.ts` file and commit both the source and the compiled output together.

## Matika-Side Imports

Cross-framework imports use the npm bare specifier `@manomatika/matika-frontend`, e.g.:

```typescript
import { MaintenanceActivityManager, ActivityMetadata } from '@manomatika/matika-frontend';
```

At runtime, matika's `base.html` ships an `<script type="importmap">` that resolves this specifier to `/static/js/index.js` (served from matika's static directory). The npm package on GitHub Packages is consumed at build time for TypeScript type checking; the runtime resolution happens entirely through the import map. The earlier `ts/shared/matika-externals.d.ts` shim and the `paths` entry in `tsconfig.json` (TODO(A.3) markers) were removed when A.3 landed — that directory and entry no longer exist. `npm run build` is still required after editing any `.ts` file; compiled JS is committed alongside source per repo convention.
