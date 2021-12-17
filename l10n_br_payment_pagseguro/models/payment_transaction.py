# Copyright 2020 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
import requests
import pprint

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

INT_CURRENCIES = [
    u'BRL', u'XAF', u'XPF', u'CLP', u'KMF', u'DJF', u'GNF', u'JPY', u'MGA',
    u'PYG', u'RWF', u'KRW',
    u'VUV', u'VND', u'XOF'
    ]


class PaymentTransactionCielo(models.Model):
    _inherit = 'payment.transaction'

    pagseguro_s2s_capture_link = fields.Char(
        string="Capture Link",
        required=False,
        )

    pagseguro_s2s_void_link = fields.Char(
        string="Void Link",
        required=False,
        )

    pagseguro_s2s_check_link = fields.Char(
        string="Check Link",
        required=False,
        )

    def _create_pagseguro_charge(self, acquirer_ref=None, tokenid=None,
                             email=None):
        """Creates the s2s payment.

        Uses credit card token instead of secret info.

        """
        api_url_charge = 'https://%s/charges' % (
            self.acquirer_id._get_pagseguro_api_url())

        # Odoo uses 'mastercard' name, pagseguro uses 'master'
        if self.payment_token_id.card_brand == 'mastercard':
            self.payment_token_id.card_brand = 'master'

        # TODO - Resivar campos e origem das informações
        charge_params = {
            "reference_id": str(self.payment_token_id.acquirer_id),
            "description": "Motivo do pagamento",
            "amount": {
                # Charge is in BRL cents -> Multiply by 100
                "value": int(self.amount * 100),
                "currency": "BRL",
                },
            "payment_method": {
                "type": "CREDIT_CARD",
                "installments": 1,
                "capture": False,
                "soft_descriptor": self.display_name[:13],
                "card": {
                    "number": self.payment_token_id.card_number,
                    "exp_month": "03",
                    "exp_year": "2026",
                    "security_code": self.payment_token_id.card_cvc,
                    "holder": {
                        "name": self.partner_id.name
                    }
                    # "CardToken": self.payment_token_id.pagseguro_token,
                    # "Brand": self.payment_pagseguro_id.card_brand,
                    # "SaveCard": "true"
                    }
                }
            }

        self.payment_token_id.active = False

        _logger.info("_create_pagseguro_charge: Sending values to URL %s", api_url_charge)
        r = requests.post(api_url_charge,
                          json=charge_params,
                          headers=self.acquirer_id._get_pagseguro_api_headers())
        res = r.json()
        _logger.info('_create_pagseguro_charge: Values received:\n%s',
                     pprint.pformat(res))
        return res

    @api.multi
    def pagseguro_s2s_do_transaction(self, **kwargs):
        self.ensure_one()
        result = self._create_pagseguro_charge(
            acquirer_ref=self.payment_token_id.acquirer_ref,
            email=self.partner_email)
        return self._pagseguro_s2s_validate_tree(result)

    @api.multi
    def cielo_s2s_capture_transaction(self):
        """Captures an authorized transaction."""
        _logger.info(
            'cielo_s2s_capture_transaction: Sending values to URL %s',
            self.cielo_s2s_capture_link)
        r = requests.put(self.cielo_s2s_capture_link,
                         headers=self.acquirer_id._get_cielo_api_headers())
        res = r.json()
        _logger.info('cielo_s2s_capture_transaction: Values received:\n%s',
                     pprint.pformat(res))
        # analyse result
        if type(res) == dict and res.get('ProviderReturnMessage') and res.get(
                'ProviderReturnMessage') == 'Operation Successful':
            # apply result
            self.write({
                'date': fields.datetime.now(),
                'acquirer_reference': res,
                })
            self._set_transaction_done()
            self.execute_callback()
        else:
            self.sudo().write({
                'state_message': res,
                'acquirer_reference': res,
                'date': fields.datetime.now(),
                })

    @api.multi
    def cielo_s2s_void_transaction(self):
        """Voids an authorized transaction."""
        _logger.info(
            'cielo_s2s_void_transaction: Sending values to URL %s',
            self.cielo_s2s_void_link)
        r = requests.put(self.cielo_s2s_void_link,
                         headers=self.acquirer_id._get_cielo_api_headers())
        res = r.json()
        _logger.info('cielo_s2s_void_transaction: Values received:\n%s',
                     pprint.pformat(res))
        # analyse result
        if type(res) == dict and res.get('ProviderReturnMessage') and res.get(
                'ProviderReturnMessage') == 'Operation Successful':
            # apply result
            self.write({
                'date': fields.datetime.now(),
                'acquirer_reference': res,
                })
            self._set_transaction_cancel()
        else:
            self.sudo().write({
                'state_message': res,
                'acquirer_reference': res,
                'date': fields.datetime.now(),
                })

    @api.multi
    def _pagseguro_s2s_validate_tree(self, tree):
        """Validates the transaction.

        This method updates the payment.transaction object describing the
        actual transaction outcome.
        Also saves get/capture/void links sent by cielo to make it easier to
        perform the operations.

        """
        self.ensure_one()
        if self.state != 'draft':
            _logger.info(
                'Cielo: trying to validate an already validated tx (ref %s)',
                self.reference)
            return True

        if type(tree) != list:
            # status = tree.get('Payment').get('Status')
            status = status = tree.get('status')

            # if status == 'AUTHORIZED':

                # TODO - Continuar o fluxo conforme necessário

            #         self.write({
            #         'date': fields.datetime.now(),
            #         'acquirer_reference': tree.get('id'),
            #         })
            #     # store capture and void links for future manual operations
            #     for method in tree.get('Payment').get('Links'):
            #         if 'Rel' in method and 'Href' in method:
            #             if method.get('Rel') == 'self':
            #                 self.pagseguro_s2s_check_link = method.get('Href')
            #             if method.get('Rel') == 'capture':
            #                 self.pagseguro_s2s_capture_link = method.get('Href')
            #             if method.get('Rel') == 'void':
            #                 self.pagseguro_s2s_void_link = method.get('Href')
            #
            #     # setting transaction to authorized - must match Cielo
            #     # payment using the case without automatic capture
            #     self._set_transaction_authorized()
            #     self.execute_callback()
            #     if self.payment_token_id:
            #         self.payment_token_id.verified = True
            #     return True
            # else:
            #     error = tree.get('Payment').get('ReturnMessage')
            #     _logger.warn(error)
            #     self.sudo().write({
            #         'state_message': error,
            #         'acquirer_reference': tree.get('id'),
            #         'date': fields.datetime.now(),
            #         })
            #     self._set_transaction_cancel()
            #     return False

        elif type(tree) == list:
            error = tree[0].get('Message')
            _logger.warn(error)
            self.sudo().write({
                'state_message': error,
                'date': fields.datetime.now(),
                })
            self._set_transaction_cancel()
            return False
