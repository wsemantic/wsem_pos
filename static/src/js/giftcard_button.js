odoo.define("im_od_pos_giftcard.GiftCardButton", function (require) {
    "use strict";

    const PosComponent = require("point_of_sale.PosComponent");
    const ProductScreen = require("point_of_sale.ProductScreen");
    const { useListener } = require("web.custom_hooks");
    const Registries = require("point_of_sale.Registries");
    const { Gui } = require("point_of_sale.Gui");
    const GiftCardButton = require('pos_gift_card.GiftCardButton');

    const PosGiftCardButton = GiftCardButton => class extends GiftCardButton {
        //@Override

        async onClick() {
            
            let currentOrder = this.env.pos.get_order();
            let amount = 0;
            if (currentOrder.get_total_with_tax()<0) {
                amount = Math.round(Math.abs(currentOrder.get_total_with_tax())*100)/100;
            }
            this.showPopup("GiftCardPopup", {
                amount: amount,
                giftCard: false,
                giftCardBarcode:  undefined
            });
        }

    }

    Registries.Component.extend(GiftCardButton, PosGiftCardButton);

    return PosGiftCardButton;
});