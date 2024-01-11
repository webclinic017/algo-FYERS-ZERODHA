def OrderParam(strategy_name,signal):
    OrderPar  = {}
    if strategy_name=='TREND_EMA':
        # directional option selling strategy when upside movement is expected
        if signal == 1:
            p1 = {'opt':'CE', 'step':8,'transtype':'BUY','Qty':50}
            p2 = {'opt':'CE', 'step':3,'transtype':'SELL','Qty':50}
            OrderPar = {'p1':p1, 'p2':p2}

        elif signal == -1:
            p1 = {'opt': 'PE', 'step': -8, 'transtype': 'BUY', 'Qty': 50}
            p2 = {'opt': 'PE', 'step': -3, 'transtype': 'SELL', 'Qty': 50}
            OrderPar = {'p1':p1, 'p2':p2}


    elif strategy_name == 'SharpeRev':
        if signal == 1:
            p1 = {'opt': 'CE', 'step': 8, 'transtype': 'BUY', 'Qty': 50}
            p2 = {'opt': 'CE', 'step': 3, 'transtype': 'SELL', 'Qty': 50}
            OrderPar = {'p1': p1, 'p2': p2}

        elif signal == -1:
            p1 = {'opt': 'PE', 'step': -8, 'transtype': 'BUY', 'Qty': 50}
            p2 = {'opt': 'PE', 'step': -3, 'transtype': 'SELL', 'Qty': 50}
            OrderPar = {'p1': p1, 'p2': p2}

    elif strategy_name == 'MOM_BURST':
        if signal == 1:
            p1 = {'opt': 'CE', 'step': 8, 'transtype': 'BUY', 'Qty': 50}
            p2 = {'opt': 'CE', 'step': 3, 'transtype': 'SELL', 'Qty': 50}
            OrderPar = {'p1': p1, 'p2': p2}

        elif signal == -1:
            p1 = {'opt': 'PE', 'step': -8, 'transtype': 'BUY', 'Qty': 50}
            p2 = {'opt': 'PE', 'step': -3, 'transtype': 'SELL', 'Qty': 50}
            OrderPar = {'p1': p1, 'p2': p2}

    return OrderPar
