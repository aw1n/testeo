#!/usr/bin/python
import os

import pandas as pd

from market import market
from portfolio import portfolio
from simulations_code import simulate


if __name__ == "__main__":

    print '*' * 80
    # currently we have only XRP in bittrex, start a portfolio with 'desired' state given only by 'XRP' and 'ETH'
    desired_state = portfolio.state_from_currencies(['ADA', 'TRIG', 'OK', 'RISE', 'IOP', 'NAV', 'MONA', 'EMC2',
                                                     'ADX', 'VTC', 'MCO', 'XVG', 'SYS', 'XLM', 'KMD', 'TKN'])

    current_market = market.Market.from_bittrex()
    p = portfolio.Portfolio.from_bittrex()

    # The first time, I run with this series, limit = pd.Series({'XRP': 0, 'ETH': 0, 'BTC': 0.165})
    # but after the original portfolio was created I changed it to the next line, not spending more bitcoins but
    # just trading between selected cryptocurrencies
    # There is a problem with my implementation. When trades are not places, and BTC are not operated
    # some money might be shifting into BTC indefinitely.
    # When I started Portfolio_1, I originaly had 0.66038387 BTC
    # From those, I traded 0.165 BTC leaving a balance of 0.49538387 BTC
    # Therefore I have to trade anythhing over the balance 0.49538387 BTC
    btc_balance_to_trade = p.dataframe.loc['BTC', 'Available'] - 0.49538387
    limit = pd.Series({'XRP': 0, 'ETH': 0, 'BTC': btc_balance_to_trade})
    p.limit_to(limit)

    p2 = portfolio.Portfolio.from_csv(os.path.expanduser(('~/Testeo/results/Portfolio_1/original_portfolio.csv')))

    # compare portfolios
    merged = p.dataframe.merge(p2.dataframe, left_index=True, right_index=True, suffixes=['_trade', '_hold'])[['Balance_hold', 'Balance_trade']]
    merged.loc[:, 'diff'] = merged['Balance_trade'] - merged['Balance_hold']
    merged.loc[:, '% diff'] = merged['diff'] * 100 / merged['Balance_hold']
    print merged

    trading_value = p.total_value(current_market, ['USDT', 'BTC'])
    holding_value = p2.total_value(current_market, ['USDT', 'BTC'])
    print 'Current value trading is: {}(USD)'.format(trading_value)
    print 'Current value holding is: {}(USD)'.format(holding_value)

    print 'ratio is: ', trading_value / holding_value
