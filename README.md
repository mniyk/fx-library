# fx-library
FX related library with Python

## Install
```
pip install git+https://github.com/mniyk/fx-library.git
```

## mt5
Package for operating MetaTrader5

 ### External Library
 - [MetaTrader5](https://pypi.org/project/MetaTrader5/)
   
 ### Examples
 ```
 from datetime import datetime, timedelta

 from fx_library.mt5 import Mt5
 
 
 # MT5インスタンスの作成
 app = Mt5(id=123456789, password='password', server='server') 

 # 接続
 app.connect()
 
 # 口座情報の取得
 account_info = app.get_account_info()
 
 # 通貨ペア情報の取得
 symbol_info = app.get_symbol_info(symbol='USDJPY')

 # ローソク足データの取得
 from_datetime = datetime.now() + timedelta(days=5)

 candles = app.get_candles(
     symbol='USDJPY', timeframe='H1', from_datetime=from_datetime, data_count=5)
 
 # 発注
 order = app.send_order(symbol='USDJPY', lot=0.1, direction=1, magic=0)
 
 # 指値と逆指値の送信
 order = app.send_profit_and_loss(
     ticket=order['order'], profit=100, loss=100, pip=0.01)
 
 # ポジションの取得
 positions = app.get_positions(symbol='USDJPY')
 positions = app.get_positions(ticket=order['order'])
 
 # 注文履歴を取得
 from_datetime = datetime.now() - timedelta(days=365)
 to_datetime = datetime.now() + timedelta(days=5)

 history_orders = app.get_history_orders(
     from_datetime=from_datetime, to_datetime=to_datetime)

 # 取引履歴を取得
 history_deals = app.get_history_deals(
     from_datetime=from_datetime, to_datetime=to_datetime)
 
 # 切断
 app.disconnect()
 ```

## technical_indicators
Package for creating technical indicators

 ### External Library
 - [pyti](https://pypi.org/project/pyti/)
   
 ### Examples
 ```
 from datetime import datetime, timedelta

 import pandas as pd

 from fx_library.mt5 import Mt5
 from fx_library.technical_indicators import TechnicalIndicators as Tech


 # MT5インスタンスの作成
 app = Mt5(id=123456789, password='password', server='server') 
 
 # 接続
 app.connect()

 # ローソク足データの取得
 from_datetime = datetime.now() + timedelta(days=5)

 candles = app.get_candles(
     symbol='USDJPY', timeframe='H1', from_datetime=from_datetime, data_count=5)
 
 df = pd.DataFrame(candles)

 # EMAの計算
 df = Tech.calculation_ema(df=df, calculation_column='close', period=12)
 
 # MACDの計算
 df = Tech.calculation_macd(
     df=df, calculation_column='close', short=12, long=26, signal=9)

 # RCIの計算
 df = Tech.calculation_rci(df=df, calculation_column='close', period=12)
 
 # SMAの計算
 df = Tech.calculation_sma(df=df, calculation_column='close', period=12)

 # ストキャスティクスの計算
 df = Tech.calculation_stochastics(df=df, calculation_column='close', period=12)

 # 前回値と前回値との差を追加
 df = Tech.add_previous_value_shift_and_diff( 
     df=df, technical_indicator_name='rci')

 # 切断
 app.disconnect()
 ```

## backtest
Package for backtest

 ### External Library
   
 ### Examples
 ```
 from datetime import datetime, timedelta

 import pandas as pd

 from fx_library.mt5 import Mt5
 from fx_library.technical_indicators import TechnicalIndicators as Tech
 from fx_library.backtest import Backtest


 # MT5インスタンスの作成
 app = Mt5(id=123456789, password='password', server='server') 
 
 # 接続
 app.connect()

 # ローソク足データの取得
 from_datetime = datetime.now() + timedelta(days=5)

 candles = app.get_candles(
     symbol='USDJPY', timeframe='H1', from_datetime=from_datetime, data_count=5)
 
 df = pd.DataFrame(candles)

 # RCIの計算
 df = Tech.calculation_rci(df=df, calculation_column='close', period=12)

 # 前回値と前回値との差を追加
 df = Tech.add_previous_value_shift_and_diff( 
     df=df, technical_indicator_name='rci')

 # Backtestインスタンスの作成
 back = Backtest(
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

 # バックテストの実行
 back.run(
     func=direction_by_value_range, 
     reverse_order=reverse_order, 
     ranges={
         'rci_12': {'ask': [80, 100], 'bid': [-80, -100]},
         'rci_12_shift_diff': {'ask': [0, 100], 'bid': [0, -100]}},
     backtest=True)

 # 実績
 performance_result = Backtest.performance(
     back.result_df, profit=profit, loss=loss)

 # 切断
 app.disconnect()
 ```
