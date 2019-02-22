"""Written by RaZ"""

import time
import hmac
import hashlib
import logging
try:
    from urllib import urlencode
    from urlparse import urljoin
except ImportError:
    from urllib.parse import urlencode
    from urllib.parse import urljoin
import requests

BUY_ORDERBOOK = 'buy'
SELL_ORDERBOOK = 'sell'
BOTH_ORDERBOOK = 'both'
ORDER_LIMIT = 'LIMIT'
ORDER_MARKET = 'MARKET'
TIMEINEFFECT_GOOD_TIL_CANCELLED = 'GOOD_TIL_CANCELLED'
TIMEINEFFECT_IMMEDIATE_OR_CANCEL = 'IMMEDIATE_OR_CANCEL'
TIMEINEFFECT_FILL_OR_KILL = 'FILL_OR_KILL'
CONDITION_NONE = 'NONE'
CONDITION_GREATER_THAN = 'GREATER_THAN'
CONDITION_LESS_THAN = 'LESS_THAN'
CONDITION_STOP_LOSS_FIXED = 'STOP_LOSS_FIXED'
CONDITION_STOP_LOSS_PERCENTAGE = 'STOP_LOSS_PERCENTAGE'

BASE_URL = 'https://bittrex.com/api/v2.0/%s/%s/'

PUB_SET = {'getmarketsummaries', 'getcurrencies', 'getwallethealth', 'getbalancedistribution', 'getmarketsummary',
           'getmarketorderbook', 'getmarkethistory', 'getmarkets'}

KEY_SET = {'getorder', 'getorderhistory', 'tradecancel', 'getopenorders', 'getopenorders_all', 'getorderhistory',
           'getbalances', 'getbalance', 'getpendingwithdrawals', 'getwithdrawalhistory', 'getpendingdeposits',
           'getdeposithistory', 'getdepositaddress', 'generatedepositaddress', 'withdrawcurrency'}

PUB_MARKETS_SET = {'getmarketsummaries', 'getmarkets'}
PUB_MARKET_SET = {'getmarketsummary', 'getmarketorderbook', 'getmarkethistory'}
PUB_CURRENCIES_SET = {'getcurrencies', 'getwallethealth'}
PUB_CURRENCY_SET = {'getbalancedistribution'}

KEY_ORDERS_SET = {'getorder', 'getopenorders_all', 'getorderhistory'}
KEY_MARKET_SET = {'tradecancel', 'getopenorders', 'getorderhistory'}
KEY_BALANCE_SET = {'getbalance', 'getbalances', 'getpendingwithdrawals', 'getwithdrawalhistory', 'getpendingdeposits',
                   'getdeposithistory', 'getdepositaddress', 'generatedepositaddress', 'withdrawcurrency'}


# MARKET_SET = {'getopenorders', 'cancel', 'sellmarket', 'selllimit', 'buymarket', 'buylimit'}

# ACCOUNT_SET = {'getbalances', 'getbalance', 'getdepositaddress', 'withdraw', 'getorderhistory'}


