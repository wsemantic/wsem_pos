odoo.define('wsem_pos.pos_barcode_case_insensitive', function (require) {
    "use strict";

    const BarcodeReader = require('point_of_sale.barcode_reader');
    const Registries = require('point_of_sale.Registries');

    // Extender el componente BarcodeReader mediante una clase ES6
    const BarcodeReaderCaseInsensitive = (BarcodeReader) =>
        class extends BarcodeReader {
            async scan(code) {
                // Verificar si el código es una cadena y convertirlo a minúsculas
                const lowercaseCode = typeof code === 'string' ? code.toLowerCase() : code;
                // Llamar al método original utilizando super()
                return await super.scan(lowercaseCode);
            }
        };

    // Registrar la extensión utilizando el sistema de Registries
    Registries.Component.extend(BarcodeReader, BarcodeReaderCaseInsensitive);

    return BarcodeReader;
});
