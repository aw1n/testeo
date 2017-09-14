#!/usr/bin/python
import os
import json
import time
from itertools import product

import numpy as np
import pandas as pd

from portfolio import portfolio
import bittrex_utils


ONEDAY = 86400.0
FOLDER = os.path.expanduser('~/Testeo/simulations/test/')
PARAMS = os.path.join(FOLDER, 'params.csv')
DATAFOLDER = os.path.join(FOLDER, 'data')
try:
    os.makedirs(DATAFOLDER)
except:
    pass


def simulate_set(state, hours, markets, min_percentage_change, base, value):
    """ Just run 'simulate' for each hour in 'hours' and append the results
    All other parameters are the same except that the 1st hour is simulated
    twice, first with 'rebalance' set to False as the baseline
    """
    timestamp = int(time.time())
    # compute the baseline
    baseline = simulate(state, min(hours), markets, min_percentage_change, False, base, value)
    save_data(timestamp, min(hours), False, baseline)
    save_simulaton_params(timestamp, state, min(hours), False)

    for hour in hours:
        data = simulate(state, hour, markets, min_percentage_change, True, base, value)
        save_data(timestamp, hour, True, data)
        save_simulaton_params(timestamp, state, hour, True)


def save_simulaton_params(timestamp, state, hour, rebalance):
    """
    :param state: 
    :param hour: 
    :param rebalance: 
    :param data: 
    :return: 
    """

    '''
    N = len(currencies)
    datadict = {'N':N,
                'rebalance': rebalance,
                'hour': hour,
                }
    '''


    # first add all currencies to the dict as key with associated value of 'False'
    datadict = {currency: False for currency in bittrex_utils.currencies_df().index}

    # Now change the value to True for those currencies used in the data
    currencies = portfolio.currencies_from_state(state)
    datadict.update({currency: True for currency in currencies})

    mi = pd.MultiIndex.from_arrays([timestamp, hour, rebalance])
    mi.names = ['timestamp', 'hour', 'rebalance']
    df = pd.DataFrame(datadict, index=mi)

    # load params.csv if it exists
    if os.path.isfile(PARAMS):
        params_df = pd.read_csv(PARAMS, index_col=[0, 1, 2])
    else:
        params_df = pd.DataFrame([])

    params_df = params_df.append(df)
    params_df.to_csv(PARAMS)


def save_data(timestamp, hour, rebalance, data):
    data.to_csv(os.path.join(DATAFOLDER, '{0}_{1}_{2}.csv'.format(timestamp, hour, rebalance)))


def simulate(state, hour, markets, min_percentage_change, rebalance, base, value):
    times = []
    values = []
    markets.reset(seconds=3600 * hour)
    p = portfolio.Portfolio.from_state(markets.first_market(), state, base, value)
    for current_time, current_market in markets:
        times.append(current_time)
        if rebalance:
            p.rebalance(current_market, state, ['BTC'], min_percentage_change)

        values.append(p.total_value(current_market, ['USDT', 'BTC']))

    data = pd.DataFrame({'time': times, 'value': values})
    data['time'] = (data['time'] - data['time'].min()) / ONEDAY
    currencies = portfolio.currencies_from_state(state)
    return data


def compute_mean_percentage(data):
    """ Compute percentage of increase last 'result' value has when compared to 'baseline' at the same time
    
    :args: data (pd.DataFrame), with columns time and value
    """
    times = data.time.values
    values = data.value.values
    data.loc[:, 'mean %'] = (values - values[0]) * 100.0 / values[0] / (times - times[0])


def compute_rate(data):
    """ Compute interest rate yielded by data at each point in time
    
    :args: data (pd.DataFrame), with columns time and value
    """
    days = data['time'].values
    values = data['value'].values

    # rate ** days = last_value / first_value
    # days * log(base) = log(last_value / first_value)
    # base = 10**(log(last_value / first_value) / days)
    rate = 10 ** (np.log10(values/values[0]) / (days - days[0]))
    data.loc[:, 'rate'] = rate


