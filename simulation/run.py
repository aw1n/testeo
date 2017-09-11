#!/usr/bin/python
import os
import sys
from collections import namedtuple
from PIL import Image
import tempfile

import cPickle as pickle
import gflags
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from market import market
from portfolio import portfolio
from results import results_utils

gflags.DEFINE_multi_int('hours', [1, 2, 3, 6, 12, 24], 'Hours in between market')
gflags.DEFINE_float('min_percentage_change', 0.1, "Minimum variation in 'balance' needed to place an order."
                    "1 is 100%")
gflags.DEFINE_integer('N', None, "Number of currencies to use")
gflags.DEFINE_boolean('random', None, "Whether to use 'N' random currencies from the given list")
gflags.DEFINE_string('currencies', None, "comma separated list of currencies")
FLAGS = gflags.FLAGS
gflags.RegisterValidator('min_percentage_change', lambda x: x >=0, 'Should be positive or 0')


Result = namedtuple('Results', ['currencies', 'hour', 'rebalance', 'data'])

BASE = 'USDT'
VALUE = 10000
OUTPUTDIR = os.path.expanduser('/var/tmp/simulation/')
try:
    os.makedirs(OUTPUTDIR)
except OSError:
    # folder already exists
    pass


if __name__ == "__main__":
    try:
        argv = FLAGS(sys.argv)
    except gflags.FlagsError as e:
        print "%s\nUsage: %s ARGS\n%s" % (e, sys.argv[0], FLAGS)
        sys.exit(1)


    # do only one simulation without rebalancing as a baseline
    hour = min(FLAGS.hours)
    markets = market.Markets(3600 * hour, 0)

    if FLAGS.currencies:
        currencies = FLAGS.currencies.split(',')
        currencies.sort()

    if FLAGS.N and FLAGS.random and FLAGS.currencies:
        state = portfolio.random_state(currencies, FLAGS.N)
    elif FLAGS.currencies:
        state = portfolio.state_from_currencies(currencies)
    elif FLAGS.N:
        state = portfolio.state_from_largest_markes(markets.first_market(), FLAGS.N)

    results_utils.simulate_set(state, FLAGS.hours, markets, FLAGS.min_percentage_change, BASE, VALUE)
    results_utils.final_analysis()

