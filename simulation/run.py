#!/usr/bin/python
import os
import sys
from collections import namedtuple
from PIL import Image

import gflags
import pandas as pd
import matplotlib.pyplot as plt

from market import market
from portfolio import portfolio

gflags.DEFINE_multi_int('hours', [6, 12, 24, 36, 48], 'Hours in between market')
gflags.DEFINE_multi_int('offsets', [0, 6, 12, 18], 'Hours to shift markets')
gflags.DEFINE_float('min_percentage_change', 0.1, "Minimum variation in 'balance' needed to place an order."
                    "1 is 100%")
gflags.DEFINE_integer('N', None, "Number of currencies to use")
gflags.DEFINE_string('currencies', None, "comma separated list of currencies")
FLAGS = gflags.FLAGS
gflags.RegisterValidator('min_percentage_change', lambda x: x >=0, 'Should be positive or 0')


Result = namedtuple('Results', ['hour', 'offset', 'rebalance', 'data'])

@gflags.multi_flags_validator(['N', 'currencies'], 'One has to be defined')
def _XOR(flags_dict):
    if not flags_dict['N'] and not flags_dict['currencies']:
        return False
    if flags_dict['N'] and flags_dict['currencies']:
        return False
    return True

BASE = 'USDT'
VALUE = 10000
ONEDAY = 86400.0
t0 = None
OUTPUTDIR = os.path.expanduser('~/Testeo/results/')


def simulate(hour, offset, markets, state, p, rebalance):
    times = []
    values = []
    for current_time, current_market in markets:
        times.append(current_time)
        if rebalance:
            p.rebalance(current_market, state, ['BTC'], FLAGS.min_percentage_change)

        values.append(p.total_value(current_market, ['USDT', 'BTC']))

    data = pd.DataFrame({'time': times, 'value': values})
    data['time'] = (data['time'] - t0) / ONEDAY
    return Result(hour, offset, rebalance, data)


def simulation_name(suffix=None):
    """
    Return a string with all parameters used in the simulation
    
    :return: 
    """
    name = "names_" + FLAGS.currencies.replace(',', '_') +\
           "_hours_" + "_".join([str(h) for h in FLAGS.hours]) +\
           "_offsets_" + "_".join([str(o) for o in FLAGS.offsets]) +\
           "_%change_" + str(int(FLAGS.min_percentage_change * 100))

    if suffix:
        name += suffix

    return name


if __name__ == "__main__":
    global t0
    try:
        argv = FLAGS(sys.argv)
    except gflags.FlagsError as e:
        print "%s\nUsage: %s ARGS\n%s" % (e, sys.argv[0], FLAGS)
        sys.exit(1)

    if not os.path.isdir(OUTPUTDIR):
        os.makedirs(OUTPUTDIR)
    png = os.path.join(OUTPUTDIR, simulation_name(suffix='.png'))
    if os.path.isfile(png):
        img = Image.open(png)
        plt.imshow(img)
        plt.show()

    else:
        results = []

        # do only one simulation without rebalancing as a baseline
        hour = min(FLAGS.hours)
        offset = 0
        markets = market.Markets(3600 * hour, 0)
        t0 = markets.times[0]

        if FLAGS.currencies:
            state, p = portfolio.Portfolio.from_currencies(markets.first_market(), FLAGS.currencies, BASE, VALUE)
        elif FLAGS.N:
            state, p = portfolio.Portfolio.from_largest_markes(markets.first_market(), FLAGS.N, BASE, VALUE)
        results.append(simulate(hour, offset, markets, state, p, False))

        for offset in FLAGS.offsets:
            for hour in FLAGS.hours:
                markets = market.Markets(3600 * hour, 3600 * offset)

                if FLAGS.currencies:
                    state, p = portfolio.Portfolio.from_currencies(markets.first_market(), FLAGS.currencies, BASE, VALUE)
                elif FLAGS.N:
                    state, p = portfolio.Portfolio.from_largest_markes(markets.first_market(), FLAGS.N, BASE, VALUE)

                rebalance = True
                results.append(simulate(hour, offset, markets, state, p, rebalance))

        fig, ax = plt.subplots()
        for r in results:
            ax.plot(r.data['time'], r.data['value'], label="{}_{}_{}".format(r.hour, r.offset, r.rebalance))

        ax.legend(loc=2)
        fig.savefig(png)
        fig.suptitle(png)
        plt.show()

