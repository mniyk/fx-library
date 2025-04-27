"""テクニカル指標を計算するモジュール
"""


import numpy as np
from pandas import DataFrame
from pyti.exponential_moving_average import exponential_moving_average as ema
from pyti.moving_average_convergence_divergence import (
    moving_average_convergence_divergence as macd)
from pyti.stochastic import percent_k
from pyti.stochastic import percent_d
from pyti.simple_moving_average import simple_moving_average as sma
from pyti.stochrsi import stochrsi


class TechnicalIndicators:
    @classmethod
    def calculation_ema(
        cls, 
        df: DataFrame, 
        calculation_column: str, 
        period: int,
        digits: int=4):
        """EMAの計算
        
        Args:
            df                 (DataFrame): ローソク足のデータフレーム
            calculation_column (str)      : 計算用の列名
            period             (int)      : 期間
            digits             (int)      : 小数点の桁数

        Returns:
            DataFrame: テクニカル指標を追加後のデータフレーム

        Examples:
            >>> df = Tech.calculation_ema( 
                    df=df, calculation_column='close', period=12)
        """
        df[f'ema_{period}'] = ema(
            df[calculation_column].values.tolist(), period)
        df[f'ema_{period}'] = df[f'ema_{period}'].round(digits)
        
        return df

    @classmethod
    def calculation_macd(
        cls, 
        df: DataFrame, 
        calculation_column: str, 
        short: int, 
        long: int, 
        signal: int, 
        digits: int=4
    ):
        """MACDの計算

        Args:
            df           (DataFrame): ローソク足のデータフレーム
            calculation_column (str): 計算用の列名
            short              (int): 短期
            long               (int): 長期
            signal             (int): シグナル
            digits             (int): 小数点の桁数
            
        Returns:
            DataFrame: テクニカル指標を追加後のデータフレーム
       
        Examples:
            >>> df = Tech.calculation_macd(
                    df=df, 
                    calculation_column='close', 
                    short=12, 
                    long=26, 
                    signal=9)
        """
        df[f'macd'] = macd(df[calculation_column].values.tolist(), short, long)
        df[f'macd_signal'] = sma(df[f'macd'].values.tolist(), signal)

        df[f'macd'] = df[f'macd'].round(digits)
        df[f'macd_signal'] = df[f'macd_signal'].round(digits)
        
        return df

    @classmethod
    def calculation_rci(
        cls,
        df: DataFrame, 
        calculation_column: str, 
        period: int, 
        digits: int=4):
        """RCIの計算

        Args:
            df                 (DataFrame): ローソク足のデータフレーム
            calculation_column (str)      : 計算用の列名
            period             (int)      : 期間
            digits             (int)      : 小数点の桁数

        Returns:
            DataFrame: テクニカル指標を追加後のデータフレーム

        Examples:
            >>> df = Tech.calculation_rci(
                    df=df, calculation_column='close', period=12)
        """
        rci_col = f'rci_{period}'

        df[rci_col] = np.nan

        for i, _ in df.iterrows():
            if i >= period:
                period_df = df.loc[i - period:i - 1].copy()
                period_df['date_rank'] = np.arange(period, 0, -1)
                period_df = period_df.sort_values(
                    calculation_column, ascending=False).reset_index(drop=True)
                period_df['price_rank'] = np.arange(1, period + 1)
                period_df['delta'] = (
                    period_df['price_rank'] - period_df['date_rank']) ** 2
                d = period_df['delta'].sum()
                df.loc[i, rci_col] = (
                    (1 - (6 * d) / (period ** 3 - period)) * 100).round(digits)

        return df
    
    @classmethod
    def calculation_sma(
        cls, 
        df: DataFrame, 
        calculation_column: str, 
        period: int,
        digits: int=4):
        """SMAの計算
        
        Args:
            df                 (DataFrame): ローソク足のデータフレーム
            calculation_column (str)      : 計算用の列名
            period             (int)      : 期間
            digits             (int)      : 小数点の桁数

        Returns:
            DataFrame: テクニカル指標を追加後のデータフレーム

        Examples:
            >>> df = Tech.calculation_sma(
                    df=df, calculation_column='close', period=12)
        """
        df[f'sma_{period}'] = sma(
            df[calculation_column].values.tolist(), period)
        df[f'sma_{period}'] = df[f'sma_{period}'].round(digits)
        
        return df


    @classmethod
    def calculation_stochastics(
        cls, 
        df: DataFrame, 
        calculation_column: str,
        period: int,
        digits: int=4
    ):
        """ストキャスティクスの計算

        Args:
            df                 (DataFrame): ローソク足のデータフレーム
            calculation_column (str)      : 計算用の列名
            period             (int)      : 期間
            digits             (int)      : 小数点の桁数

        Returns:
            DataFrame: テクニカル指標を追加後のデータフレーム
        
        Examples:
            >>> df = Tech.calculation_stochastics(
                    df=df, calculation_column='close', period=12)
        """
        df[f'stoch_k'] = percent_k(
            df[calculation_column].values.tolist(), period
        ).round(digits)
        df[f'stoch_d'] = percent_d(
            df[calculation_column].values.tolist(), period
        ).round(digits)
        df[f'stoch_rsi'] = stochrsi(
            df[calculation_column].values.tolist(), period
        ).round(digits)
        
        return df
    
    @classmethod
    def calculation_dmi(
        cls, df: DataFrame, calculation_column: str, period: int):
        """DMIの計算

        Args:
            df                 (DataFrame): ローソク足のデータフレーム
            calculation_column (str)      : 計算用の列名
            period             (int)      : 期間

        Returns:
            DataFrame: テクニカル指標を追加後のデータフレーム
        
        Examples:
            >>> df = Tech.calculation_dmi(
                    df=df, calculation_column='close', period=12)
        """
        df[f'prev'] = df[calculation_column].shift(1)
        df[f'tr'] = np.maximum(
            df['high'] - df['low'], 
            np.maximum(abs(df['high'] - df[f'prev']), abs(df['low'] - df[f'prev'])))

        df[f'plus_dm'] = np.where(
            (df['high'] - df['high'].shift(1)) > (df['low'].shift(1) - df['low']), 
            np.maximum(df['high'] - df['high'].shift(1), 0),
            0)
        df[f'minus_dm'] = np.where(
            (df['low'].shift(1) - df['low']) > (df['high'] - df['high'].shift(1)), 
            np.maximum(df['low'].shift(1) - df['low'], 0), 
            0)

        df[f'smoothed_tr'] = df[f'tr'].ewm(span=period, adjust=False).mean()
        df[f'smoothed_plus_dm'] = df[f'plus_dm'].ewm(span=period, adjust=False).mean()
        df[f'smoothed_minus_dm'] = df[f'minus_dm'].ewm(span=period, adjust=False).mean()

        df[f'plus_di'] = (df[f'smoothed_plus_dm'] / df[f'smoothed_tr']) * 100
        df[f'minus_di'] = (df[f'smoothed_minus_dm'] / df[f'smoothed_tr']) * 100

        df[f'dx'] = (abs(df[f'plus_di'] - df[f'minus_di']) / (df[f'plus_di'] + df[f'minus_di'])) * 100
        df[f'adx'] = df[f'dx'].ewm(span=period, adjust=False).mean()

        return df

    @classmethod
    def add_previous_value_shift_and_diff(
        cls, 
        df: DataFrame, 
        technical_indicator_name: str, 
        diff: bool = True,
        digits: int=4):
        """前回値と前回値との差を追加

        Args:
            df                       (DataFrame): ローソク足のデータフレーム
            technical_indicator_name (str)      : テクニカル指標の名前
            diff                     (bool)     : Trueであれば、前回値との差を追加
        
        Returns:
            DataFrame: テクニカル指標を追加後のデータフレーム 

        Examples:
            >>> df = Tech.add_previous_value_shift_and_diff(
                    df=df, technical_indicator_name='rci')
        """
        for column in df.columns:
            if technical_indicator_name in column:
                df[f'{column}_shift'] = df[column].shift(1)

                if diff:
                    df[f'{column}_shift_diff'] = (
                        df[column] - df[f'{column}_shift']).round(digits)
        
        return df
