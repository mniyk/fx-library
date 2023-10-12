import numpy  as np
import pandas as pd
import pytest

from fx_library import backtest, utils


class TestBacktest:
    def setup_method(self, method):
        self.hour_period   = backtest.HourPeriod(start=0, end=24)
        self.candle_column = backtest.CandleColumn(
            time_column  ='time_under',
            open_column  ='open_under',
            high_column  ='high_under',
            low_column   ='low_under',
            close_column ='close_under',
            spread_column='spread_under')
        self.backtest_parameter = backtest.BacktestParameter(
            hour_period     =self.hour_period,
            candle_column   =self.candle_column,
            position_count  =1,
            profit          =100,
            loss            =100,
            trail_stop      =True,
            spread_threshold=50,
            pip             =0.01,
            reverse_order   =False)
        self.df               = pd.read_csv('./tests/data.csv')
        self.df               = self.df.dropna()
        self.df['time_under'] = pd.to_datetime(self.df['time_under'])
        self.back             = backtest.Backtest(self.df, self.backtest_parameter)

    def test_run(self):
        params = {
            'ranges': {
                'period_34_under'           : {'ask': [0, 100], 'bid': [0, -100]},
                'period_34_shift_diff_under': {'ask': [0, 100], 'bid': [0, -100]},
                'period_144_top'            : {'ask': [0, 100], 'bid': [0, -100]},
                'period_144_shift_diff_top' : {'ask': [0, 100], 'bid': [0, -100]}}}

        self.back.run(utils.direction_by_value_range, **params)

        df = pd.DataFrame(self.back.settlements)

        df = pd.merge(self.df, df, left_on='time_under', right_on='order_time', how='outer')
        df = df.sort_values('time_under')

        df.to_csv('./tests/result.csv')
    
    @pytest.mark.parametrize(
        'direction, expect_order_data', 
        [
            [
                1,
                backtest.Order(
                    order_time      =np.datetime64('2000-01-01T00:00:00'),
                    order_price     =100.128,
                    direction       =1,
                    profit_price    =101.128,
                    loss_price      =99.128,
                    settlement_time =None,
                    settlement_price=0,
                    result          =0)], 
            [
                -1,
                backtest.Order(
                    order_time      =np.datetime64('2000-01-01T00:00:00'),
                    order_price     =100.125,
                    direction       =-1,
                    profit_price    =99.125,
                    loss_price      =101.125,
                    settlement_time =None,
                    settlement_price=0,
                    result          =0)]])
    def test_order(self, direction, expect_order_data):
        data = np.array([
            np.datetime64('2000-01-01 00:00:00'),
            100.100,
            100.150,
            100.050,
            100.125,
            3.0,
            20.0,
            20.0,
            '2000-01-01 12:00:00',
            '2000-01-01 11:00:00',
            20.0,
            20.0,
            '2000-01-01 12:00:00'])
        
        order_data = self.back.order(data, direction)
    
        assert order_data == expect_order_data 
    
    @pytest.mark.parametrize('all, expect', [[True, 4], [False, 0]])
    def test_settlement(self, all, expect):
        data = np.array([
            np.datetime64('2000-01-01 00:00:00'),
            100.100,
            100.150,
            100.050,
            100.125,
            3.0,
            20.0,
            20.0,
            '2000-01-01 12:00:00',
            '2000-01-01 11:00:00',
            20.0,
            20.0,
            '2000-01-01 12:00:00'])
        
        self.back.orders['ask'].append(
            backtest.Order(
                order_time      =np.datetime64('2000-01-01T00:00:00'),
                order_price     =100.128,
                direction       =1,
                profit_price    =101.128,
                loss_price      =99.128,
                settlement_time =None,
                settlement_price=0,
                result          =0))
        self.back.orders['ask'].append(
            backtest.Order(
                order_time      =np.datetime64('2000-01-01T01:00:00'),
                order_price     =100.128,
                direction       =1,
                profit_price    =101.128,
                loss_price      =99.128,
                settlement_time =None,
                settlement_price=0,
                result          =0))
        self.back.orders['bid'].append(
            backtest.Order(
                    order_time      =np.datetime64('2000-01-01T00:00:00'),
                    order_price     =100.125,
                    direction       =-1,
                    profit_price    =99.125,
                    loss_price      =101.125,
                    settlement_time =None,
                    settlement_price=0,
                    result          =0))
        self.back.orders['bid'].append(
            backtest.Order(
                    order_time      =np.datetime64('2000-01-01T01:00:00'),
                    order_price     =100.125,
                    direction       =-1,
                    profit_price    =99.125,
                    loss_price      =101.125,
                    settlement_time =None,
                    settlement_price=0,
                    result          =0))
        
        self.back.settlement(data, all)

        assert len(self.back.settlements) == expect

    @pytest.mark.parametrize(
        'settlement_data, all, expect_result, expect_loss_price, expect_settlement_price', 
        [
            [
                backtest.Settlement(
                    open_price=100.000, high_price=100.150, low_price=100.050, spread=3.0),
                True, 
                -12.8,
                99.128, 
                100.000],
            [
                backtest.Settlement(
                    open_price=100.150, high_price=100.150, low_price=100.050, spread=3.0),
                True, 
                2.2,
                99.128, 
                100.150],
            [
                backtest.Settlement(
                    open_price=100.000, high_price=100.150, low_price=100.050, spread=3.0),
                False, 
                None,
                99.150, 
                0],
            [
                backtest.Settlement(
                    open_price=100.000, high_price=101.150, low_price=99.050, spread=3.0),
                False, 
                -100,
                99.128, 
                99.050],
            [
                backtest.Settlement(
                    open_price=100.000, high_price=101.150, low_price=100.050, spread=3.0),
                False, 
                100,
                99.128, 
                101.150]])
    def test_settlement_ask(
        self, settlement_data, all, expect_result, expect_loss_price, expect_settlement_price):
        order_data = backtest.Order(
            order_time      =np.datetime64('2000-01-01T00:00:00'),
            order_price     =100.128,
            direction       =1,
            profit_price    =101.128,
            loss_price      =99.128,
            settlement_time =None,
            settlement_price=0,
            result          =0)

        result = self.back.settlement_ask(settlement_data, order_data, all)

        assert result                      == expect_result 
        assert order_data.loss_price       == expect_loss_price
        assert order_data.settlement_price == expect_settlement_price

    @pytest.mark.parametrize(
        'settlement_data, all, expect_result, expect_loss_price, expect_settlement_price', 
        [
            [
                backtest.Settlement(
                    open_price=100.000, high_price=100.150, low_price=100.050, spread=3.0),
                True, 
                12.2,
                101.125, 
                100.003],
            [
                backtest.Settlement(
                    open_price=100.150, high_price=100.150, low_price=100.050, spread=3.0),
                True, 
                -2.8,
                101.125, 
                100.153],
            [
                backtest.Settlement(
                    open_price=100.000, high_price=100.150, low_price=100.050, spread=3.0),
                False, 
                None,
                101.050, 
                0],
            [
                backtest.Settlement(
                    open_price=100.000, high_price=101.150, low_price=100.050, spread=3.0),
                False, 
                -100,
                101.125, 
                101.153],
            [
                backtest.Settlement(
                    open_price=100.000, high_price=100.150, low_price=99.050, spread=3.0),
                False, 
                100,
                101.125, 
                99.053]])
    def test_settlement_bid(
        self, settlement_data, all, expect_result, expect_loss_price, expect_settlement_price):
        order_data = backtest.Order(
            order_time      =np.datetime64('2000-01-01T00:00:00'),
            order_price     =100.125,
            direction       =-1,
            profit_price    =99.125,
            loss_price      =101.125,
            settlement_time =None,
            settlement_price=0,
            result          =0)

        result = self.back.settlement_bid(settlement_data, order_data, all)

        assert result                      == expect_result 
        assert order_data.loss_price       == expect_loss_price
        assert order_data.settlement_price == expect_settlement_price


class TestPerformance:
    def setup_method(self, method):
        self.hour_period   = backtest.HourPeriod(start=0, end=24)
        self.candle_column = backtest.CandleColumn(
            time_column  ='time_under',
            open_column  ='open_under',
            high_column  ='high_under',
            low_column   ='low_under',
            close_column ='close_under',
            spread_column='spread_under')
        self.backtest_parameter = backtest.BacktestParameter(
            hour_period     =self.hour_period,
            candle_column   =self.candle_column,
            position_count  =1,
            profit          =100,
            loss            =100,
            trail_stop      =True,
            spread_threshold=50,
            pip             =0.01,
            reverse_order   =False)
        self.df          = pd.read_csv('./tests/result.csv')
        self.performance = backtest.Performance(self.df, self.backtest_parameter)
    
    def test_performance(self):
        result = self.performance.performance()
