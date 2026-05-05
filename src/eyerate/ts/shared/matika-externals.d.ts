// TODO(A.3): Delete this file. Once @manomatika/matika-frontend is consumed via npm,
// matika publishes its own type declarations alongside the JS. This ambient module
// declaration becomes redundant and should be removed.
//
// Implementation note: tsconfig.json maps the browser URL
// `/static/js/maintenance_activity.js` to this file via `paths` so TypeScript
// can resolve types at compile time. The emitted JavaScript keeps the original
// URL untouched so the browser fetches from matika's static asset mount.
// When A.3 lands: delete this file, remove the `paths` entry from tsconfig.json,
// and update the import in ts/admin/admin-securities.ts to the npm specifier.

export interface ActivityMetadata {
    browse_panel: {
        search_fields?: Array<{ name: string; label_key: string }>;
        columns: Array<{ name: string; label_key: string }>;
    };
    maintenance_panel: {
        buttons: string[];
        fields: Array<{
            name: string;
            label_key: string;
            read_only: boolean;
            required?: boolean;
            type?: string;
            options_source?: string;
            has_lookup?: boolean;
            suffix?: string;
        }>;
    };
}

export declare class MaintenanceActivityManager {
    protected selectedRow: HTMLElement | null;
    protected isEditing: boolean;
    protected isNew: boolean;
    protected originalData: Record<string, string>;
    constructor(metadata: ActivityMetadata);
    protected showMessage(msg: string, isError?: boolean): void;
    protected selectRow(row: HTMLElement): void;
    protected checkDirty(): void;
    protected getCreateUrl(): string;
    protected getUpdateUrl(id: string): string;
    protected getDeleteUrl(id: string): string;
}
