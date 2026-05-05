// TODO(A.3): Replace with `import { MaintenanceActivityManager, ActivityMetadata } from '@manomatika/matika-frontend';`
// once matika publishes its npm package. The absolute URL below couples this file to matika's
// static asset serving path; the npm import in A.3 eliminates that URL coupling entirely.
import { MaintenanceActivityManager } from '/static/js/maintenance_activity.js';
import { LookupDialog } from '../dialogs/lookup-dialog.js';
class SecuritiesManager extends MaintenanceActivityManager {
    constructor(metadata) {
        super(metadata);
        this.btnBulkAdd = document.getElementById('btn-bulk-add');
        this.btnBulkDelete = document.getElementById('btn-bulk-delete');
        this.lookupDialog = new LookupDialog();
        this.initSecuritiesListeners();
    }
    initSecuritiesListeners() {
        const lookupButtons = document.querySelectorAll('.btn-lookup');
        lookupButtons.forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const symbolInput = document.getElementById('field-symbol');
                const results = await this.lookupDialog.open({
                    title: "Symbol Lookup",
                    multiSelect: false,
                    initialValue: symbolInput.value
                });
                if (results && results.length > 0) {
                    this.fetchMetadata(results[0].symbol);
                }
            });
        });
        this.btnBulkAdd?.addEventListener('click', () => this.handleBulkAdd());
        this.btnBulkDelete?.addEventListener('click', () => this.handleBulkDelete());
        const refreshButtons = document.querySelectorAll('.btn-refresh-field');
        refreshButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.refreshPrice();
            });
        });
    }
    selectRow(row) {
        super.selectRow(row);
        if (this.selectedRow) {
            this.refreshPrice(true);
        }
    }
    async refreshPrice(silent = false) {
        const symbolInput = document.getElementById('field-symbol');
        const symbol = symbolInput?.value;
        if (!symbol)
            return;
        try {
            if (!silent)
                this.showMessage(`Refreshing price for ${symbol}...`);
            const resp = await fetch(`/eyerate/securities/lookup?symbol=${encodeURIComponent(symbol)}`);
            if (resp.ok) {
                const data = await resp.json();
                const priceInput = document.getElementById('field-current_price');
                if (priceInput && data.current_price) {
                    priceInput.value = data.current_price;
                    if (!silent)
                        this.showMessage(`Updated price for ${symbol}: ${data.current_price}`);
                    this.checkDirty();
                }
            }
        }
        catch (err) {
            if (!silent)
                this.showMessage(`Failed to refresh price for ${symbol}`, true);
        }
    }
    async handleBulkAdd() {
        const results = await this.lookupDialog.open({
            title: "Bulk Add",
            multiSelect: true
        });
        if (results && results.length > 0) {
            this.showMessage(`Adding ${results.length} securities...`);
            const symbols = results.map(r => r.symbol);
            try {
                const resp = await fetch('/eyerate/securities/bulk_create', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ symbols })
                });
                if (resp.ok) {
                    window.location.href = `/eyerate/securities?select=${symbols[0]}`;
                }
                else {
                    const data = await resp.json();
                    this.showMessage(data.detail || "Bulk add failed", true);
                }
            }
            catch (err) {
                this.showMessage(err.message || "An error occurred during bulk add", true);
            }
        }
    }
    async handleBulkDelete() {
        // (3) Implement Bulk Delete
        const allSecurities = [];
        const rows = document.querySelectorAll('#browse-table tbody tr');
        rows.forEach(row => {
            const cells = row.cells;
            if (cells.length >= 2) {
                allSecurities.push({
                    symbol: cells[0].textContent?.trim() || '',
                    name: cells[1].textContent?.trim() || ''
                });
            }
        });
        const results = await this.lookupDialog.open({
            title: "Bulk Delete",
            multiSelect: true,
            defaultChecked: false,
            statusTemplate: "{N} records selected to be deleted",
            preloadedResults: allSecurities
        });
        if (results && results.length > 0) {
            if (!confirm(`Are you sure you want to delete ${results.length} securities?`))
                return;
            this.showMessage(`Deleting ${results.length} securities...`);
            const symbols = results.map(r => r.symbol);
            try {
                const resp = await fetch('/eyerate/securities/bulk_delete', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ symbols })
                });
                if (resp.ok) {
                    window.location.reload();
                }
                else {
                    const data = await resp.json();
                    this.showMessage(data.detail || "Bulk delete failed", true);
                }
            }
            catch (err) {
                this.showMessage(err.message || "An error occurred during bulk delete", true);
            }
        }
    }
    async fetchMetadata(symbol) {
        try {
            this.showMessage(`Fetching metadata for ${symbol}...`);
            const resp = await fetch(`/eyerate/securities/lookup?symbol=${encodeURIComponent(symbol)}`);
            if (!resp.ok) {
                if (resp.status === 404) {
                    throw new Error(`Financial Security details for '${symbol}' not found.`);
                }
                throw new Error(`Lookup failed with status ${resp.status}`);
            }
            const data = await resp.json();
            this.populateFormWithMetadata(data);
            this.showMessage(`Successfully loaded ${symbol}`);
        }
        catch (err) {
            this.showMessage(err.message || "Error fetching security metadata.", true);
        }
    }
    populateFormWithMetadata(data) {
        const mapping = {
            'symbol': data.symbol,
            'name': data.name,
            'security_type': data.security_type,
            'asset_class': data.asset_class,
            'previous_close': data.previous_close,
            'open_price': data.open_price,
            'current_price': data.current_price,
            'nav': data.nav,
            'range_52_week': data.range_52_week,
            'avg_volume': data.avg_volume,
            'yield_30_day': data.yield_30_day,
            'yield_7_day': data.yield_7_day
        };
        Object.keys(mapping).forEach(key => {
            const input = document.getElementById(`field-${key}`);
            if (input && mapping[key] !== undefined) {
                if (key.startsWith('yield_') && mapping[key]) {
                    const num = parseFloat(mapping[key]);
                    if (!isNaN(num)) {
                        input.value = (num * 100).toFixed(2) + '%';
                    }
                    else {
                        input.value = mapping[key];
                    }
                }
                else {
                    input.value = mapping[key] || '';
                }
            }
        });
        this.checkDirty();
    }
    getCreateUrl() { return "/eyerate/securities/create"; }
    getUpdateUrl(id) { return `/eyerate/securities/update/${id}`; }
    getDeleteUrl(id) { return `/eyerate/securities/delete/${id}`; }
}
document.addEventListener('DOMContentLoaded', () => {
    const metadataElement = document.getElementById('metadata-json');
    if (metadataElement) {
        const metadata = JSON.parse(metadataElement.textContent || '{}');
        const manager = new SecuritiesManager(metadata);
        const urlParams = new URLSearchParams(window.location.search);
        const selectSymbol = urlParams.get('select');
        if (selectSymbol) {
            const rows = document.querySelectorAll('#browse-table tbody tr');
            for (const row of rows) {
                const symbolCell = row.cells[0];
                if (symbolCell && symbolCell.textContent?.trim().toUpperCase() === selectSymbol.toUpperCase()) {
                    row.click();
                    break;
                }
            }
        }
    }
});
