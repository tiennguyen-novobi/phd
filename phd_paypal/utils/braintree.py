import braintree
import logging

_logger = logging.getLogger(__name__)


class BrainTree:
    def __init__(self, credentials):
        self.gateway = braintree.BraintreeGateway(
            braintree.Configuration(
                braintree.Environment.Production,
                merchant_id=credentials['merchant_id'],
                public_key=credentials['public_key'],
                private_key=credentials['private_key']
            )
        )

    def search_transaction(self, date):
        collection = self.gateway.transaction.search([
            braintree.TransactionSearch.settled_at >= date
        ])
        transactions = []
        for transaction in collection.items:
            transactions.append(transaction)

        return transactions
