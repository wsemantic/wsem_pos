odoo.define('im_od_pos_giftcard.OrderReceipt', function (require) {
    'use strict';

    const Registries = require('point_of_sale.Registries');
    const OrderReceipt = require('point_of_sale.OrderReceipt');
    
    const GiftOrderReceipt = OrderReceipt => class extends OrderReceipt {

        get giftCard() {
            return this.receiptEnv.receipt.giftCard;
        }

    }
    Registries.Component.extend(OrderReceipt, GiftOrderReceipt);

    return GiftOrderReceipt;
});