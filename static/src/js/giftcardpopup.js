odoo.define("im_od_pos_giftcard.GiftCardPopup", function (require) {
    "use strict";

    const PosComponent = require("point_of_sale.PosComponent");
    const ProductScreen = require("point_of_sale.ProductScreen");
    const { useListener } = require("web.custom_hooks");
    const Registries = require("point_of_sale.Registries");
    const { Gui } = require("point_of_sale.Gui");
    const GiftCardPopup = require('pos_gift_card.GiftCardPopup');

    const PosGiftCardPopup = GiftCardPopup => class extends GiftCardPopup {
        //@Override

        constructor() {
            super(...arguments);
			this.state.amountToSet = this.props.amount;
			 
           
            this.state.giftCardBarcode = this.props.giftCardBarcode;
            if (this.state.giftCardBarcode){
                this.switchBarcodeView();
            }
        }


    }

    Registries.Component.extend(GiftCardPopup, PosGiftCardPopup);

    return PosGiftCardPopup;
});