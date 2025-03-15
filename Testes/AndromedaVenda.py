import MetaTrader5 as mt5
import pandas as pd
import time
from datetime import datetime, timedelta



mt5.initialize() #inicializando o Meta Trade
#------------------------------------------------------------------
#                  Declarando os paramentro
#------------------------------------------------------------------

AtivoAoperar =       "WINJ25"
Contratos =             1.0
#Medias moveis
mediaMovelRapida =      17
mediaMovelLenta =       72

#Stops
StopGain = 600
StopLoss = 200

AcionarNovoStop = 100

novo_stop_gain = 200
novo_stop_loss =  100  #Novo valor de Stop Loss


Atualizar = 5         #de quanto em quantos minutos

#------------------------------------------------------------------
#                  Pegando os dados
#------------------------------------------------------------------
def pegando_dados(ativo_negociado, intervalo, data_de_inicio, data_fim):

        dados = mt5.copy_rates_range(ativo_negociado, intervalo, data_de_inicio, data_fim)
        dados = pd.DataFrame(dados)
        dados["time"] = pd.to_datetime(dados["time"], unit = "s")
        
        return dados
   
#------------------------------------------------------------------
#                  Definindo a estratégia
#------------------------------------------------------------------ 
def estrategia_trade(dados, ativo):

        dados["media_rapida"] = dados["close"].rolling(mediaMovelRapida).mean()
        dados["media_devagar"] = dados["close"].rolling(mediaMovelLenta).mean()

        #ultima_media_rapida = 40000.0
        ultima_media_rapida = dados["media_rapida"].iloc[-1]
        ultima_media_devagar = dados["media_devagar"].iloc[-1]
        
        somaDasMedias = ultima_media_rapida - ultima_media_devagar
        
        print(f"{somaDasMedias}")

        #print(f"Última Média Rápida: {ultima_media_rapida} | Última Média Devagar: {ultima_media_devagar}")

        posicao = mt5.positions_get(symbol = ativo)
#------------------------------------------------------------------
#                  VENDA
#------------------------------------------------------------------
        preco_de_tela = mt5.symbol_info(ativo).bid
        if ultima_media_rapida <= ultima_media_devagar and preco_de_tela <= ultima_media_rapida :

            if len(posicao) == 0:

                preco_de_tela = mt5.symbol_info(ativo).bid

                ordem_venda = {
                    "action": mt5.TRADE_ACTION_DEAL, #trade a mercado
                    "symbol": ativo,
                    "volume": Contratos,
                    "type": mt5.ORDER_TYPE_SELL,
                    "price": preco_de_tela,
                    "type_time": mt5.ORDER_TIME_DAY, #so manda a ordem se o mercado tiver aberto
                    "type_filling": mt5.ORDER_FILLING_RETURN,
                }
                
                mt5.order_send(ordem_venda)
                
                print(f"VENDEU O ATIVO A: {preco_atual}")
        
#------------------------------------------------------------------
#                  COMPRA   
#------------------------------------------------------------------
        preco_de_tela = mt5.symbol_info(ativo).ask
        if ultima_media_rapida > ultima_media_devagar or preco_de_tela > ultima_media_rapida :

            if len(posicao) != 0:

                preco_de_tela = mt5.symbol_info(ativo).ask

                ordem_compra = {
                    "action": mt5.TRADE_ACTION_DEAL, #trade a mercado
                    "symbol": ativo,
                    "volume": Contratos,
                    "type": mt5.ORDER_TYPE_BUY,
                    "price": preco_de_tela,
                    "type_time": mt5.ORDER_TIME_DAY, #so manda a ordem se o mercado tiver aberto
                    "type_filling": mt5.ORDER_FILLING_RETURN,    
                }
                
                mt5.order_send(ordem_compra)

                print(f"COMPROU O ATIVO A: {preco_de_tela}")


