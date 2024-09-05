odoo.define('im_od_pos_giftcard.ReceiptScreen', function (require) {
    'use strict';

    const Registries = require('point_of_sale.Registries');

    const ReceiptScreen = require('point_of_sale.ReceiptScreen');

    const GiftReceiptScreen = ReceiptScreen => class extends ReceiptScreen {
        constructor() {
            super(...arguments);
            this.orderUiState.printGift = false;
    
        }
        async mounted() {
            super.mounted();
            

        }
        changePrintGift(ev) {
            this.render();
        }
        get hasgift() {
            let orderlines = this.currentOrder.get_orderlines();
            let giftline = this.currentOrder
                .get_orderlines()
                .find((line) => line.gift_card_id);
            return (giftline) ? true : false
        }
    }


    Registries.Component.extend(ReceiptScreen, GiftReceiptScreen);

    return GiftReceiptScreen;
});