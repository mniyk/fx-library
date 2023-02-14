"""MT5を操作するためのモジュール
"""


from datetime import datetime
from enum import Enum
from typing import List, Dict

import MetaTrader5


class RequestError(Exception):
    """MT5へのリクエスト時のエラー
    """
    pass

class Timeframes(Enum):
    """Mt5で使用可能な時間枠
    """
    M1 = MetaTrader5.TIMEFRAME_M1
    M2 = MetaTrader5.TIMEFRAME_M2
    M3 = MetaTrader5.TIMEFRAME_M3
    M4 = MetaTrader5.TIMEFRAME_M4
    M5 = MetaTrader5.TIMEFRAME_M5
    M6 = MetaTrader5.TIMEFRAME_M6
    M10 = MetaTrader5.TIMEFRAME_M10
    M12 = MetaTrader5.TIMEFRAME_M12
    M15 = MetaTrader5.TIMEFRAME_M15
    M20 = MetaTrader5.TIMEFRAME_M20
    M30 = MetaTrader5.TIMEFRAME_M30
    H1 = MetaTrader5.TIMEFRAME_H1
    H2 = MetaTrader5.TIMEFRAME_H2
    H3 = MetaTrader5.TIMEFRAME_H3
    H4 = MetaTrader5.TIMEFRAME_H4
    H6 = MetaTrader5.TIMEFRAME_H6
    H8 = MetaTrader5.TIMEFRAME_H8
    H12 = MetaTrader5.TIMEFRAME_H12
    D = MetaTrader5.TIMEFRAME_D1