def simulation_name(currencies, hours, min_percentage_change, suffix=None):
    """
    Return a string with all parameters used in the data
    
    :return: 
    """
    if currencies:
        name = "names_" + '_'.join(currencies) + \
               "_hours_" + "_".join([str(h) for h in hours]) + \
               "_%change_" + str(int(min_percentage_change * 100))
    if suffix:
        name += suffix

    return name


def read_data():
    params_df = pd.read_csv(PARAMS)

    #df[:, 'time'] = df['time'].apply(json.loads)
    #df[:, 'value'] = df['value'].apply(json.loads)


    print params_df


def final_analysis():
    df = read_data()
    #compute_mean_percentage(df)
    #compute_rate(df)

    plot_result()

    # For each data set (the only thing that changes is time). Sort hours by some type of return. Then compute
    # the mean and std of the ordering of a given hour. Is 1hour the best?
    add_sorting(df)
    evaluate_hour()

    """
    Compute something like 'rate' in between start and "n" days into the data and then from "n" days until the end
    Then scatter 1st result vs last. Can we trust past behaviour as a predictar of immediate future one?
    """
    print df.head()
    print 1


def plot_result():
    """
    For each data condition (hour, all currencies) make a 2D plot with axis like 'mean %'
    and 'rate'. We can make one plot per 'N' or one single plot using different markers.
    
    :return: None, generates FOLDER / layout_1.html
    """
    import holoviews as hv
    hv.extension('bokeh')
    renderer = hv.Store.renderers['bokeh'].instance(fig='html')

    df = pd.read_csv(PARAMS)

    # we only plot 'rebalance' data
    df = df[df['rebalance']==True]

    # Create a dictionary linking 'N' to the corresponding Scatter plot
    holoMap = hv.HoloMap({N:hv.Scatter(df[df['N']==N], kdims=['rate'], vdims=['mean %']) for N in
                          [4, 8, 16]}, kdims=['N'])
    holoview = holoMap.select(N={4, 8, 16}).layout()
    renderer.save(holoview, os.path.join(FOLDER, 'layout_1'), sytle=dict(Image={'cmap':'jet'}))


    N_hour = product((4, 8, 16), (1, 2, 6, 12, 24))
    holoMap = hv.HoloMap({(N, h):hv.Scatter(df[(df['N']==N) & (df['hour']==h)], kdims=['rate'],
                                            vdims=['mean %']) for N, h in N_hour}
                         , kdims=['N', 'hour'])
    holoview_4 = holoMap.select(N={4}).overlay()
    holoview_8 = holoMap.select(N={8}).overlay()
    holoview_16 = holoMap.select(N={16}).overlay()
    holoview = holoview_4 + holoview_8 + holoview_16
    renderer.save(holoview, os.path.join(FOLDER, 'layout_2'), sytle=dict(Image={'cmap':'jet'}))


def add_sorting(df):
    """
    For each data set (the only thing that changes is time). Sort hours by some type of return and add value
    to df
    
    :param df: 
    :return: 
    """
    # Simulation set starts always with a 'baseline' data. If we pull the indexes of these 'baselines' then
    # have a handle onto the start of each data set.
    # to identify a data we can just look at rows with 'rebalanced' set to False
    baselines = df[df['rebalance']==False]
    baselines_index = baselines.index.tolist()

    # add to 'baselines_index' the index corresponding to the next empty row so that extracting all data for a
    # data is just extracting between baselines_index[i] and baselines_index[i+1]
    baselines_index.append(df.shape[0])

    for start, end in zip(baselines_index[:-1], baselines_index[1:]):
        temp = df.iloc[start:end]['rate']
        # I multiply by -1 to have them in descending order and '0' be the best data
        df.loc[start:end - 1, 'sorting'] = temp.rank(ascending=False)

    return df


