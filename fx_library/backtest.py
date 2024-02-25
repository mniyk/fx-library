"""バックテストのモジュール
"""


from dataclasses import dataclass, field
from datetime    import datetime
from typing      import Callable, Dict, List

from   numpy  import ndarray
import pandas as pd
from   pandas import DataFrame


@dataclass
class Parameter:
    """バックテストに関する設定
    Args:
        symbol             (str)     : 通過ペア
        timesframes        (List)    : 時間枠
        technical_indicator(str)     : テクニカル指標
        direction_function (Callable): 売買方向を決定する関数
        direction_range    (Dict)    : 売買方向を決定する関数に渡す引数
        start              (int)     : 開始時間
        end                (int)     : 終了時間
        position_count     (int)     : 最大ポジション数
        profit             (int)     : 利益
        loss               (int)     : 損失
        trail_stop         (bool)    : トレーリングストップ
        spread_threshold   (int)     : スプレッドの閾値
        pip                (float)   : pip単位
        reverse_order      (bool)    : Trueの場合は発注時に逆売買を行う
        time_column        (str)     : 日時の列名
        open_column        (str)     : 始値の列名
        high_column        (str)     : 高値の列名
        low_column         (str)     : 安値の列名
        close_column       (str)     : 終値の列名
        spread_column      (str)     : スプレッドの列名
        technical_column   (str)     : テクニカルインジケーターに使用した列名
    """
    symbol             : str      = ''
    timeframes         : List     = field(default_factory=[])
    technical_indicator: str      = ''
    direction_function : Callable = None
    direction_parameter: Dict     = None
    start              : int      = 0
    end                : int      = 24 
    position_count     : int      = 1
    profit             : int      = 0
    loss               : int      = 0
    trail_stop         : bool     = False
    spread_threshold   : int      = 3
    pip                : float    = 0.001
    reverse_order      : bool     = False
    time_column        : str      = 'time'
    open_column        : str      = 'open'
    high_column        : str      = 'high'
    low_column         : str      = 'low'
    close_column       : str      = 'close'
    spread_column      : str      = 'spread'
    technical_column   : str      = 'close'


@dataclass
class Order:
    """発注に関する情報
    Args:
        order_time      (datetime): 発注日時
        order_price     (float)   : 発注価格
        spread          (float)   : スプレッド
        direction       (int)     : 売買方向
        profit_price    (float)   : 利益価格
        loss_price      (float)   : 損失価格
        settlement_time (datetime): 決済日時
        settlement_price(float)   : 決済価格
        result          (int)     : 1であれば利益,-1であれば損失
    """
    order_time      : datetime = None
    order_price     : float    = 0
    spread          : float    = 0
    direction       : int      = 0
    profit_price    : float    = 0
    loss_price      : float    = 0
    settlement_time : datetime = None
    settlement_price: float    = 0
    result          : int      = 0


@dataclass
class Settlement:
    """決済に関する情報
    """
    open_price: float = 0
    high_price: float = 0
    low_price : float = 0
    spread    : float = 0


