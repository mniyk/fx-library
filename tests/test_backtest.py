from datetime import datetime
from io       import StringIO

import pandas as pd
import pytest

from fx_library import backtest, utils


DIRECTION_PARAMETER = {
    'ranges': {
        'period_34_shift_diff_under': {'ask': [0, 100], 'bid': [0, -100]},
        'period_144_shift_diff_top' : {'ask': [0, 100], 'bid': [0, -100]},
    }
}

PARAMETER = backtest.Parameter(
    symbol             ='USDJPY',
    timeframes         =['M5', 'H1'],
    technical_indicator='sma',
    direction_function =utils.direction_by_value_range,
    direction_parameter=DIRECTION_PARAMETER,
    trade_start_hour   =3,
    trade_end_hour     =23,
    position_count     =1,
    profit             =100,
    loss               =100,
    trail_stop         =True,
    spread_threshold   =0.2,
    pip                =0.01,
    reverse_order      =False,
    time_column        ='time_under',
    open_column        ='open_under',
    high_column        ='high_under',
    low_column         ='low_under',
    close_column       ='close_under',
    spread_column      ='spread_under',
    technical_column   ='close')

DATA = '''time_under,open_under,high_under,low_under,close_under,spread_under,period_34_shift_diff_under,period_144_shift_diff_top
2024-01-01 00:00:00,100.0,100.0,100.0,100.0,0.003,50,50
2024-01-01 01:00:00,100.0,100.5,100.0,100.5,0.003,-50,-50
2024-01-01 02:00:00,100.0,101.1,100.0,100.0,0.003,0,0
2024-01-01 03:00:00,100.0,100.0,98.5,100.0,0.003,0,0'''


