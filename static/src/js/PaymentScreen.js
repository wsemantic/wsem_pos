odoo.define('im_od_pos_giftcard.PaymentScreen', function (require) {
    "use strict";

    const PaymentScreen = require('point_of_sale.PaymentScreen');
    const Registries = require('point_of_sale.Registries');
    var core = require('web.core');
    var _t = core._t;


    const CustomPosGiftCardPaymentScreen = PaymentScreen => class extends PaymentScreen {


        async _postPushOrderResolve(order, server_ids) {
            if (this.env.pos.config.use_gift_card) {
				let orderlines=order.get_orderlines();
				if(orderlines !==null){
					let giftline = orderlines.find((line) => line.gift_card_id);
						
					if( typeof giftline !== "undefined" && giftline !== null && giftline.gift_card_id !==null){
						let giftCard = await this.rpc({
							model: "gift.card",
							method: "search_read",
							args: [[['id', '=', giftline.gift_card_id]]],
						});
						if (giftCard.length) {
							order.giftCard = giftCard[0];
						}
					}
				}
            }
            return super._postPushOrderResolve(order, server_ids);
        }
    };

    Registries.Component.extend(PaymentScreen, CustomPosGiftCardPaymentScreen);

    return CustomPosGiftCardPaymentScreen;
});