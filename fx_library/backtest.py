"""バックテストのモジュール
"""


from typing import Dict

import pandas as pd
from pandas import DataFrame, Series


class Backtest:
    """バックテストのクラス
    """
    def __init__(
        self, 
        df: DataFrame,
        trade_start_hour: int,
        trade_end_hour: int,
        time_column: str, 
        open_column: str,
        close_column: str, 
        high_column: str, 
        low_column: str, 
        spread_column: str, 
        order_count: int, 
        profit: int, 
        loss: int,
        trail_stop: bool,
        spread_threshold: int,
        pip: float) -> None:
        """初期化

        Args:
            df (DataFrame): ローソク足データ
            trade_start_hour (int): トレード開始時間,
            trade_end_hour (int): トレード終了時間,
            time_column (str): 日時の列名
            open_column (str): 始値の列名
            close_column (str): 終値の列名
            high_column (str): 高値の列名
            low_column (str): 安値の列名
            spread_column (str): スプレッドの列名
            order_count (int): 注文数
            profit (int): 利益
            loss (int): 損失
            trail_stop (bool): トレーリングストップ
            spread_threshold (int): スプレッドの閾値
            pip (float): pip単位

        Examples:
            >>> back = Backtest(
                    df=df, 
                    trade_start_hour=9,
                    trade_end_hour=16,
                    time_column='time', 
                    open_column='open', 
                    close_column='close', 
                    high_column='high', 
                    low_column='low', 
                    spread_column='spread', 
                    order_count=1, 
                    profit=10, 
                    loss=10, 
                    trail_stop=True, 
                    spread_threshold=10,
                    pip=0.01)
        """
        self.df = df
        self.trade_start_hour = trade_start_hour
        self.trade_end_hour = trade_end_hour
        self.time_column = time_column
        self.open_column = open_column
        self.close_column = close_column
        self.high_column = high_column
        self.low_column = low_column
        self.spread_column = spread_column
        self.order_count = order_count
        self.profit = profit
        self.loss = loss
        self.trail_stop = trail_stop
        self.spread_threshold = spread_threshold
        self.pip = pip
        self.orders = {'ask': [], 'bid': []}
        self.settlements = []
        self.result_df = None

        self.time_index = df.columns.get_loc(self.time_column)
        self.open_index = df.columns.get_loc(self.open_column)
        self.close_index = df.columns.get_loc(self.close_column)
        self.high_index = df.columns.get_loc(self.high_column)
        self.low_index = df.columns.get_loc(self.low_column)
        self.spread_index = df.columns.get_loc(self.spread_column)

    def run(self, func, reverse_order: bool=False, **kwargs) -> None:
        """バックテストの実行
        
        Args:
            func (function): 売買方向を決定する関数
            reverse_order (bool): Trueの場合は発注時に逆売買を行う
            **kwargs (dict): funcのキーワード引数
        
        Examples:
            >>> back.run(
                    func=direction_by_value_range, 
                    reverse_order=reverse_order, 
                    ranges={
                        'rci_12': {'ask': [80, 100], 'bid': [-80, -100]},
                        'rci_12_shift_diff': {
                            'ask': [0, 100], 'bid': [0, -100]}},
                    backtest=True)
        """
        columns = self.df.columns

        for data in self.df.values:
            if data[self.time_index].hour >= self.trade_end_hour:
                self.settlement(data=data, all=True)
            else:
                self.settlement(data=data)

            if  self.trade_start_hour <= data[self.time_index].hour < self.trade_end_hour:
                if data[self.spread_index] <= self.spread_threshold:
                    if kwargs:
                        direction = func(data, columns, **kwargs)
                    else:
                        direction = func(data, columns)

                    if direction != 0:
                        self.order(data, direction)

                        if reverse_order:
                            self.order(data, direction * -1)

        if self.result_df is None:
            self.result_df = pd.DataFrame.from_dict(self.settlements)
        else:
            self.result_df = self.join_dfs(
                [self.result_df, pd.DataFrame.from_dict(self.settlements)])
        
        self.result_df = self.result_df.sort_values('order_time')

    def order(self, data: Series, direction: int) -> None:
        """発注

        Args:
            data (Series): ローソク足データ
            direction (int): 売買方向
        """
        close_price = data[self.close_index]
        spread = data[self.spread_index] * self.pip * 0.1

        order_price = close_price + spread if direction == 1 else close_price
        
        profit_pip = self.profit * self.pip
        loss_pip = self.loss * self.pip

        result = {
            'order_time': data[self.time_index],
            'order_price': order_price,
            'direction': direction,
            'profit_price': None,
            'loss_price': None,
            'settlement_time': None,
            'settlement_price': None,
            'result': None}

        if direction == 1:
            if len(self.orders['ask']) < self.order_count:
                result['profit_price'] = order_price + profit_pip
                result['loss_price'] = order_price - loss_pip

                self.orders['ask'].append(result)
        elif direction == -1:
            if len(self.orders['bid']) < self.order_count:
                result['profit_price'] = order_price - profit_pip
                result['loss_price'] = order_price + loss_pip

                self.orders['bid'].append(result)

    def settlement(self, data: Series, all: bool=False) -> None:
        """決済

        Args:
            data (Series): ローソク足データ
        """
        spread = data[self.spread_index] * self.pip * 0.1

        open_price = data[self.open_index]
        high_price = data[self.high_index]
        low_price = data[self.low_index]

        for key in self.orders:
            for i in range(len(self.orders[key]) - 1, -1, -1):
                result = None 

                order_price = self.orders[key][i]['order_price']
                profit_price = self.orders[key][i]['profit_price']
                loss_price = self.orders[key][i]['loss_price']
                
                if key == 'ask':
                    if all:
                        settlement_price = open_price
                        result = round(
                            (settlement_price - order_price) / self.pip, 2)
                    else:
                        if loss_price >= low_price:
                            settlement_price = low_price 
                            result = round(
                                (loss_price - order_price) / self.pip, 2)
                            
                            if abs(result) >= self.loss:
                                result = -1 * self.loss
                        else:
                            if profit_price < high_price:
                                settlement_price = high_price
                                result = 1 * self.profit
                    
                    if result is None:
                        loss_pip = self.loss * self.pip

                        if self.trail_stop:
                            if loss_price < high_price - loss_pip:
                                loss_price = high_price - loss_pip
                                self.orders[key][i]['loss_price'] = loss_price
                elif key == 'bid':
                    order_price = order_price
                    high_price = high_price + spread
                    low_price = low_price + spread

                    if all:
                        settlement_price = open_price + spread
                        result = round(
                            (order_price - settlement_price) / self.pip, 2)
                    else:
                        if loss_price <= high_price:
                            settlement_price = high_price
                            result = round(
                                (order_price - loss_price) / self.pip, 2)

                            if abs(result) >= self.loss:
                                result = -1 * self.loss
                        else:
                            if profit_price > low_price:
                                settlement_price = low_price
                                result = 1 * self.profit
                    
                    if result is None:
                        loss_pip = self.loss * self.pip                        

                        if self.trail_stop:
                            if loss_price > low_price + loss_pip:
                                loss_price = low_price + loss_pip
                                self.orders[key][i]['loss_price'] = loss_price
                
                if result is not None:
                    self.orders[
                        key][i]['settlement_time'] = data[self.time_index]
                    self.orders[key][i]['settlement_price'] = settlement_price
                    self.orders[key][i]['result'] = result

                    self.settlements.append(self.orders[key].pop(i))
        
    @classmethod
    def performance(
        cls, backtest_df: DataFrame, profit: int, loss: int) -> Dict:
        """実績
        
        Args:
            backtest_df (DataFrame): バックテスト結果のデーフレーム
            profit (int): 利益
            loss (int): 損失
        
        Returns:
            Dict: 実績

        Examples:
            >>> Backtest.performance(
                    backtest_df=back.result_df, profit=10, loss=10)
        """
        profit_count = backtest_df[
            backtest_df['result'] > 0]['result'].count()
        loss_count = backtest_df[
            backtest_df['result'] < 0]['result'].count()

        total_count = profit_count + loss_count

        profit_rate = round((profit_count / total_count) * 100, 0)

        result = backtest_df['result'].sum()
        
        detail_data = cls.detail_performance(cls, df=backtest_df)

        return {
            'total_count': total_count,
            'profit_count': profit_count,
            'loss_count': loss_count,
            'profit_rate': profit_rate,
            'result': result,
            'profit': profit,
            'loss': loss,
            'detail': detail_data}
    
    def detail_performance(self, df: DataFrame):
        """実績の詳細

        Args:
            df (DataFrame): バックテスト結果のデーフレーム
            
        Returns:
            Dict: 実績の詳細

        Examples:
            >>> detail_data = self.detail_performance(self, df=backtest_df)
        """
        df['order_time'] = pd.to_datetime(df['order_time'])

        df['year'] = df['order_time'].dt.year
        df['month'] = df['order_time'].dt.month
        df['week'] = df['order_time'].dt.isocalendar().week
        df['day'] = df['order_time'].dt.day

        detail_data = {
            'year': self.calculation_detail(df=df, group_list=['year']),
            'month': self.calculation_detail(
                df=df, group_list=['year', 'month']),
            'week': self.calculation_detail(df=df, group_list=['year', 'week']),
            'day': self.calculation_detail(
                df=df, group_list=['year', 'month', 'day'])}

        return detail_data
    
    @staticmethod
    def calculation_detail(df: DataFrame, group_list: list):
        """実績の詳細の計算

        Args:
            df (DataFrame): バックテスト結果のデーフレーム
            group_list (list): groupbyの引数
        
        Returns:
            Dict: 実績の詳細

        Examples:
            >>> self.calculation_detail(df=df, group_list=['year', 'month'])
        """
        group = df.groupby(group_list)
        profit_group = df.loc[df['result'] > 0].groupby(group_list)
        loss_group = df.loc[df['result'] < 0].groupby(group_list)

        sum_df = group.sum('result')['result']
        profit_count_df = profit_group.count()['result']
        loss_count_df = loss_group.count()['result']

        count_df = pd.merge(
            profit_count_df, 
            loss_count_df, 
            how='outer', 
            left_index=True, 
            right_index=True)

        count_df = count_df.rename(
            columns={'result_x': 'profit_count', 'result_y': 'loss_count'})
        count_df = count_df.fillna({'profit_count': 0, 'loss_count': 0})
        count_df['total_count'] = 0
        count_df['total_count'] = (
            count_df['profit_count'] + count_df['loss_count'])
        count_df['profit_rate'] = 0
        count_df['profit_rate'] = round(
            (count_df['profit_count'] / count_df['total_count']) * 100, 0)

        merge_df = pd.merge(
            sum_df, count_df, how='outer', left_index=True, right_index=True)

        merge_df = merge_df.reset_index()

        return merge_df.to_dict(orient='records')