class TestBacktest:
    def setup_method(self, method):
        self.df               = pd.read_csv(StringIO(DATA))
        self.df['time_under'] = pd.to_datetime(self.df['time_under'])
        self.back             = backtest.Backtest(self.df, PARAMETER)
    
    def test___init__(self):
        assert list(self.back.columns) == [
            'time_under', 'open_under', 'high_under', 'low_under', 
            'close_under', 'spread_under', 'period_34_shift_diff_under',
            'period_144_shift_diff_top']
        assert self.back.time_index   == 0
        assert self.back.open_index   == 1
        assert self.back.close_index  == 4
        assert self.back.high_index   == 2
        assert self.back.low_index    == 3
        assert self.back.spread_index == 5

    @pytest.mark.parametrize(
        'trade_hour, spread, reverse_order, orders, settlements',
        [
            # トレード期間対象外
            [
                [3, 24], 
                0.2,
                False,
                {backtest.Direction.ASK: [], backtest.Direction.BID: []},
                []
            ],
            [
                [0, 24], 
                0.002,
                False,
                {backtest.Direction.ASK: [], backtest.Direction.BID: []},
                []
            ],
            # トレード
            [
                [0, 24], 
                0.2,
                False,
                {backtest.Direction.ASK: [], backtest.Direction.BID: []},
                [
                    backtest.Order(
                        order_time      =datetime(2024, 1, 1, 0, 0, 0),
                        order_price     =100.003,
                        spread          =0.003,
                        direction       =backtest.Direction.ASK,
                        profit_price    =101.003,
                        loss_price      =99.003,
                        settlement_time =datetime(2024, 1, 1, 2, 0, 0),
                        settlement_price=101.1,
                        result          =100
                    ),
                    backtest.Order(
                        order_time      =datetime(2024, 1, 1, 1, 0, 0),
                        order_price     =100.5,
                        spread          =0.003,
                        direction       =backtest.Direction.BID,
                        profit_price    =99.5,
                        loss_price      =101.5,
                        settlement_time =datetime(2024, 1, 1, 3, 0, 0),
                        settlement_price=98.503,
                        result          =100
                    )
                ]
            ],
            # トレード(逆方向への発注)
            [
                [0, 24], 
                0.2,
                True,
                {backtest.Direction.ASK: [], backtest.Direction.BID: []},
                [
                    backtest.Order(
                        order_time      =datetime(2024, 1, 1, 0, 0, 0),
                        order_price     =100.003,
                        spread          =0.003,
                        direction       =backtest.Direction.ASK,
                        profit_price    =101.003,
                        loss_price      =99.003,
                        settlement_time =datetime(2024, 1, 1, 2, 0, 0),
                        settlement_price=101.1,
                        result          =100
                    ),
                    backtest.Order(
                        order_time      =datetime(2024, 1, 1, 0, 0, 0),
                        order_price     =100.000,
                        spread          =0.003,
                        direction       =backtest.Direction.BID,
                        profit_price    =99.000,
                        loss_price      =101.000,
                        settlement_time =datetime(2024, 1, 1, 2, 0, 0),
                        settlement_price=101.103,
                        result          =-100
                    )
                ]
            ],
        ]
    )
    def test_run(
        self, 
        trade_hour: list, 
        spread: float, 
        reverse_order: bool, 
        orders: dict, 
        settlements: list):
        self.back.parameter.spread_threshold = spread
        self.back.parameter.trail_stop       = False
        self.back.parameter.reverse_order    = reverse_order
        self.back.parameter.trade_start_hour = trade_hour[0]
        self.back.parameter.trade_end_hour   = trade_hour[1]

        self.back.run()

        self.back.parameter.trail_stop    = True
        self.back.parameter.reverse_order = False

        assert self.back.orders      == orders
        assert self.back.settlements == settlements

    @pytest.mark.parametrize(
        'data, direction, last_orders, latest_orders',
        [
            # 既存の発注数が指定数未満
            [
                [datetime(2024, 1, 1, 0, 0), 100.0, 100.5, 99.5, 100.0, 0.003],
                backtest.Direction.ASK,
                {backtest.Direction.ASK: [], backtest.Direction.BID: []},
                {
                    backtest.Direction.ASK: [
                        backtest.Order(
                            order_time  =datetime(2024, 1, 1, 0, 0),
                            order_price =100.003,
                            spread      =0.003,
                            direction   =backtest.Direction.ASK,
                            profit_price=101.003,
                            loss_price  =99.003,
                        )
                    ],
                    backtest.Direction.BID: []
                }
            ],
            [
                [datetime(2024, 1, 1, 0, 0), 100.0, 100.5, 99.5, 100.0, 0.003],
                backtest.Direction.BID,
                {backtest.Direction.ASK: [], backtest.Direction.BID: []},
                {
                    backtest.Direction.ASK: [
                    ],
                    backtest.Direction.BID: [
                        backtest.Order(
                            order_time  =datetime(2024, 1, 1, 0, 0),
                            order_price =100.0,
                            spread      =0.003,
                            direction   =backtest.Direction.BID,
                            profit_price=99.0,
                            loss_price  =101.0,
                        )
                    ]
                }
            ],
            # 既存の発注数が指定数以上
            [
                [datetime(2024, 1, 1, 0, 0), 100.0, 100.5, 99.5, 100.0, 0.003],
                backtest.Direction.ASK,
                {
                    backtest.Direction.ASK: [
                        backtest.Order(
                            order_time  =datetime(2023, 12, 31, 0, 0),
                            order_price =100.003,
                            spread      =0.003,
                            direction   =backtest.Direction.ASK,
                            profit_price=101.003,
                            loss_price  =99.003,
                        )
                    ],
                    backtest.Direction.BID: []
                },
                {
                    backtest.Direction.ASK: [
                        backtest.Order(
                            order_time  =datetime(2023, 12, 31, 0, 0),
                            order_price =100.003,
                            spread      =0.003,
                            direction   =backtest.Direction.ASK,
                            profit_price=101.003,
                            loss_price  =99.003,
                        )
                    ],
                    backtest.Direction.BID: []
                }
            ],
            [
                [datetime(2024, 1, 1, 0, 0), 100.0, 100.5, 99.5, 100.0, 0.003],
                backtest.Direction.BID,
                {
                    backtest.Direction.ASK: [], 
                    backtest.Direction.BID: [
                        backtest.Order(
                            order_time  =datetime(2023, 12, 31, 0, 0),
                            order_price =100.0,
                            spread      =0.003,
                            direction   =backtest.Direction.BID,
                            profit_price=99.0,
                            loss_price  =101.0,
                        )
                    ]
                },
                {
                    backtest.Direction.ASK: [
                    ],
                    backtest.Direction.BID: [
                        backtest.Order(
                            order_time  =datetime(2023, 12, 31, 0, 0),
                            order_price =100.0,
                            spread      =0.003,
                            direction   =backtest.Direction.BID,
                            profit_price=99.0,
                            loss_price  =101.0,
                        )
                    ]
                }
            ],
        ]
    )
    def test___order(
        self, data: list, direction: int, last_orders: dict, latest_orders: dict):
        self.back.orders = last_orders
        self.back._Backtest__order(data, direction)

        assert self.back.orders == latest_orders

    @pytest.mark.parametrize(
        'data, all, orders, latest_orders, settlements',
        [
            # すべてのポジションを決済
            [
                [datetime(2024, 1, 2, 0, 0), 100.5, 101.5, 99.5, 100.5, 0.003],
                True, 
                {
                    backtest.Direction.ASK: [
                        backtest.Order(
                            order_time  =datetime(2024, 1, 1, 0, 0),
                            order_price =100.0,
                            spread      =0.003,
                            direction   =backtest.Direction.ASK,
                            profit_price=101.0,
                            loss_price  =99.0,
                        ),
                    ],
                    backtest.Direction.BID: [
                        backtest.Order(
                            order_time  =datetime(2024, 1, 1, 0, 0),
                            order_price =100.0,
                            spread      =0.003,
                            direction   =backtest.Direction.BID,
                            profit_price=99.0,
                            loss_price  =101.0,
                        ),
                    ]
                },
                {backtest.Direction.ASK: [], backtest.Direction.BID: []},
                [
                    backtest.Order(
                        order_time      =datetime(2024, 1, 1, 0, 0),
                        order_price     =100.0,
                        spread          =0.003,
                        direction       =backtest.Direction.ASK,
                        profit_price    =101.0,
                        loss_price      =99.0,
                        settlement_time =datetime(2024, 1, 2, 0, 0),
                        settlement_price=100.5,
                        result          =50.0
                    ),
                    backtest.Order(
                        order_time      =datetime(2024, 1, 1, 0, 0),
                        order_price     =100.0,
                        spread          =0.003,
                        direction       =backtest.Direction.BID,
                        profit_price    =99.0,
                        loss_price      =101.0,
                        settlement_time =datetime(2024, 1, 2, 0, 0),
                        settlement_price=100.503,
                        result          =-50.3
                    ),
                ]
            ],
            # 損失確定
            [
                [datetime(2024, 1, 2, 0, 0), 100.5, 101.1, 99.0, 100.5, 0.003],
                False, 
                {
                    backtest.Direction.ASK: [
                        backtest.Order(
                            order_time  =datetime(2024, 1, 1, 0, 0),
                            order_price =100.0,
                            spread      =0.003,
                            direction   =backtest.Direction.ASK,
                            profit_price=101.0,
                            loss_price  =99.0,
                        ),
                    ],
                    backtest.Direction.BID: []
                },
                {backtest.Direction.ASK: [], backtest.Direction.BID: []},
                [
                    backtest.Order(
                        order_time      =datetime(2024, 1, 1, 0, 0),
                        order_price     =100.0,
                        spread          =0.003,
                        direction       =backtest.Direction.ASK,
                        profit_price    =101.0,
                        loss_price      =99.0,
                        settlement_time =datetime(2024, 1, 2, 0, 0),
                        settlement_price=99.0,
                        result          =-100.0
                    ),
                ]
            ],
            [
                [datetime(2024, 1, 2, 0, 0), 100.5, 101.1, 99.0, 100.5, 0.003],
                False, 
                {
                    backtest.Direction.ASK: [
                        backtest.Order(
                            order_time  =datetime(2024, 1, 1, 0, 0),
                            order_price =100.0,
                            spread      =0.003,
                            direction   =backtest.Direction.ASK,
                            profit_price=101.0,
                            loss_price  =99.0,
                        ),
                        backtest.Order(
                            order_time  =datetime(2024, 1, 1, 0, 0),
                            order_price =100.0,
                            spread      =0.003,
                            direction   =backtest.Direction.ASK,
                            profit_price=101.5,
                            loss_price  =98.0,
                        ),
                    ],
                    backtest.Direction.BID: []
                },
                {
                    backtest.Direction.ASK: [
                        backtest.Order(
                            order_time  =datetime(2024, 1, 1, 0, 0),
                            order_price =100.0,
                            spread      =0.003,
                            direction   =backtest.Direction.ASK,
                            profit_price=101.5,
                            loss_price  =100.103,
                        ),
                    ], 
                    backtest.Direction.BID: []
                },
                [
                    backtest.Order(
                        order_time      =datetime(2024, 1, 1, 0, 0),
                        order_price     =100.0,
                        spread          =0.003,
                        direction       =backtest.Direction.ASK,
                        profit_price    =101.0,
                        loss_price      =99.0,
                        settlement_time =datetime(2024, 1, 2, 0, 0),
                        settlement_price=99.0,
                        result          =-100.0
                    ),
                ]
            ],
            [
                [
                    datetime(2024, 1, 2, 0, 0), 
                    100.5,
                    100.997, 
                    98.996, 
                    100.5, 
                    0.003
                ],
                False, 
                {
                    backtest.Direction.ASK: [],
                    backtest.Direction.BID: [
                        backtest.Order(
                            order_time  =datetime(2024, 1, 1, 0, 0),
                            order_price =100.0,
                            spread      =0.003,
                            direction   =backtest.Direction.BID,
                            profit_price=99.0,
                            loss_price  =101.0,
                        ),
                    ]
                },
                {backtest.Direction.ASK: [], backtest.Direction.BID: []},
                [
                    backtest.Order(
                        order_time      =datetime(2024, 1, 1, 0, 0),
                        order_price     =100.0,
                        spread          =0.003,
                        direction       =backtest.Direction.BID,
                        profit_price    =99.0,
                        loss_price      =101.0,
                        settlement_time =datetime(2024, 1, 2, 0, 0),
                        settlement_price=101.0,
                        result          =-100.0
                    ),
                ]
            ],
            [
                [
                    datetime(2024, 1, 2, 0, 0), 
                    100.5,
                    100.997, 
                    98.996, 
                    100.5, 
                    0.003
                ],
                False, 
                {
                    backtest.Direction.ASK: [],
                    backtest.Direction.BID: [
                        backtest.Order(
                            order_time  =datetime(2024, 1, 1, 0, 0),
                            order_price =100.0,
                            spread      =0.003,
                            direction   =backtest.Direction.BID,
                            profit_price=99.0,
                            loss_price  =101.0,
                        ),
                        backtest.Order(
                            order_time  =datetime(2024, 1, 1, 0, 0),
                            order_price =100.0,
                            spread      =0.003,
                            direction   =backtest.Direction.BID,
                            profit_price=98.0,
                            loss_price  =102.0,
                        ),
                    ]
                },
                {
                    backtest.Direction.ASK: [], 
                    backtest.Direction.BID: [
                        backtest.Order(
                            order_time  =datetime(2024, 1, 1, 0, 0),
                            order_price =100.0,
                            spread      =0.003,
                            direction   =backtest.Direction.BID,
                            profit_price=98.0,
                            loss_price  =99.996,
                        ),
                    ]
                },
                [
                    backtest.Order(
                        order_time      =datetime(2024, 1, 1, 0, 0),
                        order_price     =100.0,
                        spread          =0.003,
                        direction       =backtest.Direction.BID,
                        profit_price    =99.0,
                        loss_price      =101.0,
                        settlement_time =datetime(2024, 1, 2, 0, 0),
                        settlement_price=101.0,
                        result          =-100.0
                    ),
                ]
            ],
            [
                [datetime(2024, 1, 2, 0, 0), 100.5, 101.1, 99.0, 100.5, 0.003],
                False, 
                {
                    backtest.Direction.ASK: [
                        backtest.Order(
                            order_time  =datetime(2024, 1, 1, 0, 0),
                            order_price =100.0,
                            spread      =0.003,
                            direction   =backtest.Direction.ASK,
                            profit_price=101.0,
                            loss_price  =99.0,
                        ),
                    ],
                    backtest.Direction.BID: [
                        backtest.Order(
                            order_time  =datetime(2024, 1, 1, 0, 0),
                            order_price =100.0,
                            spread      =0.003,
                            direction   =backtest.Direction.BID,
                            profit_price=98.0,
                            loss_price  =102.0,
                        ),
                    ]
                },
                {
                    backtest.Direction.ASK: [], 
                    backtest.Direction.BID: [
                        backtest.Order(
                            order_time  =datetime(2024, 1, 1, 0, 0),
                            order_price =100.0,
                            spread      =0.003,
                            direction   =backtest.Direction.BID,
                            profit_price=98.0,
                            loss_price  =100.0,
                        ),
                    ]
                },
                [
                    backtest.Order(
                        order_time      =datetime(2024, 1, 1, 0, 0),
                        order_price     =100.0,
                        spread          =0.003,
                        direction       =backtest.Direction.ASK,
                        profit_price    =101.0,
                        loss_price      =99.0,
                        settlement_time =datetime(2024, 1, 2, 0, 0),
                        settlement_price=99.0,
                        result          =-100.0
                    ),
                ]
            ],
            [
                [
                    datetime(2024, 1, 2, 0, 0), 
                    100.5,
                    100.997, 
                    98.996, 
                    100.5, 
                    0.003
                ],
                False, 
                {
                    backtest.Direction.ASK: [
                        backtest.Order(
                            order_time  =datetime(2024, 1, 1, 0, 0),
                            order_price =100.0,
                            spread      =0.003,
                            direction   =backtest.Direction.ASK,
                            profit_price=102.0,
                            loss_price  =98.0,
                        ),
                    ],
                    backtest.Direction.BID: [
                        backtest.Order(
                            order_time  =datetime(2024, 1, 1, 0, 0),
                            order_price =100.0,
                            spread      =0.003,
                            direction   =backtest.Direction.BID,
                            profit_price=99.0,
                            loss_price  =101.0,
                        ),
                    ]
                },
                {
                    backtest.Direction.ASK: [
                        backtest.Order(
                            order_time  =datetime(2024, 1, 1, 0, 0),
                            order_price =100.0,
                            spread      =0.003,
                            direction   =backtest.Direction.ASK,
                            profit_price=102.0,
                            loss_price  =100.0,
                        ),
                    ], 
                    backtest.Direction.BID: []
                },
                [
                    backtest.Order(
                        order_time      =datetime(2024, 1, 1, 0, 0),
                        order_price     =100.0,
                        spread          =0.003,
                        direction       =backtest.Direction.BID,
                        profit_price    =99.0,
                        loss_price      =101.0,
                        settlement_time =datetime(2024, 1, 2, 0, 0),
                        settlement_price=101.0,
                        result          =-100.0
                    ),
                ]
            ],
            # 利益確定
            [
                [datetime(2024, 1, 2, 0, 0), 100.5, 101.1, 99.5, 100.5, 0.003],
                False, 
                {
                    backtest.Direction.ASK: [
                        backtest.Order(
                            order_time  =datetime(2024, 1, 1, 0, 0),
                            order_price =100.0,
                            spread      =0.003,
                            direction   =backtest.Direction.ASK,
                            profit_price=101.0,
                            loss_price  =99.0,
                        ),
                    ],
                    backtest.Direction.BID: []
                },
                {backtest.Direction.ASK: [], backtest.Direction.BID: []},
                [
                    backtest.Order(
                        order_time      =datetime(2024, 1, 1, 0, 0),
                        order_price     =100.0,
                        spread          =0.003,
                        direction       =backtest.Direction.ASK,
                        profit_price    =101.0,
                        loss_price      =99.0,
                        settlement_time =datetime(2024, 1, 2, 0, 0),
                        settlement_price=101.1,
                        result          =100.0
                    ),
                ]
            ],
            [
                [
                    datetime(2024, 1, 2, 0, 0), 
                    100.5,
                    100.5, 
                    98.996, 
                    100.5, 
                    0.003
                ],
                False, 
                {
                    backtest.Direction.ASK: [],
                    backtest.Direction.BID: [
                        backtest.Order(
                            order_time  =datetime(2024, 1, 1, 0, 0),
                            order_price =100.0,
                            spread      =0.003,
                            direction   =backtest.Direction.BID,
                            profit_price=99.0,
                            loss_price  =101.0,
                        ),
                    ]
                },
                {backtest.Direction.ASK: [], backtest.Direction.BID: []},
                [
                    backtest.Order(
                        order_time      =datetime(2024, 1, 1, 0, 0),
                        order_price     =100.0,
                        spread          =0.003,
                        direction       =backtest.Direction.BID,
                        profit_price    =99.0,
                        loss_price      =101.0,
                        settlement_time =datetime(2024, 1, 2, 0, 0),
                        settlement_price=98.999,
                        result          =100.0
                    ),
                ]
            ],
            [
                [datetime(2024, 1, 2, 0, 0), 100.5, 101.1, 99.5, 100.5, 0.003],
                False, 
                {
                    backtest.Direction.ASK: [
                        backtest.Order(
                            order_time  =datetime(2024, 1, 1, 0, 0),
                            order_price =100.0,
                            spread      =0.003,
                            direction   =backtest.Direction.ASK,
                            profit_price=101.0,
                            loss_price  =99.0,
                        ),
                    ],
                    backtest.Direction.BID: [
                        backtest.Order(
                            order_time  =datetime(2024, 1, 1, 0, 0),
                            order_price =100.0,
                            spread      =0.003,
                            direction   =backtest.Direction.BID,
                            profit_price=98.0,
                            loss_price  =102.0,
                        ),
                    ]
                },
                {
                    backtest.Direction.ASK: [], 
                    backtest.Direction.BID: [
                        backtest.Order(
                            order_time  =datetime(2024, 1, 1, 0, 0),
                            order_price =100.0,
                            spread      =0.003,
                            direction   =backtest.Direction.BID,
                            profit_price=98.0,
                            loss_price  =100.5,
                        ),
                    ]
                },
                [
                    backtest.Order(
                        order_time      =datetime(2024, 1, 1, 0, 0),
                        order_price     =100.0,
                        spread          =0.003,
                        direction       =backtest.Direction.ASK,
                        profit_price    =101.0,
                        loss_price      =99.0,
                        settlement_time =datetime(2024, 1, 2, 0, 0),
                        settlement_price=101.1,
                        result          =100.0
                    ),
                ]
            ],
            [
                [
                    datetime(2024, 1, 2, 0, 0), 
                    100.5,
                    100.5, 
                    98.996, 
                    100.5, 
                    0.003
                ],
                False, 
                {
                    backtest.Direction.ASK: [
                        backtest.Order(
                            order_time  =datetime(2024, 1, 1, 0, 0),
                            order_price =100.0,
                            spread      =0.003,
                            direction   =backtest.Direction.ASK,
                            profit_price=102.0,
                            loss_price  =98.0,
                        ),
                    ],
                    backtest.Direction.BID: [
                        backtest.Order(
                            order_time  =datetime(2024, 1, 1, 0, 0),
                            order_price =100.0,
                            spread      =0.003,
                            direction   =backtest.Direction.BID,
                            profit_price=99.0,
                            loss_price  =101.0,
                        ),
                    ]
                },
                {
                    backtest.Direction.ASK: [
                        backtest.Order(
                            order_time  =datetime(2024, 1, 1, 0, 0),
                            order_price =100.0,
                            spread      =0.003,
                            direction   =backtest.Direction.ASK,
                            profit_price=102.0,
                            loss_price  =99.503,
                        ),
                    ], 
                    backtest.Direction.BID: []
                },
                [
                    backtest.Order(
                        order_time      =datetime(2024, 1, 1, 0, 0),
                        order_price     =100.0,
                        spread          =0.003,
                        direction       =backtest.Direction.BID,
                        profit_price    =99.0,
                        loss_price      =101.0,
                        settlement_time =datetime(2024, 1, 2, 0, 0),
                        settlement_price=98.999,
                        result          =100.0
                    ),
                ]
            ],
        ],
    )
    def test___settlement(
        self, 
        data: list, 
        all: bool, 
        orders: dict, 
        latest_orders: dict, 
        settlements: list):
        self.back.orders = orders

        self.back._Backtest__settlement(data, all)

        assert self.back.orders      == latest_orders
        assert self.back.settlements == settlements

    @pytest.mark.parametrize(
        'order, settlement, expect',
        [
            [
                backtest.Order(
                    order_time  =datetime(2024, 1, 1, 0, 0),
                    order_price =100.0,
                    spread      =0.003,
                    direction   =backtest.Direction.ASK,
                    profit_price=101.0,
                    loss_price  =99.0,
                ),
                backtest.Settlement(
                    open_price=100.5,
                    high_price=101.1,
                    low_price =99.0,
                    spread    =0.003
                ),
                [100.5, 50.0]
            ],
            [
                backtest.Order(
                    order_time  =datetime(2024, 1, 1, 0, 0),
                    order_price =100.0,
                    spread      =0.003,
                    direction   =backtest.Direction.ASK,
                    profit_price=101.0,
                    loss_price  =99.0,
                ),
                backtest.Settlement(
                    open_price=99.5,
                    high_price=101.1,
                    low_price =99.0,
                    spread    =0.003
                ),
                [99.5, -50.0]
            ],
            [
                backtest.Order(
                    order_time  =datetime(2024, 1, 1, 0, 0),
                    order_price =100.0,
                    spread      =0.003,
                    direction   =backtest.Direction.BID,
                    profit_price=99.0,
                    loss_price  =101.0,
                ),
                backtest.Settlement(
                    open_price=99.497,
                    high_price=100.997,
                    low_price =98.9,
                    spread    =0.003
                ),
                [99.5, 50.0]
            ],
            [
                backtest.Order(
                    order_time  =datetime(2024, 1, 1, 0, 0),
                    order_price =100.0,
                    spread      =0.003,
                    direction   =backtest.Direction.BID,
                    profit_price=99.0,
                    loss_price  =101.0,
                ),
                backtest.Settlement(
                    open_price=100.497,
                    high_price=100.997,
                    low_price =98.9,
                    spread    =0.003
                ),
                [100.5, -50.0]
            ],
        ]
    )
    def test___all_close(
        self, 
        order: backtest.Order, 
        settlement: backtest.Settlement, 
        expect: float):
        self.back._Backtest__all_close(order, settlement)

        assert order.settlement_price == expect[0]
        assert order.result           == expect[1]

    @pytest.mark.parametrize(
        'order, settlement, expect',
        [
            # 損失確定の対象
            [
                backtest.Order(
                    order_time  =datetime(2024, 1, 1, 0, 0),
                    order_price =100.0,
                    spread      =0.003,
                    direction   =backtest.Direction.ASK,
                    profit_price=101.0,
                    loss_price  =99.0,
                ),
                backtest.Settlement(
                    open_price=100.0,
                    high_price=101.1,
                    low_price =99.0,
                    spread    =0.003
                ),
                [99.0, -100.0]
            ],
            [
                backtest.Order(
                    order_time  =datetime(2024, 1, 1, 0, 0),
                    order_price =100.0,
                    spread      =0.003,
                    direction   =backtest.Direction.BID,
                    profit_price=99.0,
                    loss_price  =101.0,
                ),
                backtest.Settlement(
                    open_price=100.0,
                    high_price=100.997,
                    low_price =98.9,
                    spread    =0.003
                ),
                [101.0, -100.0]
            ],
            # 損失確定の対象(指定損失より大きい損失)
            [
                backtest.Order(
                    order_time  =datetime(2024, 1, 1, 0, 0),
                    order_price =100.0,
                    spread      =0.003,
                    direction   =backtest.Direction.ASK,
                    profit_price=101.0,
                    loss_price  =99.0,
                ),
                backtest.Settlement(
                    open_price=100.0,
                    high_price=101.1,
                    low_price =90.0,
                    spread    =0.003
                ),
                [90.0, -100.0]
            ],
            [
                backtest.Order(
                    order_time  =datetime(2024, 1, 1, 0, 0),
                    order_price =100.0,
                    spread      =0.003,
                    direction   =backtest.Direction.BID,
                    profit_price=99.0,
                    loss_price  =101.0,
                ),
                backtest.Settlement(
                    open_price=100.0,
                    high_price=109.997,
                    low_price =98.9,
                    spread    =0.003
                ),
                [110.0, -100.0]
            ],
            # 損失確定の対象外
            [
                backtest.Order(
                    order_time  =datetime(2024, 1, 1, 0, 0),
                    order_price =100.0,
                    spread      =0.003,
                    direction   =backtest.Direction.ASK,
                    profit_price=101.0,
                    loss_price  =99.0,
                ),
                backtest.Settlement(
                    open_price=99.5,
                    high_price=99.6,
                    low_price =99.4,
                    spread    =0.003
                ),
                [None, None]
            ],
            [
                backtest.Order(
                    order_time  =datetime(2024, 1, 1, 0, 0),
                    order_price =100.0,
                    spread      =0.003,
                    direction   =backtest.Direction.BID,
                    profit_price=99.0,
                    loss_price  =101.0,
                ),
                backtest.Settlement(
                    open_price=100.5,
                    high_price=100.6,
                    low_price =100.4,
                    spread    =0.003
                ),
                [None, None]
            ],
        ]
    )
    def test___loss_fixed(
        self, 
        order: backtest.Order, 
        settlement: backtest.Settlement, 
        expect: float):
        self.back._Backtest__loss_fixed(order, settlement)

        assert order.settlement_price == expect[0]
        assert order.result           == expect[1]
    
    @pytest.mark.parametrize(
        'order, settlement, expect',
        [
            # 利益確定の対象
            [
                backtest.Order(
                    order_time  =datetime(2024, 1, 1, 0, 0),
                    order_price =100.0,
                    spread      =0.003,
                    direction   =backtest.Direction.ASK,
                    profit_price=101.0,
                    loss_price  =99.0,
                ),
                backtest.Settlement(
                    open_price=100.0,
                    high_price=101.1,
                    low_price =99.9,
                    spread    =0.003
                ),
                [101.1, 100.0]
            ],
            [
                backtest.Order(
                    order_time  =datetime(2024, 1, 1, 0, 0),
                    order_price =100.0,
                    spread      =0.003,
                    direction   =backtest.Direction.BID,
                    profit_price=99.0,
                    loss_price  =101.0,
                ),
                backtest.Settlement(
                    open_price=100.0,
                    high_price=100.1,
                    low_price =98.996,
                    spread    =0.003
                ),
                [98.999, 100.0]
            ],
            # 利益確定の対象外
            [
                backtest.Order(
                    order_time  =datetime(2024, 1, 1, 0, 0),
                    order_price =100.0,
                    spread      =0.003,
                    direction   =backtest.Direction.ASK,
                    profit_price=101.0,
                    loss_price  =99.0,
                ),
                backtest.Settlement(
                    open_price=99.5,
                    high_price=99.6,
                    low_price =99.4,
                    spread    =0.003
                ),
                [None, None]
            ],
            [
                backtest.Order(
                    order_time  =datetime(2024, 1, 1, 0, 0),
                    order_price =100.0,
                    spread      =0.003,
                    direction   =backtest.Direction.BID,
                    profit_price=99.0,
                    loss_price  =101.0,
                ),
                backtest.Settlement(
                    open_price=100.5,
                    high_price=100.6,
                    low_price =100.4,
                    spread    =0.003
                ),
                [None, None]
            ],
        ]
    )
    def test___profit_fixed(
        self, 
        order: backtest.Order, 
        settlement: backtest.Settlement, 
        expect: float):
        self.back._Backtest__profit_fixed(order, settlement)

        assert order.settlement_price == expect[0]
        assert order.result           == expect[1]

    @pytest.mark.parametrize(
        'order, settlement, expect',
        [
            # トレールストップの対象
            [
                backtest.Order(
                    order_time  =datetime(2024, 1, 1, 0, 0),
                    order_price =100.0,
                    spread      =0.003,
                    direction   =backtest.Direction.ASK,
                    profit_price=101.0,
                    loss_price  =99.0,
                ),
                backtest.Settlement(
                    open_price=100.0,
                    high_price=100.1,
                    low_price =99.9,
                    spread    =0.003
                ),
                99.103
            ],
            [
                backtest.Order(
                    order_time  =datetime(2024, 1, 1, 0, 0),
                    order_price =100.0,
                    spread      =0.003,
                    direction   =backtest.Direction.BID,
                    profit_price=99.0,
                    loss_price  =101.0,
                ),
                backtest.Settlement(
                    open_price=100.0,
                    high_price=100.1,
                    low_price =99.9,
                    spread    =0.003
                ),
                100.9
            ],
            # トレールストップの対象外
            [
                backtest.Order(
                    order_time  =datetime(2024, 1, 1, 0, 0),
                    order_price =100.0,
                    spread      =0.003,
                    direction   =backtest.Direction.ASK,
                    profit_price=101.0,
                    loss_price  =99.0,
                ),
                backtest.Settlement(
                    open_price=99.5,
                    high_price=99.6,
                    low_price =99.4,
                    spread    =0.003
                ),
                99.0
            ],
            [
                backtest.Order(
                    order_time  =datetime(2024, 1, 1, 0, 0),
                    order_price =100.0,
                    spread      =0.003,
                    direction   =backtest.Direction.BID,
                    profit_price=99.0,
                    loss_price  =101.0,
                ),
                backtest.Settlement(
                    open_price=100.5,
                    high_price=100.6,
                    low_price =100.4,
                    spread    =0.003
                ),
                101.0
            ],
        ]
    )
    def test___calc_trail_stop(
        self, 
        order: backtest.Order, 
        settlement: backtest.Settlement, 
        expect: float):
        self.back._Backtest__calc_trail_stop(order, settlement)

        assert order.loss_price == expect


