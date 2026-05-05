var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
import { MaintenanceActivityManager } from './maintenance_activity.js';
import { LookupDialog } from './lookup_dialog.js';
class SecuritiesManager extends MaintenanceActivityManager {
    constructor(metadata) {
        super(metadata);
        this.btnBulkAdd = document.getElementById('btn-bulk-add');
        this.btnBulkDelete = document.getElementById('btn-bulk-delete');
        this.lookupDialog = new LookupDialog();
        this.initSecuritiesListeners();
    }
    initSecuritiesListeners() {
        var _a, _b;
        const lookupButtons = document.querySelectorAll('.btn-lookup');
        lookupButtons.forEach(btn => {
            btn.addEventListener('click', (e) => __awaiter(this, void 0, void 0, function* () {
                e.stopPropagation();
                const symbolInput = document.getElementById('field-symbol');
                const results = yield this.lookupDialog.open({
                    title: "Symbol Lookup",
                    multiSelect: false,
                    initialValue: symbolInput.value
                });
                if (results && results.length > 0) {
                    this.fetchMetadata(results[0].symbol);
                }
            }));
        });
        (_a = this.btnBulkAdd) === null || _a === void 0 ? void 0 : _a.addEventListener('click', () => this.handleBulkAdd());
        (_b = this.btnBulkDelete) === null || _b === void 0 ? void 0 : _b.addEventListener('click', () => this.handleBulkDelete());
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
    refreshPrice() {
        return __awaiter(this, arguments, void 0, function* (silent = false) {
            const symbolInput = document.getElementById('field-symbol');
            const symbol = symbolInput === null || symbolInput === void 0 ? void 0 : symbolInput.value;
            if (!symbol)
                return;
            try {
                if (!silent)
                    this.showMessage(`Refreshing price for ${symbol}...`);
                const resp = yield fetch(`/admin/securities/lookup?symbol=${encodeURIComponent(symbol)}`);
                if (resp.ok) {
                    const data = yield resp.json();
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
        });
    }
    handleBulkAdd() {
        return __awaiter(this, void 0, void 0, function* () {
            const results = yield this.lookupDialog.open({
                title: "Bulk Add",
                multiSelect: true
            });
            if (results && results.length > 0) {
                this.showMessage(`Adding ${results.length} securities...`);
                const symbols = results.map(r => r.symbol);
                try {
                    const resp = yield fetch('/admin/securities/bulk_create', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ symbols })
                    });
                    if (resp.ok) {
                        window.location.href = `/admin/securities?select=${symbols[0]}`;
                    }
                    else {
                        const data = yield resp.json();
                        this.showMessage(data.detail || "Bulk add failed", true);
                    }
                }
                catch (err) {
                    this.showMessage(err.message || "An error occurred during bulk add", true);
                }
            }
        });
    }
    handleBulkDelete() {
        return __awaiter(this, void 0, void 0, function* () {
            // (3) Implement Bulk Delete
            const allSecurities = [];
            const rows = document.querySelectorAll('#browse-table tbody tr');
            rows.forEach(row => {
                var _a, _b;
                const cells = row.cells;
                if (cells.length >= 2) {
                    allSecurities.push({
                        symbol: ((_a = cells[0].textContent) === null || _a === void 0 ? void 0 : _a.trim()) || '',
                        name: ((_b = cells[1].textContent) === null || _b === void 0 ? void 0 : _b.trim()) || ''
                    });
                }
            });
            const results = yield this.lookupDialog.open({
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
                    const resp = yield fetch('/admin/securities/bulk_delete', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ symbols })
                    });
                    if (resp.ok) {
                        window.location.reload();
                    }
                    else {
                        const data = yield resp.json();
                        this.showMessage(data.detail || "Bulk delete failed", true);
                    }
                }
                catch (err) {
                    this.showMessage(err.message || "An error occurred during bulk delete", true);
                }
            }
        });
    }
    fetchMetadata(symbol) {
        return __awaiter(this, void 0, void 0, function* () {
            try {
                this.showMessage(`Fetching metadata for ${symbol}...`);
                const resp = yield fetch(`/admin/securities/lookup?symbol=${encodeURIComponent(symbol)}`);
                if (!resp.ok) {
                    if (resp.status === 404) {
                        throw new Error(`Financial Security details for '${symbol}' not found.`);
                    }
                    throw new Error(`Lookup failed with status ${resp.status}`);
                }
                const data = yield resp.json();
                this.populateFormWithMetadata(data);
                this.showMessage(`Successfully loaded ${symbol}`);
            }
            catch (err) {
                this.showMessage(err.message || "Error fetching security metadata.", true);
            }
        });
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
    getCreateUrl() { return "/admin/securities/create"; }
    getUpdateUrl(id) { return `/admin/securities/update/${id}`; }
    getDeleteUrl(id) { return `/admin/securities/delete/${id}`; }
}
document.addEventListener('DOMContentLoaded', () => {
    var _a;
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
                if (symbolCell && ((_a = symbolCell.textContent) === null || _a === void 0 ? void 0 : _a.trim().toUpperCase()) === selectSymbol.toUpperCase()) {
                    row.click();
                    break;
                }
            }
        }
    }
});
