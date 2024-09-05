odoo.define("im_od_pos_giftcard.gift_card", function (require) {
    "use strict";

    const models = require("point_of_sale.models");


    var _order_super = models.Order.prototype;
    models.Order = models.Order.extend({
        export_for_printing: function () {
            var receipt = _order_super.export_for_printing.apply(
                this,
                arguments
            );
            receipt.giftCard = this.giftCard;


            return receipt;
        },

    });
});