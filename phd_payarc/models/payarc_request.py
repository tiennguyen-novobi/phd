import requests


class PayarcError(Exception):
    pass


class PayarcRequest(object):

    access_token: str

    def __init__(self, payarc_info):
        credentials = self.extract_credentials(payarc_info)
        for k, v in credentials.items():
            setattr(self, k, v)
        self.batch_url = 'https://api.payarc.net/v1/deposit/summary'

    @classmethod
    def extract_credentials(cls, payarc_info):
        return {
            'access_token': payarc_info['payarc_access_token']
        }

    def _generate_header(self):
        return {
            'Accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Authorization': 'Bearer %s' % self.access_token
        }

    def parse_payarc_batch_report_reponse_data(self, raw_datas):
        res = []
        datas = raw_datas['rows_data']

        for date, row in datas.items():
            if 'row_totals' in row:
                for deposit in row['row_data']:
                    if 'transType' in deposit and deposit['transType'] == 'DEPOSIT':
                        res.append({
                            'amount': deposit['amount'],
                            'batch_ref': deposit['batch_reference_number'],
                            'transaction_qty': deposit['transaction_count'],
                            'date': row['row_totals']['Settlement_Date']
                        })
        return res

    def get_batch_from_payarc(self, from_date, to_date):
        headers = self._generate_header()
        params = {
            'from_date': from_date,
            'to_date': to_date
        }

        response = requests.get(url=self.batch_url, headers=headers, params=params)
        if response.ok:
            return self.parse_payarc_batch_report_reponse_data(response.json()['data'])
        else:
            error_message = response.json().get('error_description')
            raise PayarcError("Something went wrong while getting Batch Report!\n%s" % error_message)