class Backtest:
    """バックテストのクラス
    """
    def __init__(self, df: DataFrame, parameter: Parameter) -> None:
        """初期化

        Args:
            df        (DataFrame): ローソク足データ
            parameter (Parameter): バックテストに関する設定
        """
        self.df        = df
        self.parameter = parameter

        self.orders      = {'ask': [], 'bid': []}
        self.settlements = []
        self.result_df   = None

        self.columns      = self.df.columns
        self.time_index   = self.columns.get_loc(self.parameter.time_column)
        self.open_index   = self.columns.get_loc(self.parameter.open_column)
        self.close_index  = self.columns.get_loc(self.parameter.close_column)
        self.high_index   = self.columns.get_loc(self.parameter.high_column)
        self.low_index    = self.columns.get_loc(self.parameter.low_column)
        self.spread_index = self.columns.get_loc(self.parameter.spread_column)

    def run(self) -> None:
        """バックテストの実行
        """
        start, end = self.parameter.start, self.parameter.end

        for data in self.df.values:
            data_hour = data[self.time_index].hour

            settlement_all = True if data_hour >= end else False
            self.settlement(data=data, all=settlement_all)

            if  start <= data_hour < end:
                if data[self.spread_index] > self.parameter.spread_threshold:
                    continue

                direction, _ = self.parameter.direction_function(
                    data, self.columns, **self.parameter.direction_parameter)

                if direction == 0:
                    continue

                self.order(data, direction)

                if self.parameter.reverse_order:
                    self.order(data, direction * -1)

    def order(self, data: ndarray, direction: int) -> None:
        """発注

        Args:
            data      (ndarray): ローソク足データ
            direction (int)    : 売買方向
        """
        ask_bid     = 'ask' if direction == 1 else 'bid'
        spread      = data[self.spread_index]
        close_price = data[self.close_index]
        order_price = close_price + spread if direction == 1 else close_price

        order_data = Order(
            order_time =data[self.time_index], 
            order_price=order_price, 
            spread     =spread,
            direction  =direction)

        if direction == 0:
            return

        if len(self.orders[ask_bid]) >= self.parameter.position_count:
            return

        profit_pip = self.parameter.profit * self.parameter.pip
        profit_pip = profit_pip if direction == 1 else profit_pip * -1 

        loss_pip   = self.parameter.loss * self.parameter.pip
        loss_pip   = loss_pip * -1 if direction == 1 else loss_pip
        
        order_data.profit_price = order_price + profit_pip
        order_data.loss_price   = order_price + loss_pip

        self.orders[ask_bid].append(order_data)

    def settlement(self, data: ndarray, all: bool=False) -> None:
        """決済

        Args:
            data (ndarray): ローソク足データ
            all  (bool)   : Trueであればすべて決済
        """
        settlement_data = Settlement(
            open_price=data[self.open_index],
            high_price=data[self.high_index],
            low_price =data[self.low_index],
            spread    =data[self.spread_index] * self.parameter.pip * 0.1)
        
        for key in self.orders:
            for i in range(len(self.orders[key]) - 1, -1, -1):
                result     = None
                order_data = self.orders[key][i]
                
                if key == 'ask':
                    result = self.settlement_ask(settlement_data, order_data, all)
                elif key == 'bid':
                    result = self.settlement_bid(settlement_data, order_data, all)
                
                if result is not None:
                    order_data.settlement_time  = data[self.time_index]
                    order_data.result           = result

                    self.settlements.append(self.orders[key].pop(i))
        
    def settlement_ask(self, settlement_data: Settlement, order_data: Order, all: bool) -> float:
        result = None

        if all:
            order_data.settlement_price = settlement_data.open_price

            result = round((order_data.settlement_price - order_data.order_price) / self.parameter.pip, 2)

            return result

        if order_data.loss_price >= settlement_data.low_price:
            order_data.settlement_price = settlement_data.low_price 

            result = round((order_data.loss_price - order_data.order_price) / self.parameter.pip, 2)
            result = self.parameter.loss * -1 if abs(result) >= self.parameter.loss else result

            return result

        if order_data.profit_price < settlement_data.high_price:
            order_data.settlement_price = settlement_data.high_price
            result                      = self.parameter.profit

            return result
                    
        if result is None and self.parameter.trail_stop:
            loss_pip   = self.parameter.loss * self.parameter.pip

            if order_data.loss_price < settlement_data.high_price - loss_pip:
                order_data.loss_price = settlement_data.high_price - loss_pip
        
        return result

    def settlement_bid(self, settlement_data: Settlement, order_data: Order, all: bool) -> float:
        result = None

        if all:
            order_data.settlement_price = settlement_data.open_price + settlement_data.spread

            result = round((order_data.order_price - order_data.settlement_price) / self.parameter.pip, 2)

            return result            

        if order_data.loss_price <= settlement_data.high_price + settlement_data.spread:
            order_data.settlement_price = settlement_data.high_price + settlement_data.spread

            result = round((order_data.order_price - order_data.loss_price) / self.parameter.pip, 2)
            result = self.parameter.loss * -1 if abs(result) >= self.parameter.loss else result

            return result

        if order_data.profit_price > settlement_data.low_price + settlement_data.spread:
            order_data.settlement_price = settlement_data.low_price + settlement_data.spread
            result                      = self.parameter.profit

            return result
        
        if result is None and self.parameter.trail_stop:
            loss_pip = self.parameter.loss * self.parameter.pip

            if order_data.loss_price > settlement_data.low_price + loss_pip:
                order_data.loss_price = settlement_data.low_price + loss_pip

        return result

class Performance():
    """バックテストの実績のクラス
    """
    def __init__(self, df: DataFrame, parameter: Parameter) -> None:
        """初期化

        Args:
            df        (DataFrame): バックテスト結果のデータフレーム
            parameter (Parameter): バックテストの設定値
        """
        self.df        = df
        self.parameter = parameter

        self.df['order_time'] = pd.to_datetime(self.df['order_time'])
        self.df['year']       = self.df['order_time'].dt.year
        self.df['month']      = self.df['order_time'].dt.month
        self.df['week']       = self.df['order_time'].dt.isocalendar().week
        self.df['day']        = self.df['order_time'].dt.day

    def performance(self) -> Dict:
        """実績

        Returns:
            Dict: 実績
        """
        profit_count = self.df[self.df['result'] >= 0]['result'].count()
        loss_count   = self.df[self.df['result'] < 0]['result'].count()
        total_count  = profit_count + loss_count
        profit_rate  = round((profit_count / total_count) * 100, 0)

        result = self.df['result'].sum()
        
        year  = self.detail(group_list=['year'])
        month = self.detail(group_list=['year', 'month'])
        week  = self.detail(group_list=['year', 'week'])
        day   = self.detail(group_list=['year', 'month', 'day'])

        detail_perfoemance = {'year': year, 'month': month, 'week': week, 'day': day}

        return {
            'total_count' : total_count,
            'profit_count': profit_count,
            'loss_count'  : loss_count,
            'profit_rate' : profit_rate,
            'result'      : result,
            'profit'      : self.parameter.profit,
            'loss'        : self.parameter.loss,
            'detail'      : detail_perfoemance}
    
    def detail(self, group_list) -> Dict:
        """実績の詳細

        Args:
            group_list (list): groupbyの引数
        
        Returns:
            Dict: 実績の詳細
        """
        group        = self.df.groupby(group_list)
        profit_group = self.df.loc[self.df['result'] >= 0].groupby(group_list)
        loss_group   = self.df.loc[self.df['result'] < 0].groupby(group_list)

        sum_df = group.sum('result')['result']
        profit = profit_group.count()['result']
        loss   = loss_group.count()['result']

        count_df = pd.merge(profit, loss, how='outer', left_index=True, right_index=True)
        count_df = count_df.rename(columns={'result_x': 'profit_count', 'result_y': 'loss_count'})
        count_df = count_df.fillna({'profit_count': 0, 'loss_count': 0})

        count_df['total_count'] = (count_df['profit_count'] + count_df['loss_count'])
        count_df['profit_rate'] = round((count_df['profit_count'] / count_df['total_count']) * 100, 0)

        merge_df = pd.merge(sum_df, count_df, how='outer', left_index=True, right_index=True)
        merge_df = merge_df.fillna({'profit_count': 0, 'loss_count': 0, 'total_count': 0, 'profit_rate': 0})
        merge_df = merge_df.reset_index()

        return merge_df.to_dict(orient='records')