#------------------------------------------------------------------
#                   Modificando stoploss
#------------------------------------------------------------------
def modificar_stop(ativo, novo_stop_loss,novo_stop_gain):
        #Obter posições abertas:
        posicao = mt5.positions_get(symbol=ativo) 
        if posicao and len(posicao) > 0: #garantindo que tem um posição aberta
            #Obter Informações da Posição       
            ticket = posicao[0].ticket 
            preco_de_tela = mt5.symbol_info(ativo).bid 
            sl_atual = posicao[0].sl #obtendo valor de stoploss
            tp_atual = posicao[0].tp #obtendo valor de stopgain   
            
            #Verificar se o Novo Stop é Diferente do Atual
            if sl_atual != preco_de_tela - novo_stop_loss or tp_atual != preco_de_tela:
                #Dicionário:
                ordem_modificacao = {                        
                    "action": mt5.TRADE_ACTION_SLTP, 
                    "symbol": ativo,
                    "position": ticket, 
                    "sl": preco_de_tela + novo_stop_loss, 
                    "tp": preco_de_tela - novo_stop_gain,
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": mt5.ORDER_FILLING_RETURN
                    }                 
                resultado = mt5.order_send(ordem_modificacao)
                print(f"Resultado da modificação do Stop Loss")
                if resultado.retcode == mt5.TRADE_RETCODE_DONE:
                    print(f"Stop Loss e modificado com sucesso!") 
                else: 
                    print(f"Erro ao modificar Stop Loss: {resultado.comment}") 
            else: 
                print("O novo Stop Loss é igual ao Stop Loss atual. Nenhuma mudança feita.") 
        else: 
            print("Nenhuma posição aberta para modificar o Stop Loss.")

#------------------------------------------------------------------
#                  Lucro diário
#------------------------------------------------------------------

def obter_lucro_diario(): 

# Obter todas as negociações fechadas de hoje 
    data_de_hoje = datetime.now().date() 
    data_inicial = datetime(data_de_hoje.year, 
    data_de_hoje.month, data_de_hoje.day, 0, 0) 
    data_final = datetime(data_de_hoje.year, 
    data_de_hoje.month, data_de_hoje.day, 23, 59, 59) 

    historico_negociacoes = mt5.history_deals_get(data_inicial, data_final)
    
    if historico_negociacoes is None: 
        print("Nenhuma negociação fechada hoje.") 
        return 
    
    # Converter o histórico para um DataFrame do Pandas 
    df_negociacoes = pd.DataFrame(list(historico_negociacoes), columns=historico_negociacoes[0]._asdict().keys())
    
    # Calcular o lucro total das negociações de hoje
    lucro_total = df_negociacoes['profit'].sum() 

    print(f"Lucro total de hoje: {lucro_total:.2f}")    
    if lucro_total >= 500:
                print("encerrando metatrade por gain")
                time.sleep(5)
                mt5.shutdown()
                             
    if lucro_total <= -300:
            print("encerrando metatrade por loss")
            time.sleep(5)
            mt5.shutdown()
            


#------------------------------------------------------------------
#           Loop Principal para Executar a Estratégia
#------------------------------------------------------------------

while True:
    ticker = AtivoAoperar
    intervalo = mt5.TIMEFRAME_M5
    data_final = datetime.today()
    data_inicial = datetime.today() - timedelta(days = 3)
    mt5.symbol_select(ticker)
   

    preco_inicial = mt5.symbol_info(ticker).ask 
    while True: 
        preco_atual_do_ativo =   mt5.symbol_info(AtivoAoperar).ask
        preco_atual = mt5.symbol_info(ticker).ask 
        print(f"Preço Atual: {preco_atual}") 
        dados_atualizados = pegando_dados(ticker, intervalo, data_inicial, data_final)
        estrategia_trade(dados_atualizados, ticker)
        obter_lucro_diario()
        hora_agora = datetime.now().strftime("%H:%M")

        print(f"Hora atual: {hora_agora}")
        print("Robo de venda")
        
        
        #Monitora o preço e ajusta Stop Loss após subir 100 pontos 
        if preco_atual >= preco_inicial - AcionarNovoStop: 
            modificar_stop(ticker, novo_stop_loss,novo_stop_gain) 
            preco_inicial = preco_atual # Atualizando o preço inicial após reajustar o Stop Loss 
        
        time.sleep(60*Atualizar)

























