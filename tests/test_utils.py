import json

import numpy  as np
import pandas as pd
import pytest

from fx_library import utils


@pytest.mark.parametrize(
    'data, params, expect_result',
    [
        [
            np.array([
                np.datetime64('2000-01-01 00:00:00'),
                100.100,
                100.150,
                100.050,
                100.125,
                3.0,
                10.0,
                20.0,
                '2000-01-01 12:00:00',
                '2000-01-01 11:00:00',
                30.0,
                40.0,
                '2000-01-01 12:00:00']),
            {
                'ranges': {
                    'period_34_under': {'ask': [0, 100], 'bid': [0, -100]},
                    'period_34_shift_diff_under': {'ask': [0, 100], 'bid': [0, -100]},
                    'period_144_top': {'ask': [0, 100], 'bid': [0, -100]},
                    'period_144_shift_diff_top': {'ask': [0, 100], 'bid': [0, -100]}}},
            1],
        [
            np.array([
                np.datetime64('2000-01-01 00:00:00'),
                100.100,
                100.150,
                100.050,
                100.125,
                3.0,
                100.0,
                100.0,
                '2000-01-01 12:00:00',
                '2000-01-01 11:00:00',
                100.0,
                100.0,
                '2000-01-01 12:00:00']),
            {
                'ranges': {
                    'period_34_under': {'ask': [0, 100], 'bid': [0, -100]},
                    'period_34_shift_diff_under': {'ask': [0, 100], 'bid': [0, -100]},
                    'period_144_top': {'ask': [0, 100], 'bid': [0, -100]},
                    'period_144_shift_diff_top': {'ask': [0, 100], 'bid': [0, -100]}}},
            1],
        [
            np.array([
                np.datetime64('2000-01-01 00:00:00'),
                100.100,
                100.150,
                100.050,
                100.125,
                3.0,
                0,
                0,
                '2000-01-01 12:00:00',
                '2000-01-01 11:00:00',
                0,
                0,
                '2000-01-01 12:00:00']),
            {
                'ranges': {
                    'period_34_under': {'ask': [0, 100], 'bid': [0, -100]},
                    'period_34_shift_diff_under': {'ask': [0, 100], 'bid': [0, -100]},
                    'period_144_top': {'ask': [0, 100], 'bid': [0, -100]},
                    'period_144_shift_diff_top': {'ask': [0, 100], 'bid': [0, -100]}}},
            0],
        [
            np.array([
                np.datetime64('2000-01-01 00:00:00'),
                100.100,
                100.150,
                100.050,
                100.125,
                3.0,
                10,
                20,
                '2000-01-01 12:00:00',
                '2000-01-01 11:00:00',
                30,
                -40,
                '2000-01-01 12:00:00']),
            {
                'ranges': {
                    'period_34_under': {'ask': [0, 100], 'bid': [0, -100]},
                    'period_34_shift_diff_under': {'ask': [0, 100], 'bid': [0, -100]},
                    'period_144_top': {'ask': [0, 100], 'bid': [0, -100]},
                    'period_144_shift_diff_top': {'ask': [0, 100], 'bid': [0, -100]}}},
            0],
        [
            np.array([
                np.datetime64('2000-01-01 00:00:00'),
                100.100,
                100.150,
                100.050,
                100.125,
                3.0,
                10.0,
                20.0,
                '2000-01-01 12:00:00',
                '2000-01-01 11:00:00',
                30.0,
                40.0,
                '2000-01-01 12:00:00']),
            {
                'ranges': {
                    'period_34_under': {'ask': [-100, 0], 'bid': [100, 0]},
                    'period_34_shift_diff_under': {'ask': [-100, 0], 'bid': [100, 0]},
                    'period_144_top': {'ask': [-100, 0], 'bid': [100, 0]},
                    'period_144_shift_diff_top': {'ask': [-100, 0], 'bid': [100, 0]}}},
            -1]])
def test_direction_by_value_range(data, params, expect_result):
    df = pd.read_csv('./tests/data.csv')
    columns = df.columns
    
    result, _ = utils.direction_by_value_range(data, columns, **params)

    assert result == expect_result


def test_create_backtest_parameters_from_json():
    with open('./tests/backtests.json') as f:
        settings_json = json.load(f)

    for symbol in settings_json['symbols']:
        parameters = utils.create_backtest_parameters_from_json(
            symbol, settings_json, utils.direction_by_value_range)