class TestPerformance:
    def setup_method(self, method):
        self.df               = pd.read_csv(StringIO(DATA))
        self.df['time_under'] = pd.to_datetime(self.df['time_under'])
        self.back             = backtest.Backtest(self.df, PARAMETER)
        self.back.run()
        self.performance      = backtest.Performance(self.back.result_df, PARAMETER)
    
    def test_performance(self):
        result = self.performance.performance()

        assert result == {
            'total_count': 2, 
            'profit_count': 2, 
            'loss_count': 0, 
            'profit_rate': 100.0, 
            'result': 200, 
            'profit': 100, 
            'loss': 100, 
            'detail': {
                'year': [
                    {
                        'year': 2024, 
                        'result': 200, 
                        'profit_count': 2, 
                        'loss_count': 0.0, 
                        'total_count': 2.0, 
                        'profit_rate': 100.0
                    }
                ], 
                'month': [
                    {
                        'year': 2024, 
                        'month': 1, 
                        'result': 200, 
                        'profit_count': 2, 
                        'loss_count': 0.0, 
                        'total_count': 2.0, 
                        'profit_rate': 100.0
                    }
                ], 
                'week': [
                    {
                        'year': 2024, 
                        'week': 1, 
                        'result': 200, 
                        'profit_count': 2, 
                        'loss_count': 0.0, 
                        'total_count': 2.0, 
                        'profit_rate': 100.0
                    }
                ], 
                'day': [
                    {
                        'year': 2024, 
                        'month': 1, 
                        'day': 1, 
                        'result': 200, 
                        'profit_count': 2, 
                        'loss_count': 0.0, 
                        'total_count': 2.0, 
                        'profit_rate': 100.0
                    }
                ]
            }
        }