def evaluate_hour(N=None, currencies=None):
    """
    For each data set (the only thing that changes is time). Sort hours by some type of return. Then compute
    the mean and std of the ordering of a given hour. Is 1hour the best?
    
    :N: int, limit analysis to data with the given number of currencies
    :currencies: list of str, limit analysis to data that have those currencies. Len(currencies) can be less
                 than or equal to N, ie: if currencies = ['LTC'] then all data involving 'LTC' will be reported
                 
    :return: 
    """

    df = pd.read_csv(PARAMS)

    if N:
        assert type(N) == int
        df = df[df['N']==N]
        df.reset_index(inplace=True, drop=True)

    if currencies:
        assert type(currencies) == list
        df = df[df.apply(lambda x: np.alltrue([x[c] for c in currencies]), axis=1)]
        df.reset_index(inplace=True, drop=True)

    # to identify a data we can just look at rows with 'rebalanced' set to False

    baselines = df[df['rebalance']==False]
    baselines_index = baselines.index.tolist()

    # add to 'baselines_index' the index corresponding to the next empty row so that extracting all data for a
    # data is just extracting between baselines_index[i] and baselines_index[i+1]
    baselines_index.append(df.shape[0])

    output_df = pd.DataFrame([])

    for start, end in zip(baselines_index[:-1], baselines_index[1:]):
        temp = df.iloc[start:end]
        sim_name = csv_row_to_name(temp.iloc[0])
        sorted_order = np.argsort(temp['mean %'].values)
        reversed_order = len(sorted_order) - 1 - sorted_order
        hours = temp['hour'].values
        s = pd.Series(reversed_order, index=hours, name=sim_name)
        output_df = pd.concat([output_df, s], axis=1)

    mean = output_df.mean(axis=1)
    std = output_df.std(axis=1)
    hour_stats = pd.concat([mean, std], axis=1)
    hour_stats.columns = ['mean', 'std']

    hour_stats.to_csv(os.path.join(FOLDER, 'hour_stats.csv'))

    return hour_stats


def csv_row_to_name(row):
    """
    return a friendly name from a csv row
    """
    # keep only boolean values
    boolean_row = row.select(lambda i: type(row[i])==np.bool_ and row[i])
    if 'rebalance' in boolean_row.index:
        boolean_row.drop('rebalance', inplace=True)

    return '_'.join([str(i) for i in boolean_row.index])



'''
def fix_csv():
    """
    Load the csv and fix it, modify as needed
    :return: 
    """
    df = pd.read_csv(PARAMS)

    df.drop(['rate', 'percentage_to_baseline'], axis=1, inplace=True)

    rates = []
    means = []

    for index, row in df.iterrows():
        temp_df = pd.DataFrame({'time': json.loads(row.time), 'value': json.loads(row.value)})
        compute_rate(temp_df)
        compute_mean_percentage(temp_df)
        rates.append([temp_df['rate'].tolist()])
        means.append([temp_df['mean %'].tolist()])
        #df.loc[index, 'rate'] = [temp_df['rate'].tolist()]
        #df.loc[index, 'mean %'] = [temp_df['mean %'].tolist()]

    df.loc[:, 'rate'] = rates
    df.loc[:, 'percentage_to_baseline'] = means
    columns = df.columns.tolist()

    # last 5 columns are: rebalance, percentage_to_baseline, rate, time, value
    # and I want them to be:
    # mean %, rate, rebalance, time, value
    # so the index order is: -4, -3, -5, -2, -1
    index = columns.index('percentage_to_baseline')
    columns[index] = 'mean %'
    df.columns = columns
    print columns[-5:]
    columns = columns[:-4] + [columns[-4], columns[-3], columns[-5]] + columns[-2:]
    print columns[-5:]
    df = df[columns]
    df.to_csv('test.csv', index=False)
'''
