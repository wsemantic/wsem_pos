/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { BarcodeReader } from "@point_of_sale/app/barcode/barcode_reader_service";

patch(BarcodeReader.prototype, {
    async _scan(code) {
        console.log("[POS Barcode Case Insensitive] Original code:", code);
        const lowercaseCode = typeof code === 'string' ? code.toLowerCase() : code;
        console.log("[POS Barcode Case Insensitive] Lowercase code:", lowercaseCode);
        return await super._scan(lowercaseCode);
    }
});
