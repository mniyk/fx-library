"""ユーティリティ関数のモジュール
"""


import itertools

import numpy as np

from .backtest import Direction, Parameter
from .mt5      import PIPS


def direction_by_value_range(data, columns, **kwargs):
    """売買方向を値の範囲で決定
    
    **kwargsには、以下のような辞書を設定
    {
        'ranges': {
            'rci_12': {'ask': [80, 100], 'bid': [-80, -100]},
            'rci_12_shift_diff': {'ask': [0, 100], 'bid': [0, -100]}},
        'backtest': False}
    """
    log_direcctions = []
    directions = []

    for k, v in kwargs['ranges'].items():
        direction = 0
        index = columns.get_loc(k)
        val = data[index]

        if v['ask'][0] < val <= v['ask'][1]:
            direction = 1
                
        if v['bid'][0] > val >= v['bid'][1]:
            direction = -1

        directions.append(direction)
        
        log_direcctions.append({
            k: {'val': val, 'ranges': v, 'direction': direction}})

    result = Direction.ZERO 

    if abs(sum(directions)) == len(directions):
        if sum(directions) > 0:
            result = Direction.ASK
        elif sum(directions) < 0:
            result = Direction.BID
    
    return result, log_direcctions


def create_profit_loss(min_value, max_value, increase):
    """最小値と最大値から損益のペアを作成
    """
    profit_loss = range(min_value, max_value + increase, increase)
    profit_loss = itertools.product(profit_loss, repeat=2)
    profit_loss = list(profit_loss)

    return profit_loss


def create_direction_ranges(direction_range):
    """最小値と最大値、分割数から売買方向の範囲のリストを作成
    """
    direction_ranges = {}

    for col, param in direction_range['ranges'].items():
        if direction_range['range_calculation']:
            arange_list = np.round(
                    np.linspace(
                        param['range']['min'], 
                        param['range']['max'], 
                        param['range']['split']), 
                    param['range']['digits'])
            arange_list = list(arange_list)

            result_range = [
                {
                    'ask': [arange_list[i], arange_list[i + 1]],
                    'bid': [
                        arange_list[(i + 1) * -1], arange_list[(i + 2) * -1]]}
                for i in range(len(arange_list) - 1)]
        else:
            result_range = [param['value']]

        direction_ranges.setdefault(col, result_range)

    if len(direction_ranges) == 1:
        direction_ranges = one_direction_ranges(
            direction_ranges=direction_ranges)
    elif len(direction_ranges) == 2:
        direction_ranges = two_direction_ranges(
            direction_ranges=direction_ranges)
    elif len(direction_ranges) == 3:
        direction_ranges = three_direction_ranges(
            direction_ranges=direction_ranges)
    elif len(direction_ranges) == 4:
        direction_ranges = four_direction_ranges(
            direction_ranges=direction_ranges)
    else:
        direction_ranges = []

    return direction_ranges


def one_direction_ranges(direction_ranges):
    result = []

    key_list = list(direction_ranges.keys())

    for one_ranges in direction_ranges[key_list[0]]:
        result.append({"ranges": {key_list[0]: one_ranges}})

    return result


def two_direction_ranges(direction_ranges):
    result = []

    key_list = list(direction_ranges.keys())

    for one_ranges in direction_ranges[key_list[0]]:
        for two_ranges in direction_ranges[key_list[1]]:
            result.append(
                {"ranges": {key_list[0]: one_ranges, key_list[1]: two_ranges}})

    return result


def three_direction_ranges(direction_ranges):
    result = []

    key_list = list(direction_ranges.keys())

    for one_ranges in direction_ranges[key_list[0]]:
        for two_ranges in direction_ranges[key_list[1]]:
            for three_ranges in direction_ranges[key_list[2]]:
                result.append(
                    {
                        "ranges": {
                            key_list[0]: one_ranges, 
                            key_list[1]: two_ranges, 
                            key_list[2]: three_ranges}})

    return result


def four_direction_ranges(direction_ranges):
    result = []

    key_list = list(direction_ranges.keys())

    for one_ranges in direction_ranges[key_list[0]]:
        for two_ranges in direction_ranges[key_list[1]]:
            for three_ranges in direction_ranges[key_list[2]]:
                for four_ranges in direction_ranges[key_list[3]]:
                    result.append(
                        {
                            "ranges": {
                                key_list[0]: one_ranges, 
                                key_list[1]: two_ranges,
                                key_list[2]: three_ranges,
                                key_list[3]: four_ranges}})

    return result


def create_backtest_parameters_from_json(
    symbol, direction_parameter, json_data, direction_function):
    parameters = []

    profit_loss = create_profit_loss(
        json_data['profit_loss']['min'], 
        json_data['profit_loss']['max'], 
        json_data['profit_loss']['increase'])

    direction_ranges = create_direction_ranges(direction_parameter)

    for direction_range in direction_ranges:
        for profit, loss in profit_loss:
            parameter = Parameter(
                symbol             =symbol,
                timeframes         =json_data['timeframes'],
                technical_indicator=json_data['technical_indicator'],
                direction_function =direction_function,
                direction_parameter=direction_range,
                start              =json_data['start'],
                end                =json_data['end'],
                position_count     =json_data['position_count'],
                profit             =profit,
                loss               =loss,
                trail_stop         =json_data['trail_stop'],
                spread_threshold   =json_data['spread_threshold'],
                pip                =PIPS[symbol],
                reverse_order      =json_data['reverse_order'],
                time_column        =json_data['columns']['time'],
                open_column        =json_data['columns']['open'],
                high_column        =json_data['columns']['high'],
                low_column         =json_data['columns']['low'],
                close_column       =json_data['columns']['close'],
                spread_column      =json_data['columns']['spread'],
                technical_column   =json_data['columns']['technical'])
            
            parameters.append(parameter)
    
    return parameters
