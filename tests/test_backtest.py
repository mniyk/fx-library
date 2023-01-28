import pandas as pd
import pytest

from fx_library.backtest import Backtest
from fx_library.utils import direction_by_value_range


class TestTechnicalIndicators:
    time_column='time' 
    close_column='close' 
    high_column='high' 
    low_column='low' 
    order_count=1 
    profit=100 
    loss=100 
    pip=0.01

    def setup_method(self):
        data = [
            ['2022-10-20 01:00:00', 100.0, 100.5, 99.5, 100.0, 20, 20],
            ['2022-10-20 02:00:00', 100.0, 100.5, 99.5, 100.0, 90, 20],
            ['2022-10-20 03:00:00', 100.0, 100.5, 99.5, 100.0, 90, 20],
            ['2022-10-20 04:00:00', 100.0, 100.5, 99.5, 100.0, -90, -20],
            ['2022-10-20 05:00:00', 100.0, 100.5, 99.5, 100.0, -20, -20],
            ['2022-10-20 06:00:00', 100.0, 100.5, 99.5, 100.0, -90, -20],
            ['2022-10-20 07:00:00', 100.0, 100.5, 98.5, 100.0, 20, 20],
            ['2022-10-20 08:00:00', 100.0, 102.5, 99.5, 100.0, 20, 20]]

        self.df = pd.DataFrame(
            data, 
            columns=[
                'time', 
                'open', 
                'high', 
                'low', 
                'close', 
                'rci_12', 
                'rci_12_shift_diff'])

        self.back = Backtest(
            df=self.df.copy(),
            time_column=self.time_column,
            close_column=self.close_column,
            high_column=self.high_column,
            low_column=self.low_column,
            order_count=self.order_count,
            profit=self.profit,
            loss=self.loss,
            pip=self.pip)

    @pytest.mark.parametrize(
        'reverse_order, expect',
        [
            [
                False, 
                [
                    {
                        'order_time': '2022-10-20 02:00:00', 
                        'order_price': 100.0, 
                        'direction': 1, 
                        'profit_price': 101.0, 
                        'loss_price': 99.0, 
                        'settlement_time': '2022-10-20 07:00:00', 
                        'settlement_price': 98.5, 
                        'result': -1}, 
                    {
                        'order_time': '2022-10-20 04:00:00', 
                        'order_price': 100.0, 
                        'direction': -1, 
                        'profit_price': 99.0, 
                        'loss_price': 101.0, 
                        'settlement_time': '2022-10-20 07:00:00', 
                        'settlement_price': 98.5, 
                        'result': 1}]],
            [
                True, 
                [
                    {
                        'order_time': '2022-10-20 02:00:00', 
                        'order_price': 100.0, 
                        'direction': 1, 
                        'profit_price': 101.0, 
                        'loss_price': 99.0, 
                        'settlement_time': '2022-10-20 07:00:00', 
                        'settlement_price': 98.5, 
                        'result': -1}, 
                    {
                        'order_time': '2022-10-20 02:00:00', 
                        'order_price': 100.0, 
                        'direction': -1, 
                        'profit_price': 99.0, 
                        'loss_price': 101.0, 
                        'settlement_time': '2022-10-20 07:00:00', 
                        'settlement_price': 98.5, 
                        'result': 1}]]])
    def test_run(self, reverse_order, expect):
        self.back.run(
            func=direction_by_value_range, 
            reverse_order=reverse_order, 
            ranges={
                'rci_12': {'ask': [80, 100], 'bid': [-80, -100]},
                'rci_12_shift_diff': {'ask': [0, 100], 'bid': [0, -100]}},
            backtest=True)
        
        assert self.back.settlements == expect

    @pytest.mark.parametrize(
        'direction, expect', 
        [
            [
                1, 
                {
                    'ask': [{
                        'order_time': '2022-10-20 01:00:00', 
                        'order_price': 100.0, 
                        'direction': 1, 
                        'profit_price': 101.0, 
                        'loss_price': 99.0, 
                        'settlement_time': None, 
                        'settlement_price': None, 
                        'result': None}], 
                    'bid': []}],
            [
                -1, 
                {
                    'ask': [],
                    'bid': [{
                        'order_time': '2022-10-20 01:00:00', 
                        'order_price': 100.0, 
                        'direction': -1, 
                        'profit_price': 99.0, 
                        'loss_price': 101.0, 
                        'settlement_time': None, 
                        'settlement_price': None, 
                        'result': None}]}]])
    def test_order(self, direction, expect):
        self.back.order(data=self.df.loc[0], direction=direction)

        assert self.back.orders == expect

    @pytest.mark.parametrize(
        'direction, data, expect', 
        [
            [
                1,
                ['2022-10-20 02:00:00', 100.0, 102.5, 99.5, 100.0, 20, 20],
                [{
                    'order_time': '2022-10-20 01:00:00', 
                    'order_price': 100.0, 
                    'direction': 1, 
                    'profit_price': 101.0, 
                    'loss_price': 99.0, 
                    'settlement_time': '2022-10-20 02:00:00', 
                    'settlement_price': 102.5, 
                    'result': 1}]],
            [
                1,
                ['2022-10-20 02:00:00', 100.0, 102.5, 98.5, 100.0, 20, 20],
                [{
                    'order_time': '2022-10-20 01:00:00', 
                    'order_price': 100.0, 
                    'direction': 1, 
                    'profit_price': 101.0, 
                    'loss_price': 99.0, 
                    'settlement_time': '2022-10-20 02:00:00', 
                    'settlement_price': 98.5, 
                    'result': -1}]],
            [
                1,
                ['2022-10-20 02:00:00', 100.0, 100.5, 99.5, 100.0, 20, 20],
                []],
            [
                -1,
                ['2022-10-20 02:00:00', 100.0, 100.5, 98.5, 100.0, 20, 20],
                [{
                    'order_time': '2022-10-20 01:00:00', 
                    'order_price': 100.0, 
                    'direction': -1, 
                    'profit_price': 99.0, 
                    'loss_price': 101.0, 
                    'settlement_time': '2022-10-20 02:00:00', 
                    'settlement_price': 98.5, 
                    'result': 1}]],
            [
                -1,
                ['2022-10-20 02:00:00', 100.0, 102.5, 98.5, 100.0, 20, 20],
                [{
                    'order_time': '2022-10-20 01:00:00', 
                    'order_price': 100.0, 
                    'direction': -1, 
                    'profit_price': 99.0, 
                    'loss_price': 101.0, 
                    'settlement_time': '2022-10-20 02:00:00', 
                    'settlement_price': 102.5, 
                    'result': -1}]],
            [
                -1,
                ['2022-10-20 02:00:00', 100.0, 100.5, 99.5, 100.0, 20, 20],
                []]])
    def test_settlement(self, direction, data, expect):
        self.back.order(data=self.df.loc[0], direction=direction)

        ser = pd.Series(data)
        
        self.back.settlement(data=ser)

        assert self.back.settlements == expect

    def test_performance(self):
        self.back.run(
            func=direction_by_value_range, 
            reverse_order=True, 
            ranges={
                'rci_12': {'ask': [80, 100], 'bid': [-80, -100]},
                'rci_12_shift_diff': {'ask': [0, 100], 'bid': [0, -100]}},
            backtest=True)
        
        performance_result = Backtest.performance(
            self.back.result_df, profit=self.profit, loss=self.loss)
        
        expect = {
            'total_count': 2, 
            'profit_count': 1, 
            'loss_count': 1, 
            'profit_rate': 50.0, 
            'profit_and_loss': 0, 
            'profit': 100, 
            'loss': 100,
            'detail': {
                'year': [{
                    'year': 2022, 
                    'profit_and_loss': 0, 
                    'profit_count': 1, 
                    'loss_count': 1, 
                    'total_count': 2, 
                    'profit_rate': 50.0}], 
                'month': [{
                    'year': 2022, 
                    'month': 10, 
                    'profit_and_loss': 0, 
                    'profit_count': 1, 
                    'loss_count': 1, 
                    'total_count': 2, 
                    'profit_rate': 50.0}], 
                'week': [{
                    'year': 2022, 
                    'week': 42, 
                    'profit_and_loss': 0, 
                    'profit_count': 1, 
                    'loss_count': 1, 
                    'total_count': 2, 
                    'profit_rate': 50.0}]}}

        assert performance_result == expect
