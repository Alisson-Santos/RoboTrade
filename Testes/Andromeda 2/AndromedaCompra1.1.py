import backtrader as bt
import pandas as pd
import MetaTrader5 as mt5
from datetime import datetime, timedelta

# Configuração do MetaTrader5
mt5.initialize()

# Definição da estratégia no Backtrader
class AndromedaStrategy(bt.Strategy):
    params = (
        ('media_rapida', 17),
        ('media_lenta', 72),
        ('stop_gain', 600),
        ('stop_loss', 200),
    )

    def __init__(self):
        # Indicadores de média móvel
        self.media_rapida = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.media_rapida)
        self.media_lenta = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.media_lenta)

    def next(self):
        # Lógica de compra
        if not self.position:
            if self.media_rapida > self.media_lenta and self.data.close > self.media_rapida:
                self.buy()
                self.stop_loss = self.data.close - self.params.stop_loss
                self.take_profit = self.data.close + self.params.stop_gain

        # Lógica de venda
        elif self.position:
            if self.media_rapida <= self.media_lenta or self.data.close <= self.media_lenta or self.data.close <= self.media_rapida:
                self.sell()

        # Ajuste do stop loss
        if self.position and self.data.close >= self.data.close + 100:
            self.stop_loss = self.data.close - 100
            self.take_profit = self.data.close + 200

# Função para obter dados históricos do MetaTrader5
def get_historical_data(symbol, timeframe, start_date, end_date):
    mt5.symbol_select(symbol)
    rates = mt5.copy_rates_range(symbol, timeframe, start_date, end_date)
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)
    return df

# Configuração do backtest
if __name__ == '__main__':
    cerebro = bt.Cerebro()

    # Adicionando a estratégia
    cerebro.addstrategy(AndromedaStrategy)

    # Obtendo dados históricos
    symbol = "WINJ25"
    timeframe = mt5.TIMEFRAME_M5
    end_date = datetime.now()
    start_date = end_date - timedelta(days=3)
    data = get_historical_data(symbol, timeframe, start_date, end_date)

    # Convertendo os dados para o formato do Backtrader
    data_feed = bt.feeds.PandasData(dataname=data)
    cerebro.adddata(data_feed)

    # Configuração do capital inicial
    cerebro.broker.set_cash(10000)

    # Executando o backtest
    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())
    cerebro.run()
    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())

    # Plotando os resultados
    cerebro.plot()