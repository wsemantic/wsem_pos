/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

// PERF — Memoización del grid de productos del POS.
//
// Problema (Odoo core, no de este módulo):
// El getter `productsToDisplay` de ProductScreen (el que usa la plantilla,
// t-foreach) filtra y ordena TODOS los productos cargados aplicando
// `unaccent(searchString)` a cada uno. Como es un getter usado en el render, Owl
// lo recalcula en CADA re-render. Y cualquier cambio
// del pedido (añadir una línea al hacer clic o al escanear) provoca un re-render
// de la pantalla completa, aunque la lista visible del grid no haya cambiado.
// Con catálogos grandes (decenas de miles de variantes talla/color) ese recálculo
// cuesta ~1-2 s por clic; con pocos productos es instantáneo.
//
// Solución:
// Cachear el resultado del grid y reutilizarlo mientras no cambie lo que de verdad
// afecta a la lista visible: el texto de búsqueda, la categoría seleccionada y el
// número de productos cargados (por si entra alguno bajo demanda). Un cambio del
// pedido —clic, escaneo, apertura del diálogo de variantes, validar, imprimir— NO
// altera esa clave, así que devuelve la caché sin recorrer los N productos.
// La caché vive en la instancia del componente (persiste entre renders) y solo se
// reconstruye cuando cambia la clave.
patch(ProductScreen.prototype, {
    get productsToDisplay() {
        const model = this.pos.models["product.product"];
        // conteo O(1) de productos cargados (con fallback defensivo)
        const loadedCount = model.records?.[model.modelName]?.size ?? model.getAll().length;
        const key = `${this.searchWord}|${this.pos.selectedCategory?.id ?? 0}|${loadedCount}`;

        if (key === this._wsemGridKey) {
            return this._wsemGridCache;
        }
        this._wsemGridKey = key;
        this._wsemGridCache = super.productsToDisplay;
        return this._wsemGridCache;
    },
});
