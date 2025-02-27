odoo.define('wsem_pos.pos_barcode_case_insensitive', function (require) {
    "use strict";

    const BarcodeReader = require('point_of_sale.barcode_reader');
    const Registries = require('point_of_sale.Registries');

    // Extender el componente BarcodeReader mediante una clase ES6
    // Extender el componente BarcodeReader utilizando ES6
    const BarcodeReaderCaseInsensitive = (BarcodeReader) =>
        class extends BarcodeReader {
            async scan(code) {
                console.log("[POS Barcode Case Insensitive] Código original:", code);
                // Verificar si el código es una cadena y convertirlo a minúsculas
                const lowercaseCode = typeof code === 'string' ? code.toLowerCase() : code;
                console.log("[POS Barcode Case Insensitive] Código en minúsculas:", lowercaseCode);
                // Llamar al método original utilizando super() y almacenar el resultado
                let result = await super.scan(lowercaseCode);
                console.log("[POS Barcode Case Insensitive] Resultado del scan:", result);
                return result;
            }
        };

    // Registrar la extensión para que se aplique sin reemplazar por completo el componente original
    Registries.Component.extend(BarcodeReader, BarcodeReaderCaseInsensitive);


    return BarcodeReader;
});
