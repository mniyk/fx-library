"""ユーティリティ関数のモジュール
"""


def direction_by_value_range(data, columns, **kwargs):
    """売買方向を値の範囲で決定
    
    **kwargsには、以下のような辞書を想定
    {
        'ranges': {
            'rci_12': {'ask': [80, 100], 'bid': [-80, -100]},
            'rci_12_shift_diff': {'ask': [0, 100], 'bid': [0, -100]}},
        'backtest': False}
    """
    log_direcctions = []
    directions = []

    for k, v in kwargs['ranges'].items():
        direction = 0
        index = columns.get_loc(k)
        val = data[index]

        if v['ask'][0] <= val < v['ask'][1]:
            direction = 1
                
        if v['bid'][0] >= val > v['bid'][1]:
            direction = -1

        directions.append(direction)
        
        log_direcctions.append({
            k: {'val': val, 'ranges': v, 'direction': direction}})

    result = 0

    if abs(sum(directions)) == len(directions):
        if sum(directions) > 0:
            result = 1
        elif sum(directions) < 0:
            result = -1

    if kwargs['backtest']:
        return result
    
    return result, log_direcctions
