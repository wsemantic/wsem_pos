odoo.define('wsem_pos.pos_barcode_case_insensitive', function (require) {
    "use strict";

    const BarcodeReader = require('point_of_sale.barcode_reader');

    // Guardar la función scan original
    const originalScan = BarcodeReader.prototype.scan;

    // Redefinir la función scan en el prototipo
    BarcodeReader.prototype.scan = async function(code) {
        console.log("[POS Barcode Case Insensitive] Código original:", code);
        // Convertir el código a minúsculas si es una cadena
        const lowercaseCode = typeof code === 'string' ? code.toLowerCase() : code;
        console.log("[POS Barcode Case Insensitive] Código en minúsculas:", lowercaseCode);
        // Llamar a la función original con el código modificado
        let result = await originalScan.call(this, lowercaseCode);
        console.log("[POS Barcode Case Insensitive] Resultado del scan:", result);
        return result;
    };

    return BarcodeReader;
});