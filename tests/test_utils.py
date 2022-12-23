import pandas as pd
import pytest

from fx_library import utils


@pytest.mark.parametrize(
    'data, backtest, expect',
    [
        [
            [
                '2022-10-20 02:00:00', 
                100.0, 
                100.5, 
                99.5, 
                100.0, 
                90, 
                20, 
                90, 
                20],
            False,
            0],
        [
            [
                '2022-10-20 02:00:00', 
                100.0, 
                100.5, 
                99.5, 
                100.0, 
                90, 
                20, 
                -90, 
                -20],
            False,
            1],
        [
            [
                '2022-10-20 02:00:00', 
                100.0, 
                100.5, 
                99.5, 
                100.0, 
                -90, 
                -20, 
                90, 
                20],
            False,
            -1],
        [
            [
                '2022-10-20 02:00:00', 
                100.0, 
                100.5, 
                99.5, 
                100.0, 
                90, 
                20, 
                90, 
                20],
            True,
            0],
    ]
)
def test_direction_by_value_range(data, backtest, expect):
    df = pd.DataFrame(
        [data], 
        columns=[ 
            'time', 
            'open', 
            'high', 
            'low', 
            'close', 
            'rci_12', 
            'rci_12_shift_diff',
            'rci_24', 
            'rci_24_shift_diff'])
    
    columns = df.columns

    if backtest:
        result = utils.direction_by_value_range(
            data=df.iloc[0, :], 
            columns=columns, 
            ranges={
                'rci_12': {'ask': [80, 100], 'bid': [-80, -100]},
                'rci_12_shift_diff': {'ask': [0, 100], 'bid': [0, -100]},
                'rci_24': {'ask': [-100, -80], 'bid': [100, 80]},
                'rci_24_shift_diff': {'ask': [-100, 0], 'bid': [100, 0]}},
            backtest=backtest)
    else:
        result, _ = utils.direction_by_value_range(
            data=df.iloc[0, :], 
            columns=columns, 
            ranges={
                'rci_12': {'ask': [80, 100], 'bid': [-80, -100]},
                'rci_12_shift_diff': {'ask': [0, 100], 'bid': [0, -100]},
                'rci_24': {'ask': [-100, -80], 'bid': [100, 80]},
                'rci_24_shift_diff': {'ask': [-100, 0], 'bid': [100, 0]}},
            backtest=backtest)
    
    assert result == expect
