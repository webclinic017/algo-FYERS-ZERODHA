

# p1 ,p2 stands for the order of  sequence of postions to be taken under certain strategy

def OrderParam(strategy_name,signal):
    OrderPar  = {}
    if strategy_name=='TREND_EMA':
        # directional option selling strategy when upside movement is expected
        if signal == 1:
            p1 = {'opt':'CE', 'step':-3,'transtype':'BUY','Qty':50}
            OrderPar = {'p1':p1}

        elif signal == -1:
            p1 = {'opt': 'PE', 'step': 3, 'transtype': 'BUY', 'Qty': 50}
            OrderPar = {'p1': p1}

    elif strategy_name == 'SharpeRev':
        if signal == 1:
            p1 = {'opt': 'CE', 'step': -3, 'transtype': 'BUY', 'Qty': 50}
            OrderPar = {'p1': p1}
        elif signal == -1:
            p1 = {'opt': 'PE', 'step': 3, 'transtype': 'BUY', 'Qty': 50}
            OrderPar = {'p1': p1}

    elif strategy_name == 'ZSCORE':
        if signal == 1:
            p1 = {'opt': 'CE', 'step': -3, 'transtype': 'BUY', 'Qty': 50}
            OrderPar = {'p1': p1}
        elif signal == -1:
            p1 = {'opt': 'PE', 'step': 3, 'transtype': 'BUY', 'Qty': 50}
            OrderPar = {'p1': p1}


    return OrderPar
