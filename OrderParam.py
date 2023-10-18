

# p1 ,p2 stands for the order of  sequence of postions to be taken under certain strategy

def OrderParam(strategy_name ,signal):
    OrderPar  = None
    if strategy_name=='3EMA':
        # directional option selling strategy when upside movement is expected
        if signal==1:
            p1 ={'opt':'CE', 'step':0,'transtype':'BUY','Qty':50}
            p2 ={'opt': 'PE', 'step': 0, 'transtype': 'SELL','Qty': 50}
            OrderPar = {'p1':p1,'p2':p2}
        elif signal==-1:
            p1 = {'opt': 'CE', 'step': 0, 'transtype': 'SELL', 'Qty': 50}
            p2 = {'opt': 'PE', 'step': 0, 'transtype': 'BUY', 'Qty': 50}
            OrderPar = {'p1': p2, 'p2': p1}

    elif strategy_name=='RSI':
        pass


    return OrderPar