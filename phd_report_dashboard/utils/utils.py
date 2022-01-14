import re
import locale
import base64
import datetime
import time
import odoo
from pytz import timezone
import dateutil

from odoo.tools import formatLang


def format_currency(self, value):
    currency = self.env.user.company_id.currency_id
    return_value = formatLang(self.env, currency.round(value) + 0.0, currency_obj=currency)
    return return_value

def format_percentage(number):
    precision = 2
    str_num_formatted = "{:.{}f}".format(number, precision) + '%'
    return str_num_formatted

def format_human_readable_amount(amount, suffix=''):
    for unit in ['', 'K', 'M', 'G']:
        if abs(amount) < 1000.0:
            return "%3.2f%s%s" % (amount, unit, suffix)
        amount /= 1000.0
    return "%.2f%s%s" % (amount, 'T', suffix)

def format_currency_amount(amount, currency_id, no_break_space=False):
    pre = post = u''
    if currency_id.position == 'before':
        pre = u'{symbol}%s'.format(symbol=currency_id.symbol or '') % \
               (u'\N{NO-BREAK SPACE}' if no_break_space else '', )
    else:
        post = u'%s{symbol}'.format(symbol=currency_id.symbol or '') % \
               (u'\N{NO-BREAK SPACE}' if no_break_space else '', )
    return u'{pre}{0}{post}'.format(amount, pre=pre, post=post)

def get_short_currency_amount(value, currency_id):
    converted_amount = format_human_readable_amount(value)
    short_title = format_currency_amount(converted_amount, currency_id)
    return short_title