class Mt5:
    """MT5を使用するためのクラス
    """
    def __init__(self, id: int, password: str, server: str) -> None:
        """初期化
        
        Args:
            id (int): ID
            password (str): パスワード
            server (str): サーバー名
        
        Examples:
            >>> from fx_library.mt5 import Mt5
            >>> app = Mt5(id=123456789, password='password', server='server') 
        """
        self.id = id
        self.password = password
        self.server = server
        
    def connect(self) -> None:
        """接続

        Examples:
            >>> app.connect()
        """
        MetaTrader5.initialize(
            login=self.id, password=self.password, server=self.server)
    
    def disconnect(self) -> None:
        """切断

        Examples:
            >>> app.disconnect()
        """
        MetaTrader5.shutdown()
    
    def get_account_info(self) -> Dict:
        """口座情報の取得

        Returns:
            Dict: 口座情報

        Examples:
            >>> account_info = app.get_account_info()
        """
        return MetaTrader5.account_info()._asdict()

    def get_symbol_info(self, symbol: str) -> Dict:
        """通貨ペア情報の取得
        
        Args:
            symbol (str): 通貨ペア

        Returns:
            Dict: 通貨ペア情報
        
        Examples:
            >>> symbol_info = app.get_symbol_info(symbol='USDJPY')
        """
        return MetaTrader5.symbol_info(symbol.upper())._asdict()

    def get_candles(
        self, 
        symbol: str, 
        timeframe: str, 
        from_datetime: datetime, 
        data_count: int=99999) -> List:
        """終了日時とデータ数でのローソク足データの取得

        終了日時からデータ数分、以前のデータを取得する

        Args:
            symbol (str): 通貨ペア
            timeframe (str): ローソク足時間
            from_datetime (datetime): 終了日時
            data_count (int): データ数

        Returns:
            List: ローソク足データのリスト

        Examples:
            >>> from_datetime = datetime.now() + timedelta(days=5)
            >>> candles = app.get_candles(
                    symbol='USDJPY', 
                    timeframe='H1', 
                    from_datetime=from_datetime, 
                    data_count=5)
        """
        response = MetaTrader5.copy_rates_from(
            symbol.upper(), 
            Timeframes[timeframe.upper()].value, 
            from_datetime, 
            data_count)

        candles = [{
            'time': datetime.utcfromtimestamp(data[0]),
            'open': data[1],
            'high': data[2],
            'low': data[3],
            'close': data[4],
            'volume': data[5],
            'spread': data[6]}
            for data in response]
        
        return candles

    def send_order(
        self,
        symbol: str, 
        lot: int, 
        direction: int, 
        magic: int,
        deviation: int=10) -> Dict:
        """発注

        Args:
            symbol (str): 通貨ペア
            lot (int): 注文数
            direction (int): 売買方向
            magic (int): 取引方法のID
            deviation (int): スリッページ
        
        Returns
            Dict: 発注結果
        
        Examples:
            >>> order = app.send_order(
                    symbol='USDJPY', lot=0.1, direction=1, magic=0)
        """
        if direction == 1:
            order_type = MetaTrader5.ORDER_TYPE_BUY
        elif direction == -1:
            order_type = MetaTrader5.ORDER_TYPE_SELL
        else:
            return None

        request = {
            'action': MetaTrader5.TRADE_ACTION_DEAL,
            'symbol': symbol.upper(),
            'volume': lot,
            'deviation': deviation,
            'type': order_type,
            'magic': magic,
            'type_time': MetaTrader5.ORDER_TIME_GTC,
            'type_filling': MetaTrader5.ORDER_FILLING_IOC}

        order = MetaTrader5.order_send(request)._asdict()

        if order['comment'] != 'Request executed':
            raise RequestError

        return order 

    def send_profit_and_loss(
        self, ticket: int, profit: int, loss: int, pip: float) -> Dict:
        """指値と逆指値を送信

        Args:
            ticket: チケット
            profit: 利益
            loss: 損失
            pip: pip単位
        
        Returns:
            Dict: 設定結果

        Examples:
            >>> order = app.send_profit_and_loss(
                    ticket=order['order'], profit=100, loss=100, pip=0.01)
        """
        positions = self.get_positions(ticket=ticket)
        position = positions[0]

        price = position['price_open']

        if position['type'] == 0:
            profit_price = price + (profit * pip)
            loss_price = price - (loss * pip)
        elif position['type'] == 1:
            profit_price = price - (profit * pip)
            loss_price = price + (loss * pip)
        
        request = {
            'action': MetaTrader5.TRADE_ACTION_SLTP,
            'position': ticket,
            'sl': loss_price,
            'tp': profit_price}

        order = MetaTrader5.order_send(request)._asdict()
        
        if order['comment'] != 'Request executed':
            raise RequestError

        return order

    def get_positions(self, symbol: str=None, ticket: int=None) -> List:
        """ポジションの取得

        Args:
            symbol (str): 通貨ペア
            ticket (int): チケット

        Returns:
            List: ポジションのリスト

        Examples:
            >>> positions = app.get_positions(symbol='USDJPY)
            >>> positions = app.get_positions(ticket=order['order'])
            >>> positions = app.get_positions()
        """
        if symbol:
            response = MetaTrader5.positions_get(symbol=symbol.upper())
        elif ticket:
            response = MetaTrader5.positions_get(ticket=ticket)
        else:
            response = MetaTrader5.positions_get()

        positions = [data._asdict() for data in response]

        return positions
    
    def close_positions(self, symbol: str=None, ticket: int=None) -> List:
        """ポジションの決済

        Args:
            symbol (str): 通貨ペア
            ticket (int): チケット

        Returns:
            List: 決済のリスト

        Examples:
            >>> positions = app.close_positions(symbol='USDJPY)
            >>> positions = app.close_positions(ticket=order['order'])
            >>> positions = app.close_positions()
        """
        result = []

        positions = self.get_positions(symbol=symbol, ticket=ticket)

        for position in positions:
            order_type = (
                MetaTrader5.ORDER_TYPE_SELL 
                if position['type'] == MetaTrader5.ORDER_TYPE_BUY else 
                MetaTrader5.ORDER_TYPE_BUY)
            
            request = {
                'action': MetaTrader5.TRADE_ACTION_DEAL,
                'symbol': position['symbol'],
                'volume': position['volume'],
                'position': position['ticket'],
                'type': order_type,
                'type_time': MetaTrader5.ORDER_TIME_GTC,
                'type_filling': MetaTrader5.ORDER_FILLING_IOC}

            order = MetaTrader5.order_send(request)._asdict()
            
            result.append(order)
        
        return result

    def get_history_orders(
        self, from_datetime: datetime, to_datetime: datetime) -> List:
        """注文履歴を取得

        Args:
            from_datetime (datetime): 
            to_datetime (datetime): 
        
        Returns:
            List: 注文のリスト

        Examples:
            >>> from_datetime = datetime.now() - timedelta(days=365)
            >>> to_datetime = datetime.now() + timedelta(days=5)
            >>> history_orders = app.get_history_orders(
                    from_datetime=from_datetime, to_datetime=to_datetime)
        """
        response = MetaTrader5.history_orders_get(from_datetime, to_datetime)
        
        history_orders = [{
            'ticket': data.ticket,
            'time_setup': datetime.utcfromtimestamp(data.time_setup),
            'time_setup_msc': data.time_setup_msc,
            'time_done': datetime.utcfromtimestamp(data.time_done),
            'time_done_msc': data.time_done_msc,
            'time_expiration': data.time_expiration,
            'type': data.type,
            'type_time': data.type_time,
            'type_filling': data.type_filling,
            'state': data.state,
            'magic': data.magic,
            'position_id': data.position_id,
            'position_by_id': data.position_by_id,
            'reason': data.reason,
            'volume_initial': data.volume_initial,
            'volume_current': data.volume_current,
            'price_open': data.price_open,
            'sl': data.sl,
            'tp': data.tp,
            'price_current': data.price_current,
            'price_stoplimit': data.price_stoplimit,
            'symbol': data.symbol,
            'comment': data.comment,
            'external_id': data.external_id}
            for data in response]
        
        return history_orders

    def get_history_deals(
        self, from_datetime: datetime, to_datetime: datetime) -> List:
        """取引履歴を取得

        Args:
            from_datetime (datetime): 
            to_datetime (datetime): 
        
        Returns:
            List: 取引のリスト

        Examples:
            >>> from_datetime = datetime.now() - timedelta(days=365)
            >>> to_datetime = datetime.now() + timedelta(days=5)
            >>> history_deals = app.get_history_deals(
                    from_datetime=from_datetime, to_datetime=to_datetime)
        """
        response = MetaTrader5.history_deals_get(from_datetime, to_datetime)
        
        history_deals = [{
            'ticket': data.ticket,
            'order': data.order,
            'time': datetime.utcfromtimestamp(data.time),
            'time_msc': data.time_msc,
            'type': data.type, 
            'entry': data.entry,
            'magic': data.magic,
            'position_id': data.position_id,
            'reason': data.reason,
            'volume': data.volume,
            'price': data.price,
            'commition': data.commission,
            'swap': data.swap,
            'profit': data.profit,
            'fee': data.fee,
            'symbol': data.symbol,
            'comment': data.comment,
            'external_id': data.external_id}
            for data in response]
        
        return history_deals 
    