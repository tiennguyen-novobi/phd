from ..utils.braintree import BrainTree


class PaypalError(Exception):
    pass


class PaypalRequest(object):

    def __init__(self, braintree_credentials):
        credentials = self.extract_credentials(braintree_credentials)
        self.braintree_gateway = BrainTree(credentials)

    @classmethod
    def extract_credentials(cls, braintree_credentials):
        return {
            'merchant_id': braintree_credentials['merchant_id'],
            'public_key': braintree_credentials['public_key'],
            'private_key': braintree_credentials['private_key']
        }

    @classmethod
    def _parse_authorization_id(cls, data):
        if data.payment_instrument_type == 'paypal_account':
            return data.paypal_details.authorization_id
        elif data.payment_instrument_type == 'paypal_here':
            return data.paypal_here_details.authorization_id
        return ''

    @classmethod
    def _parse_transaction_fee(cls, data):
        if data.payment_instrument_type == 'paypal_account':
            return float(data.paypal_details.transaction_fee_amount or 0)
        elif data.payment_instrument_type == 'paypal_here':
            return float(data.paypal_here_details.transaction_fee_amount or 0)
        return 0

    @classmethod
    def parse_braintree_transaction(cls, datas, settled_at):
        result = []
        for data in datas:
            result.append({
                'transaction_id': data.id,
                'date': settled_at,
                'order_id': data.order_id,
                'amount': float(data.amount),
                'authorization_id': cls._parse_authorization_id(data),
                'paypal_fee_amount': cls._parse_transaction_fee(data)
            })
        return result

    def get_transaction_by_date(self, settled_at):
        try:
            datas = self.braintree_gateway.search_transaction(settled_at)
            transactions = self.parse_braintree_transaction(datas, settled_at)
            return transactions
        except Exception as e:
            raise PaypalError("Something went wrong while getting Paypal Transaction via BrainTree!\n%s" % e)
