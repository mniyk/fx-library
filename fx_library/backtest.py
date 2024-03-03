"""バックテストのモジュール
"""


from dataclasses import dataclass, field
from datetime    import datetime
from enum        import Enum
from typing      import Callable

from   numpy  import ndarray
import pandas as pd
from   pandas import DataFrame


class Direction(Enum):
    """売買方向
    """
    ASK  = 1
    ZERO = 0
    BID  = -1


@dataclass
class Parameter:
    """バックテストに関する設定

    Args:
        symbol              (str)     : 通過ペア
        timesframes         (list)    : 時間枠
        technical_indicator (str)     : テクニカル指標
        direction_function  (Callable): 売買方向を決定する関数
        direction_range     (dict)    : 売買方向を決定する関数に渡す引数
        trade_start_hour    (int)     : トレードの開始時間
        trade_end_hour      (int)     : トレードの終了時間
        position_count      (int)     : 最大ポジション数
        profit              (int)     : 利益
        loss                (int)     : 損失
        trail_stop          (bool)    : トレーリングストップ
        spread_threshold    (int)     : スプレッドの閾値
        pip                 (float)   : pip単位
        reverse_order       (bool)    : Trueの場合は発注時に逆売買を行う
        time_column         (str)     : 日時の列名
        open_column         (str)     : 始値の列名
        high_column         (str)     : 高値の列名
        low_column          (str)     : 安値の列名
        close_column        (str)     : 終値の列名
        spread_column       (str)     : スプレッドの列名
        technical_column    (str)     : テクニカルインジケーターに使用した列名
    """
    symbol             : str      = ''
    timeframes         : list     = field(default_factory=list)
    technical_indicator: str      = ''
    direction_function : Callable = None
    direction_parameter: dict     = None
    trade_start_hour   : int      = 0
    trade_end_hour     : int      = 24
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
        order_time       (datetime): 発注日時
        order_price      (float)   : 発注価格
        spread           (float)   : スプレッド
        direction        (int)     : 売買方向
        profit_price     (float)   : 利益価格
        loss_price       (float)   : 損失価格
        settlement_time  (datetime): 決済日時
        settlement_price (float)   : 決済価格
        result           (int)     : 1であれば利益,-1であれば損失
    """
    order_time      : datetime = None
    order_price     : float    = 0
    spread          : float    = 0
    direction       : int      = 0
    profit_price    : float    = 0
    loss_price      : float    = 0
    settlement_time : datetime = None
    settlement_price: float    = None 
    result          : float    = None


@dataclass
class Settlement:
    """決済に関する情報

    Args:
        open_price (float): 始値 
        high_price (float): 高値
        low_price  (float): 安値
        spread     (float): スプレッド
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
        
        Returns:
            None
        """
        self.df        = df
        self.parameter = parameter

        self.orders      = {Direction.ASK: [], Direction.BID: []}
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

        Returns:
            None
        """
        trade_start_hour = self.parameter.trade_start_hour
        trade_end_hour   = self.parameter.trade_end_hour

        for data in self.df.values:
            data_hour = data[self.time_index].hour

            # トレードの終了日時以上であればすべて決済する
            self.__settlement(
                data=data, all=True if data_hour >= trade_end_hour else False)

            # スプレッドの閾値より大きければトレードを行わない
            if data[self.spread_index] > self.parameter.spread_threshold:
                continue

            # 開始日時から終了日時未満であればトレードを行う
            if  trade_start_hour <= data_hour < trade_end_hour:
                # 売買方向を決定
                direction, _ = self.parameter.direction_function(
                    data, self.columns, **self.parameter.direction_parameter)

                # 売買なしであれば発注しない
                if direction == Direction.ZERO:
                    continue

                # 発注
                self.__order(data, direction)

                # 逆方向への発注
                if self.parameter.reverse_order:
                    direction = (
                        Direction.BID 
                        if direction == Direction.ASK 
                        else Direction.ASK)
                    
                    self.__order(data, direction)
        
        # バックテスト結果のデータフレームを作成
        if len(self.settlements) != 0:
            self.result_df = pd.DataFrame(self.settlements)

    def __order(self, data: ndarray, direction: Direction) -> None:
        """発注

        Args:
            data      (ndarray): ローソク足データ
            direction (int)    : 売買方向
        
        Returns:
            None
        """
        # 既存の発注数が指定数以上であれば発注しない
        if len(self.orders[direction]) >= self.parameter.position_count:
            return

        # 買い注文の場合は、終値にスプレッドを足した価格を発注価格とする
        if direction == Direction.ASK:
            order_price = data[self.close_index] + data[self.spread_index]
        else:
            order_price = data[self.close_index]

        # 売りであれば、下げ方向が利益となる
        profit_pip   = self.parameter.profit * self.parameter.pip
        profit_pip   = (
            profit_pip if direction == Direction.ASK else profit_pip * -1)
        profit_price = order_price + profit_pip

        # 買いであれば、下げ方向が損失となる
        loss_pip   = self.parameter.loss * self.parameter.pip
        loss_pip   = loss_pip * -1 if direction == Direction.ASK else loss_pip 
        loss_price = order_price + loss_pip

        order = Order(
            order_time  =data[self.time_index], 
            order_price =order_price, 
            spread      =data[self.spread_index],
            direction   =direction,
            profit_price=profit_price,
            loss_price  =loss_price)

        # 発注リストに追加する
        self.orders[direction].append(order)

    def __settlement(self, data: ndarray, all: bool=False) -> None:
        """決済

        Args:
            data (ndarray): ローソク足データ
            all  (bool)   : Trueであればすべて決済

        Returns:
            None
        """
        settlement = Settlement(
            open_price=data[self.open_index],
            high_price=data[self.high_index],
            low_price =data[self.low_index],
            spread    =data[self.spread_index])
        
        for key in self.orders:
            for i in range(len(self.orders[key]) - 1, -1, -1):
                order: Order = self.orders[key][i]

                # すべてのポジションを決済
                if all:
                    self.__all_close(order, settlement) 

                # 損失確定
                self.__loss_fixed(order, settlement)

                # 利益確定
                self.__profit_fixed(order, settlement)

                # トレールストップ
                self.__calc_trail_stop(order, settlement)
                
                # 決済が確定したポジションを削除
                if order.result is not None:
                    order.settlement_time = data[self.time_index]

                    self.settlements.append(self.orders[key].pop(i))
    
    def __all_close(self, order: Order, settlement: Settlement) -> None:
        """すべてのポジションを決済

        Args:
            order      (Order)     : 発注データ
            settlement (Settlement): 決済データ
        
        Returns:
            None

        Note:
            買いの場合:
                始値 - 発注価格とする
            売りの場合:
                発注価格 - 始値 + スプレッドとする
            損益pipは、損益 / pipとする
        """
        if order.direction == Direction.ASK:
            order.settlement_price = settlement.open_price

            result = order.settlement_price - order.order_price
        else:
            order.settlement_price = settlement.open_price + settlement.spread

            result = order.order_price - order.settlement_price

        order.result = round(result / self.parameter.pip, 2)
        
    def __loss_fixed(self, order: Order, settlement: Settlement) -> None:
        """損失確定

        Args:
            order      (Order)     : 発注データ
            settlement (Settlement): 決済データ
        
        Returns:
            None
        
        Note:
            買いの場合:
                安値が損失価格以下であれば、損失確定とする
            売りの場合:
                高値 + スプレッドが損失価格以上であれば、損失確定とする
            損失pipは、損失 / pipとする
            確定した損失pipが指定した損失pipより大きければ指定した損失pipとする
        """
        # 決済済みの場合は何もしない
        if order.result is not None:
            return

        result = None

        if order.direction == Direction.ASK:
            target_price = settlement.low_price

            if order.loss_price >= target_price:
                order.settlement_price = target_price

                result = order.loss_price - order.order_price
        else:
            target_price = settlement.high_price + settlement.spread

            if order.loss_price <= target_price:
                order.settlement_price = target_price

                result = order.order_price - order.loss_price

        if result is not None:
            result = round(result / self.parameter.pip, 2)
            result = (
                self.parameter.loss * -1 
                if abs(result) >= self.parameter.loss 
                else result)

            order.result = result
    
    def __profit_fixed(self, order: Order, settlement: Settlement) -> None:
        """利益確定

        Args:
            order      (Order)     : 発注データ
            settlement (Settlement): 決済データ
        
        Returns:
            None
        
        Note:
            買いの場合:
                高値が利益価格より高ければ、利益確定とする
            売りの場合:
                安値 + スプレッドが利益価格より低ければ、利益確定とする
        """
        # 決済済みの場合は何もしない
        if order.result is not None:
            return

        if order.direction == Direction.ASK:
            target_price = settlement.high_price

            if order.profit_price < target_price:
                order.settlement_price = target_price
                order.result           = self.parameter.profit
        else:
            target_price = settlement.low_price + settlement.spread

            if order.profit_price > target_price:
                order.settlement_price = target_price
                order.result           = self.parameter.profit
    
    def __calc_trail_stop(self, order: Order, settlement: Settlement) -> None:
        """トレールストップ

        Args:
            order      (Order)     : 発注データ
            settlement (Settlement): 決済データ
        
        Returns:
            None

        Note:
            買いの場合:
                高値 - 損失pipが損失価格より高ければ、損失価格を高値 - 損失pipとする
            売りの場合:
                安値 + 損失pipが損失価格より低ければ、損失価格を安値 + 損失pipとする
        """
        # 決済済みの場合は何もしない
        if order.result is not None:
            return
        
        # trail_stopがTrueでない場合は何もしない
        if not self.parameter.trail_stop:
            return

        loss_pip = self.parameter.loss * self.parameter.pip

        if order.direction == Direction.ASK:
            target_price = (
                settlement.high_price + settlement.spread) - loss_pip

            if order.loss_price < target_price:
                order.loss_price = target_price
        else:
            target_price = settlement.low_price + loss_pip

            if order.loss_price > target_price:
                order.loss_price = target_price


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

    def performance(self) -> dict:
        """実績

        Returns:
            dict: 実績
        """
        # 損益回数
        profit_count = self.df[self.df['result'] >= 0]['result'].count()
        loss_count   = self.df[self.df['result'] < 0]['result'].count()
        total_count  = profit_count + loss_count

        # 勝率
        profit_rate  = round((profit_count / total_count) * 100, 0)

        # 損益合計
        result = self.df['result'].sum()
        
        # 実績の詳細
        year_detail  = self.__detail(group_list=['year'])
        month_detail = self.__detail(group_list=['year', 'month'])
        week_detail  = self.__detail(group_list=['year', 'week'])
        day_detail   = self.__detail(group_list=['year', 'month', 'day'])

        return {
            'total_count' : total_count,
            'profit_count': profit_count,
            'loss_count'  : loss_count,
            'profit_rate' : profit_rate,
            'result'      : result,
            'profit'      : self.parameter.profit,
            'loss'        : self.parameter.loss,
            'detail'      : {
                'year': year_detail, 
                'month': month_detail, 
                'week': week_detail, 
                'day': day_detail}}
    
    def __detail(self, group_list: list) -> dict:
        """実績の詳細

        Args:
            group_list (list): groupbyの引数
        
        Returns:
            dict: 実績の詳細
        """
        # 損益毎のグループ化
        group        = self.df.groupby(group_list)
        profit_group = self.df.loc[self.df['result'] >= 0].groupby(group_list)
        loss_group   = self.df.loc[self.df['result'] < 0].groupby(group_list)

        # 損益回数
        profit = profit_group.count()['result']
        loss   = loss_group.count()['result']

        count_df = pd.merge(
            profit, loss, how='outer', left_index=True, right_index=True)
        count_df = count_df.rename(
            columns={'result_x': 'profit_count', 'result_y': 'loss_count'})
        count_df = count_df.fillna({'profit_count': 0, 'loss_count': 0})

        count_df['total_count'] = (
            count_df['profit_count'] + count_df['loss_count'])

        # 勝率
        count_df['profit_rate'] = round(
            (count_df['profit_count'] / count_df['total_count']) * 100, 0)

        # 損益合計
        sum_df = group.sum('result')['result']

        merge_df = pd.merge(
            sum_df, count_df, how='outer', left_index=True, right_index=True)
        merge_df = merge_df.fillna(
            {
                'profit_count': 0, 
                'loss_count': 0, 
                'total_count': 0, 
                'profit_rate': 0})
        merge_df = merge_df.reset_index()

        return merge_df.to_dict(orient='records')