class BittrexV2(object):
    """
    Used for requesting Bittrex with API key and API secret
    """
    def __init__(self, api_key, api_secret):
        self.api_key = str(api_key) if api_key is not None else ''
        self.api_secret = str(api_secret) if api_secret is not None else ''

    def api_query(self, method, options=None):
        """
        Queries Bittrex with given method and options

        :param method: Query method for getting info
        :type method: str

        :param options: Extra options for query
        :type options: dict

        :return: JSON response from Bittrex
        :rtype : dict
        """
        if not options:
            options = {}
        nonce = str(int(time.time() * 1000))

        method_set = 'unknown'
        section_set = 'unknown'

        if method in PUB_SET:
            method_set = 'pub'
            if method in PUB_CURRENCIES_SET:
                section_set = 'CURRENCIES'
            elif method in PUB_CURRENCY_SET:
                section_set = 'CURRENCY'
            elif method in PUB_MARKET_SET:
                section_set = 'MARKET'
            elif method in PUB_MARKETS_SET:
                section_set = 'MARKETS'
            else:
                logging.error('Section for pub_set wasnt found!')
        elif method in KEY_SET:
            method_set = 'key'
            if method in KEY_BALANCE_SET:
                section_set = 'BALANCE'
            elif method in KEY_MARKET_SET:
                section_set = 'MARKET'
            elif method in KEY_ORDERS_SET:
                section_set = 'ORDERS'
            else:
                logging.error('Section for key_set wasnt found!')
        else:
            logging.error('Method wasnt found!')

        if method == 'getopenorders_all':
            method = 'getopenorders'

        request_url = (BASE_URL % (method_set, section_set)) + method + '?'

        if method_set != 'pub':
            request_url += 'apikey=' + self.api_key + "&nonce=" + nonce + '&'

        request_url += urlencode(options)
        print(request_url)
        return requests.get(
            request_url,
            headers={"apisign": hmac.new(self.api_secret.encode(), request_url.encode(), hashlib.sha512).hexdigest()}
            ).json()

    def get_market_summaries(self):
        """
        :return: 24-hour summary of all markets in JSON
        """
        return self.api_query('getmarketsummaries')

    def get_currencies(self):
        """
        :return: all currencies currently on Bittrex with their metadata in JSON
        """
        return self.api_query('getcurrencies')

    def get_wallet_health(self):
        """
        :return: returns wallet health in JSON
        """
        return self.api_query('getwallethealth')

    def get_balance_distribution(self, currency):
        """
        Returns the balance distribution for a specific currency
        :param currency: str
        :return: balance distribution in JSON
        """
        return self.api_query('getbalancedistribution', {'currencyname': currency})

    def get_market_summary(self, marketname):
        """
        Returns a 24-hour summary for a specific market
        :param marketname: str
        :return: summary in JSON
        """
        return self.api_query('getmarketsummary', {'marketName': marketname})

    def get_market_order_book(self, marketname):
        """
        Returns the orderbook for a specific market
        :param marketname: str
        :return: orderbook in JSON
        """
        return self.api_query('getmarketorderbook', {'marketname': marketname})

    def get_market_history(self, marketname):
        """
        Returns latest trades that occurred for a specific market
        :param marketname: str
        :return: market history in JSON
        """
        return self.api_query('getmarkethistory', {'marketname': marketname})

    def get_markets(self):
        """
        Returns all markets with their metadata
        :return: list of all markets in JSON
        """
        return self.api_query('getmarkets')

    def get_order(self, orderid):
        """
        Returns information about a specific order (by UUID)
        :param orderid: str
        :return:
        """
        return self.api_query('getorder', {'orderid': orderid})

    def cancel_order(self, orderid):
        """
        Cancels a specific order based on its order's UUID
        :param orderid: str
        :return:
        """
        return self.api_query('tradecancel', {'orderid': orderid})

    def get_open_orders(self, marketname=''):
        """
        Returns your currently open orders in a specific market
        or all your currently open orders if marketname wasn't given
        :param marketname: str
        :return: list of open orders in JSON
        """
        if marketname == '':
            return self.api_query('getopenorders_all')
        else:
            return self.api_query('getopenorders', {'marketname': marketname})

    def get_order_history(self, marketname=''):
        """
        Returns your order history in a specific market
        or all of your order history if marketname wasn't given
        :param marketname: str
        :return: order history in JSON
        """
        if marketname == '':
            return self.api_query('getorderhistory')
        else:
            return self.api_query('getorderhistory', {'marketname': marketname})

    def get_balances(self):
        """
        :return: Returns all current balances in JSON
        """
        return self.api_query('getbalances')

    def get_balance(self, currency):
        """
        Returns the balance of a specific currency
        :param currency: str
        :return: balance in JSON
        """
        return self.api_query('getbalance', {'currencyname': currency})

    def get_pending_withdrawals(self, currency=''):
        """
        Returns pending withdrawals for a specific currency
        or all pending withdrawals if currency wasn't given
        :param currency: str
        :return: pending withdrawals in JSON
        """
        if currency == '':
            return self.api_query('getpendingwithdrawals')
        else:
            return self.api_query('getpendingwithdrawals', {'currencyname': currency})

    def get_withdrawal_history(self, currency=''):
        """
        Returns your withdrawal history for a specific currency
        or your whole withdrawal history if currency wasn't given
        :param currency: str
        :return: withdrawal history in JSON
        """
        if currency == '':
            return self.api_query('getwithdrawalhistory')
        else:
            return self.api_query('getwithdrawalhistory', {'currencyname': currency})

    def get_pending_deposits(self, currency=''):
        """
        Returns pending deposits for a specific currency
        or your all pending deposits if currency wasn't given
        :param currency: str
        :return: pending deposits in JSON
        """
        if currency == '':
            return self.api_query('getpendingdeposits')
        else:
            return self.api_query('getpendingdeposits', {'currencyname': currency})

    def get_deposit_history(self, currency=''):
        """
        Returns your deposit history for a specific currency
        or your whole deposit history if no currency was given
        :param currency: str
        :return: your deposit history in JSON
        """
        if currency == '':
            return self.api_query('getdeposithistory')
        else:
            return self.api_query('getdeposithistory', {'currencyname': currency})

    def get_deposit_address(self, currency):
        """
        Returns your deposit address for a specific currency
        :param currency: str
        :return: your deposit address in JSON
        """
        return self.api_query('getdepositaddress', {'currencyname': currency})

    def generate_deposit_address(self, currency):
        """
        Generates a new deposit address for a specific currency
        :param currency: str
        :return:
        """
        return self.api_query('generatedepositaddress', {'currencyname': currency})

    def withdraw(self, currency, amount, address):
        """
        Withdraws a specific amount of a certain currency to the specified address
        :param currency: str
        :param amount: str
        :param address: str
        :return:
        """
        return self.api_query('withdrawcurrency', {'currencyname': currency, 'quantity': amount, 'address': address})

    def place_order(self, tradetype, market, ordertype, quantity, rate, timeineffect, conditiontype, target):
        """
        Places a buy/sell order with these specific conditions (target only required if a condition is in place
        :param tradetype: str
        :param market: str
        :param ordertype: str
        :param quantity: str
        :param rate: str
        :param timeineffect: str
        :param conditiontype: str
        :param target: str
        :return:
        """
        method = None
        if tradetype == BUY_ORDERBOOK:
            method = 'tradebuy'
        elif tradetype == SELL_ORDERBOOK:
            method = 'tradesell'
        if conditiontype == CONDITION_NONE:
            target = '0'
        return self.api_query(method, {'marketname': market, 'ordertype': ordertype, 'quantity': quantity, 'rate': rate,
                                       'timeineffect': timeineffect, 'conditiontype': conditiontype, 'target': target})

