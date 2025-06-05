import MetaTrader5 as mt5
import pandas as pd
import time
import tkinter as tk
from datetime import datetime, timedelta
from threading import Thread

# Inicializando o MetaTrader 5
if not mt5.initialize():
    print("Erro ao inicializar o MetaTrader 5. Verifique a instalação e o terminal.")
    exit()

# Variável global para controlar o estado da estratégia (iniciada ou pausada)
estrategia_ativa = False
tipo_posicao = None # Inicializa como None para indicar que não há posição aberta
preco_inicial = 0.0 # Usado para o trailing stop, será atualizado

#------------------------------------------------------------------
#                  Interface Gráfica
#------------------------------------------------------------------

# Criando a janela principal
root = tk.Tk()
root.title("Robo Trader - Andromeda 3.0")

# Função para criar e exibir os parâmetros na interface gráfica
def criar_interface_parametros():
    # Frame para organizar os parâmetros
    frame_parametros = tk.Frame(root)
    frame_parametros.pack(padx=10, pady=10)

    # Título da seção de parâmetros
    tk.Label(frame_parametros, text="Parâmetros de Operação", font=("Arial", 14, "bold")).grid(row=0, column=0, columnspan=2, pady=5)

    # Dicionário para armazenar os campos de entrada
    global entries
    entries = {}

    # Parâmetros e seus valores padrão
    parametros = {
        "Ativo a Operar": "WINM25",
        "Contratos": 1.0,
        "Média Móvel Rápida": 17,
        "Média Móvel Lenta": 72,
        "Stop Gain (Operação em pontos)": 500, # Corrigido para indicar que é em pontos
        "Stop Loss (Operação em pontos)": 200, # Corrigido para indicar que é em pontos
        "Stop Gain (Dia)": 500,
        "Stop Loss (Dia)": -100,
        "Acionar Novo Stop (pontos)": 100, # Corrigido para indicar que é em pontos
        "Novo Stop Gain (pontos)": 150, # Corrigido para indicar que é em pontos
        "Novo Stop Loss (pontos)": 100, # Corrigido para indicar que é em pontos
        "Atualizar (minutos)": 1 # Reduzido para 1 minuto para testes mais rápidos
    }

    # Adicionando os parâmetros à interface
    for i, (chave, valor) in enumerate(parametros.items()):
        tk.Label(frame_parametros, text=f"{chave}:", font=("Arial", 10)).grid(row=i+1, column=0, sticky="w", padx=5, pady=2)
        entry = tk.Entry(frame_parametros, font=("Arial", 10))
        entry.insert(0, str(valor))
        entry.grid(row=i+1, column=1, sticky="w", padx=5, pady=2)
        entries[chave] = entry

# Função para obter os parâmetros inseridos pelo usuário
def obter_parametros():
    global AtivoAoperar, Contratos, mediaMovelRapida, mediaMovelLenta, StopGain, StopLoss, StopGainDia, StopLossDia, AcionarNovoStop, novo_stop_gain, novo_stop_loss, Atualizar
    AtivoAoperar = entries["Ativo a Operar"].get()
    Contratos = float(entries["Contratos"].get())
    mediaMovelRapida = int(entries["Média Móvel Rápida"].get())
    mediaMovelLenta = int(entries["Média Móvel Lenta"].get())
    StopGain = float(entries["Stop Gain (Operação em pontos)"].get())
    StopLoss = float(entries["Stop Loss (Operação em pontos)"].get())
    StopGainDia = float(entries["Stop Gain (Dia)"].get())
    StopLossDia = float(entries["Stop Loss (Dia)"].get())
    AcionarNovoStop = float(entries["Acionar Novo Stop (pontos)"].get())
    novo_stop_gain = float(entries["Novo Stop Gain (pontos)"].get())
    novo_stop_loss = float(entries["Novo Stop Loss (pontos)"].get())
    Atualizar = int(entries["Atualizar (minutos)"].get())

# Função para atualizar o widget de texto com as mensagens
def atualizar_texto(mensagem):
    texto_log.insert(tk.END, mensagem + "\n")  # Adiciona a mensagem ao final do widget
    texto_log.see(tk.END)  # Rola para o final do texto
    root.update_idletasks()  # Atualiza a interface gráfica

#------------------------------------------------------------------
#                  Pegando os dados (Corrigido)
#------------------------------------------------------------------
def pegando_dados(ativo_negociado, intervalo, num_candles):
    """
    Obtém os últimos 'num_candles' do ativo e intervalo especificados.
    """
    rates = mt5.copy_rates_from_pos(ativo_negociado, intervalo, 0, num_candles)
    if rates is None:
        atualizar_texto(f"Erro ao obter dados para {ativo_negociado}. Retcode: {mt5.last_error()}")
        return pd.DataFrame() # Retorna DataFrame vazio em caso de erro

    dados = pd.DataFrame(rates)
    dados["time"] = pd.to_datetime(dados["time"], unit="s")
    return dados

#------------------------------------------------------------------
#                  Função de Compra (Corrigido)
#------------------------------------------------------------------
def comprar(ativo):
    global tipo_posicao, Contratos, StopLoss, StopGain
    symbol_info = mt5.symbol_info(ativo)
    if symbol_info is None:
        atualizar_texto(f"Erro: Ativo {ativo} não encontrado.")
        return False
    
    point = symbol_info.point
    preco_de_tela = symbol_info.ask

    # Calcula SL e TP em preço, usando o 'point' do ativo
    sl_price = preco_de_tela - (StopLoss * point)
    tp_price = preco_de_tela + (StopGain * point)

    ordem_compra = {
        "action": mt5.TRADE_ACTION_DEAL,  # trade a mercado
        "symbol": ativo,
        "volume": Contratos,
        "type": mt5.ORDER_TYPE_BUY,
        "price": preco_de_tela,
        "sl": sl_price,
        "tp": tp_price,
        "deviation": 10, # Desvio máximo permitido em pontos
        "type_time": mt5.ORDER_TIME_GTC,  # Good Till Cancel - válida até ser cancelada
        "type_filling": mt5.ORDER_FILLING_RETURN, # Preencher ou cancelar
    }

    resultado = mt5.order_send(ordem_compra)
    if resultado.retcode == mt5.TRADE_RETCODE_DONE:
        atualizar_texto(f">>>>> Comprou {Contratos} de {ativo} a: {preco_de_tela:.2f} (SL: {sl_price:.2f}, TP: {tp_price:.2f})")
        # A atualização de tipo_posicao será feita pela função que verifica as posições abertas
        return True
    else:
        atualizar_texto(f"Erro ao comprar: {resultado.comment} (Retcode: {resultado.retcode})")
        return False

#------------------------------------------------------------------
#                  Função de Venda (Corrigido)
#------------------------------------------------------------------
def vender(ativo):
    global tipo_posicao, Contratos, StopLoss, StopGain
    symbol_info = mt5.symbol_info(ativo)
    if symbol_info is None:
        atualizar_texto(f"Erro: Ativo {ativo} não encontrado.")
        return False

    point = symbol_info.point
    preco_de_tela = symbol_info.bid

    # Calcula SL e TP em preço, usando o 'point' do ativo
    sl_price = preco_de_tela + (StopLoss * point)
    tp_price = preco_de_tela - (StopGain * point)

    ordem_venda = {
        "action": mt5.TRADE_ACTION_DEAL,  # trade a mercado
        "symbol": ativo,
        "volume": Contratos,
        "type": mt5.ORDER_TYPE_SELL,
        "price": preco_de_tela,
        "sl": sl_price,
        "tp": tp_price,
        "deviation": 10, # Desvio máximo permitido em pontos
        "type_time": mt5.ORDER_TIME_GTC,  # Good Till Cancel - válida até ser cancelada
        "type_filling": mt5.ORDER_FILLING_RETURN, # Preencher ou cancelar
    }

    resultado = mt5.order_send(ordem_venda)
    if resultado.retcode == mt5.TRADE_RETCODE_DONE:
        atualizar_texto(f">>>>> Vendeu {Contratos} de {ativo} a: {preco_de_tela:.2f} (SL: {sl_price:.2f}, TP: {tp_price:.2f})")
        # A atualização de tipo_posicao será feita pela função que verifica as posições abertas
        return True
    else:
        atualizar_texto(f"Erro ao vender: {resultado.comment} (Retcode: {resultado.retcode})")
        return False

# Função de fechamento de posição (Melhorado)
def fechar_posicao_mt5(ativo):
    """
    Função para fechar todas as posições abertas para um determinado ativo no MT5.
    """
    positions = mt5.positions_get(symbol=ativo)
    if positions is None:
        atualizar_texto(f"Erro ao obter posições para fechar em {ativo}. Retcode: {mt5.last_error()}")
        return False

    if not positions:
        atualizar_texto(f"Nenhuma posição aberta para fechar em {ativo}.")
        return False

    for pos in positions:
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": ativo,
            "volume": pos.volume,
            "type": mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY, # Inverte o tipo para fechar
            "position": pos.ticket,
            "price": mt5.symbol_info(ativo).bid if pos.type == mt5.ORDER_TYPE_BUY else mt5.symbol_info(ativo).ask,
            "deviation": 10, # Desvio permitido
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_RETURN,
        }
        result = mt5.order_send(request)
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            atualizar_texto(f"Posição {pos.ticket} em {ativo} de {pos.volume} fechada com sucesso. (Profit: {result.deal_profit:.2f})")
            return True
        else:
            atualizar_texto(f"Erro ao fechar posição {pos.ticket}: {result.comment} (Retcode: {result.retcode})")
            return False
    return False # Retorna False se não conseguiu fechar nenhuma posição

#------------------------------------------------------------------
#                 Estégia Estrela Cadente
#------------------------------------------------------------------
def estrategia_estrela_cadente(dados, ativo):
    """
    Função que verifica se há um padrão de estrela cadente após uma tendência de alta
    e executa uma ordem de venda se o padrão for identificado.
    Encerra qualquer posição anterior antes de vender.
    """
    global tipo_posicao

    # Verifica se há dados suficientes para análise (pelo menos 3 candles para tendência)
    if len(dados) < 3:
        atualizar_texto("Dados insuficientes para identificar padrão de estrela cadente.")
        return

    # Obtém os últimos 3 candles
    candle_atual = dados.iloc[-1]
    candle_anterior = dados.iloc[-2]
    candle_antecessor = dados.iloc[-3]

    # Verifica a tendência de alta (pode ser mais robusta, mas para exemplo, simples fechamentos crescentes)
    tendencia_alta = (
        candle_antecessor["close"] < candle_anterior["close"] and
        candle_anterior["close"] < candle_atual["close"]
    )

    # Verifica o padrão de estrela cadente no candle atual
    corpo_candle = abs(candle_atual["close"] - candle_atual["open"])
    sombra_superior = candle_atual["high"] - max(candle_atual["open"], candle_atual["close"])
    sombra_inferior = min(candle_atual["open"], candle_atual["close"]) - candle_atual["low"]

    # Condições para identificar uma estrela cadente
    # Considerar um corpo pequeno e sombra superior longa
    estrela_cadente = (
        corpo_candle < (candle_atual["high"] - candle_atual["low"]) * 0.3 and  # Corpo pequeno (menos de 30% do range)
        sombra_superior >= 2 * corpo_candle and  # Sombra superior longa (pelo menos 2x o corpo)
        sombra_inferior < 0.5 * corpo_candle  # Sombra inferior muito pequena
    )

    # Se houver tendência de alta e padrão de estrela cadente
    if tendencia_alta and estrela_cadente:
        atualizar_texto("Padrão de Estrela Cadente detectado.")
        # Verifica se há uma posição aberta e fecha se for comprada
        if tipo_posicao == "comprado":
            atualizar_texto("Fechando posição comprada existente antes de vender.")
            fechar_posicao_mt5(ativo)
            # A atualização de tipo_posicao para None será feita pela função que verifica as posições abertas

        # Executa a ordem de venda se não houver posição ou se for vendida
        if tipo_posicao != "vendido":
            if vender(ativo):
                atualizar_texto("Vendido por Estrela Cadente.")
        else:
            atualizar_texto("Ativo já está vendido, não vendendo novamente por Estrela Cadente.")
    else:
        atualizar_texto("Sem Estrela Cadente.")

#------------------------------------------------------------------
#                 Estégia Martelo
#------------------------------------------------------------------

def estrategia_martelo(dados, ativo):
    """
    Função que verifica se há um padrão de martelo após uma tendência de baixa
    e executa uma ordem de compra se o padrão for identificado.
    Encerra qualquer posição anterior antes de comprar.
    """
    global tipo_posicao

    # Verifica se há dados suficientes para análise
    if len(dados) < 3:
        atualizar_texto("Dados insuficientes para identificar padrão de martelo.")
        return

    # Obtém os últimos 3 candles
    candle_atual = dados.iloc[-1]
    candle_anterior = dados.iloc[-2]
    candle_antecessor = dados.iloc[-3]

    # Verifica a tendência de baixa (pode ser mais robusta)
    tendencia_baixa = (
        candle_antecessor["close"] > candle_anterior["close"] and
        candle_anterior["close"] > candle_atual["close"]
    )

    # Verifica o padrão de martelo no candle atual
    corpo_candle = abs(candle_atual["close"] - candle_atual["open"])
    sombra_inferior = min(candle_atual["open"], candle_atual["close"]) - candle_atual["low"]
    sombra_superior = candle_atual["high"] - max(candle_atual["open"], candle_atual["close"])

    # Condições para identificar um martelo
    # Corpo pequeno, sombra inferior longa e sombra superior muito pequena
    martelo = (
        corpo_candle < (candle_atual["high"] - candle_atual["low"]) * 0.3 and  # Corpo pequeno
        sombra_inferior >= 2 * corpo_candle and  # Sombra inferior longa
        sombra_superior < 0.5 * corpo_candle  # Sombra superior muito pequena
    )

    # Se houver tendência de baixa e padrão de martelo
    if tendencia_baixa and martelo:
        atualizar_texto("Padrão de Martelo detectado.")
        # Verifica se há uma posição aberta e fecha se for vendida
        if tipo_posicao == "vendido":
            atualizar_texto("Fechando posição vendida existente antes de comprar.")
            fechar_posicao_mt5(ativo)
            # A atualização de tipo_posicao para None será feita pela função que verifica as posições abertas

        # Executa a ordem de compra se não houver posição ou se for comprada
        if tipo_posicao != "comprado":
            if comprar(ativo):
                atualizar_texto("Comprado por Martelo.")
        else:
            atualizar_texto("Ativo já está comprado, não comprando novamente por Martelo.")
    else:
        atualizar_texto("Sem Martelo.")

#------------------------------------------------------------------
#                  Estratégia de Médias Móveis
#------------------------------------------------------------------
def estrategia_medias_moveis(dados, ativo):
    global tipo_posicao

    # Certifica-se de que há dados suficientes para as médias móveis
    if len(dados) < mediaMovelLenta:
        atualizar_texto(f"Dados insuficientes para médias móveis. Necessário pelo menos {mediaMovelLenta} candles.")
        return

    dados["media_rapida"] = dados["close"].rolling(mediaMovelRapida).mean()
    dados["media_devagar"] = dados["close"].rolling(mediaMovelLenta).mean()

    ultima_media_rapida = dados["media_rapida"].iloc[-1]
    ultima_media_devagar = dados["media_devagar"].iloc[-1]

    # **ATUALIZAÇÃO CRÍTICA**: Verifica as posições abertas no MT5 para garantir que o tipo_posicao global está correto
    posicoes_abertas_mt5 = mt5.positions_get(symbol=ativo)
    if posicoes_abertas_mt5 is None:
        atualizar_texto(f"Erro ao obter posições abertas: {mt5.last_error()}")
        return # Sai da função se houver erro

    if len(posicoes_abertas_mt5) > 0:
        pos = posicoes_abertas_mt5[0] # Pega a primeira posição (assumindo apenas uma por ativo)
        if pos.type == mt5.ORDER_TYPE_BUY:
            tipo_posicao = "comprado"
        elif pos.type == mt5.ORDER_TYPE_SELL:
            tipo_posicao = "vendido"
        atualizar_texto(f"Posição atual (MT5): {tipo_posicao} - Volume: {pos.volume} - Preço Abertura: {pos.price_open:.2f}")
    else:
        if tipo_posicao is not None: # Se a posição interna estava setada, mas não há no MT5, reseta
            atualizar_texto("Nenhuma posição aberta no MT5. Resetando tipo_posicao.")
        tipo_posicao = None  # Nenhuma posição aberta


    #------------------------------------------------------------------
    #                  COMPRAR
    #------------------------------------------------------------------
    preco_ask = mt5.symbol_info(ativo).ask
    if preco_ask == 0.0: # Verifica se o preço é válido
        atualizar_texto(f"Erro ao obter preço ASK para {ativo}.")
        return

    if ultima_media_rapida > ultima_media_devagar and preco_ask > ultima_media_rapida:
        if tipo_posicao != "comprado":  # Só compra se não estiver comprado
            if tipo_posicao == "vendido": # Se estiver vendido, fecha antes de comprar
                atualizar_texto("Fechando posição vendida antes de comprar por média móvel.")
                fechar_posicao_mt5(ativo)
                time.sleep(1) # Pequena pausa para a ordem de fechamento processar
            if comprar(ativo):
                atualizar_texto("Comprado pela média.")
        else:
            atualizar_texto("Ativo já está comprado pela média.")

    #------------------------------------------------------------------
    #                  VENDER
    #------------------------------------------------------------------
    preco_bid = mt5.symbol_info(ativo).bid
    if preco_bid == 0.0: # Verifica se o preço é válido
        atualizar_texto(f"Erro ao obter preço BID para {ativo}.")
        return

    if ultima_media_rapida <= ultima_media_devagar and preco_bid <= ultima_media_rapida:
        if tipo_posicao != "vendido":  # Só vende se não estiver vendido
            if tipo_posicao == "comprado": # Se estiver comprado, fecha antes de vender
                atualizar_texto("Fechando posição comprada antes de vender por média móvel.")
                fechar_posicao_mt5(ativo)
                time.sleep(1) # Pequena pausa para a ordem de fechamento processar
            if vender(ativo):
                atualizar_texto("Vendido pela média.")
        else:
            atualizar_texto("Ativo já está vendido pela média.")

#------------------------------------------------------------------
#                   Modificando stoploss (Corrigido)
#------------------------------------------------------------------
def modificar_stop(ativo, novo_stop_loss_pontos, novo_stop_gain_pontos):
    symbol_info = mt5.symbol_info(ativo)
    if symbol_info is None:
        atualizar_texto(f"Erro: Ativo {ativo} não encontrado para modificar stop.")
        return False
    point = symbol_info.point

    posicao = mt5.positions_get(symbol=ativo)
    if posicao and len(posicao) > 0:  # garantindo que tem uma posição aberta
        pos = posicao[0] # Pega a primeira posição
        ticket = pos.ticket
        
        # Obtém o preço atual de acordo com o tipo de posição para o cálculo do novo stop
        preco_atual_para_stop = mt5.symbol_info_tick(ativo).bid if pos.type == mt5.ORDER_TYPE_SELL else mt5.symbol_info_tick(ativo).ask
        if preco_atual_para_stop == 0.0:
            atualizar_texto(f"Erro ao obter preço atual para modificar stop em {ativo}.")
            return False

        sl_atual = pos.sl  # obtendo valor de stoploss
        tp_atual = pos.tp  # obtendo valor de stopgain

        novo_sl_preco = 0.0
        novo_tp_preco = 0.0

        if pos.type == mt5.ORDER_TYPE_BUY:  # Se estiver comprado
            novo_sl_preco = preco_atual_para_stop - (novo_stop_loss_pontos * point)
            novo_tp_preco = preco_atual_para_stop + (novo_stop_gain_pontos * point)
        
        elif pos.type == mt5.ORDER_TYPE_SELL:  # Se estiver vendido
            novo_sl_preco = preco_atual_para_stop + (novo_stop_loss_pontos * point)
            novo_tp_preco = preco_atual_para_stop - (novo_stop_gain_pontos * point)
        
        # Verificar se o Novo Stop é Diferente do Atual para evitar ordens desnecessárias
        # Comparação com uma pequena tolerância devido a imprecisões de ponto flutuante
        if abs(sl_atual - novo_sl_preco) > point/2 or abs(tp_atual - novo_tp_preco) > point/2:
            ordem_modificacao = {
                "action": mt5.TRADE_ACTION_SLTP,
                "symbol": ativo,
                "position": ticket,
                "sl": novo_sl_preco,
                "tp": novo_tp_preco,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_RETURN,
            }
            resultado = mt5.order_send(ordem_modificacao)
            if resultado.retcode == mt5.TRADE_RETCODE_DONE:
                atualizar_texto(f"Stop Loss e Take Profit modificados com sucesso! SL: {novo_sl_preco:.2f}, TP: {novo_tp_preco:.2f}")
                return True
            else:
                atualizar_texto(f"Erro ao modificar Stop Loss: {resultado.comment} (Retcode: {resultado.retcode})")
                return False
        else:
            atualizar_texto("O novo Stop Loss e Take Profit são iguais aos atuais. Nenhuma mudança feita.")
            return False
    else:
        atualizar_texto("Nenhuma posição aberta para modificar o Stop Loss.")
        return False

#------------------------------------------------------------------
#                  Lucro diário (Melhorado)
#------------------------------------------------------------------
def obter_lucro_diario():
    global AtivoAoperar, StopGainDia, StopLossDia
    lucro_total_hoje = 0.0

    # Obter todas as negociações fechadas de hoje
    data_de_hoje = datetime.now().date()
    # Define o início do dia de negociação para o cálculo de lucro
    # Ajuste para o fuso horário da corretora se necessário
    data_inicial_hoje = datetime(data_de_hoje.year, data_de_hoje.month, data_de_hoje.day, 0, 0, 0)
    data_final_hoje = datetime.now() # Vai até o momento atual

    historico_negociacoes = mt5.history_deals_get(data_inicial_hoje, data_final_hoje)

    if historico_negociacoes is None:
        atualizar_texto(f"Erro ao obter histórico de negociações: {mt5.last_error()}")
        return

    num_negociacoes_fechadas = 0
    if len(historico_negociacoes) > 0:
        for deal in historico_negociacoes:
            if deal.entry == mt5.DEAL_ENTRY_OUT: # Apenas negociações de fechamento
                if deal.time_msc >= data_inicial_hoje.timestamp() * 1000: # Verifica se está dentro do dia de hoje
                    lucro_total_hoje += deal.profit
                    num_negociacoes_fechadas += 1
        atualizar_texto(f"Negociações fechadas hoje: {num_negociacoes_fechadas}")
    else:
        atualizar_texto("Nenhuma negociação fechada hoje encontrada.")

    # Verificar posições em aberto e adicionar lucro/prejuízo não realizado
    posicoes_abertas = mt5.positions_get(symbol=AtivoAoperar)
    lucro_posicoes_abertas = 0.0

    if posicoes_abertas is None:
        atualizar_texto(f"Erro ao obter posições abertas: {mt5.last_error()}")
    elif len(posicoes_abertas) == 0:
        atualizar_texto("Nenhuma posição em aberto.")
    else:
        # Assumindo que você lida com apenas uma posição por vez para simplificar
        posicao = posicoes_abertas[0]
        symbol_info = mt5.symbol_info(AtivoAoperar)
        if symbol_info is None:
            atualizar_texto(f"Erro: Ativo {AtivoAoperar} não encontrado para cálculo de posição.")
            return

        tick = mt5.symbol_info_tick(AtivoAoperar)
        if tick is None:
            atualizar_texto(f"Erro ao obter tick info para {AtivoAoperar}.")
            return

        # Calcular o lucro/prejuízo da posição aberta
        lucro_posicoes_abertas = posicao.profit # MT5 já fornece o lucro/prejuízo atualizado
        
        atualizar_texto(f"Posição aberta: {posicao.volume} @ {posicao.price_open:.2f} - Lucro/Prejuízo não realizado: {lucro_posicoes_abertas:.2f}")
    
    lucro_total_final = lucro_total_hoje + lucro_posicoes_abertas
    atualizar_texto(f"Lucro total de hoje (realizado + não realizado): {lucro_total_final:.2f}")

    # Verificar se o lucro diário atingiu os limites
    if lucro_total_final >= StopGainDia:
        atualizar_texto("Encerrando MetaTrader por gain diário.")
        # Fechar todas as posições antes de encerrar
        if tipo_posicao is not None:
            fechar_posicao_mt5(AtivoAoperar)
        mt5.shutdown()
        global estrategia_ativa
        estrategia_ativa = False # Para parar o loop principal
        atualizar_texto("Estratégia finalizada por Stop Gain Diário.")

    if lucro_total_final <= StopLossDia:
        atualizar_texto("Encerrando MetaTrader por loss diário.")
        # Fechar todas as posições antes de encerrar
        if tipo_posicao is not None:
            fechar_posicao_mt5(AtivoAoperar)
        mt5.shutdown()
        estrategia_ativa = False # Para parar o loop principal
        atualizar_texto("Estratégia finalizada por Stop Loss Diário.")

#----------------------------------------
#                  Loop Principal para Executar a Estratégia
#------------------------------------------------------------------
def iniciar_estrategia():
    global estrategia_ativa, tipo_posicao, preco_inicial
    obter_parametros()  # Obter os parâmetros inseridos pelo usuário

    ticker = AtivoAoperar
    intervalo = mt5.TIMEFRAME_M5 # Qual periodo dos candles

    # Selecionar o símbolo uma vez no início da estratégia
    if not mt5.symbol_select(ticker, True):
        atualizar_texto(f"Falha ao selecionar o ativo {ticker}. Verifique se ele está visível no MetaTrader 5.")
        estrategia_ativa = False
        return

    # Inicializa preco_inicial com o preço atual ao iniciar a estratégia
    # Isso é crucial para o trailing stop funcionar corretamente desde o início
    tick_info = mt5.symbol_info_tick(ticker)
    if tick_info is None:
        atualizar_texto(f"Erro ao obter informações de tick para {ticker}. Encerrando estratégia.")
        estrategia_ativa = False
        return

    # Define o preco_inicial baseado na primeira posição, se houver
    # Ou no preço atual se não houver posições
    posicoes_abertas = mt5.positions_get(symbol=ticker)
    if posicoes_abertas and len(posicoes_abertas) > 0:
        pos = posicoes_abertas[0]
        preco_inicial = pos.price_open # Usa o preço de abertura da posição existente
        if pos.type == mt5.ORDER_TYPE_BUY:
            tipo_posicao = "comprado"
        elif pos.type == mt5.ORDER_TYPE_SELL:
            tipo_posicao = "vendido"
        atualizar_texto(f"Retomando operação com posição {tipo_posicao} aberta a {preco_inicial:.2f}.")
    else:
        preco_inicial = tick_info.ask # Preço de compra para começar o monitoramento
        tipo_posicao = None
        atualizar_texto(f"Iniciando sem posições. Preço inicial de referência: {preco_inicial:.2f}")


    while estrategia_ativa:
        hora_atual = datetime.now().hour
        minuto_atual = datetime.now().minute

        if hora_atual >= 9 and hora_atual < 17:  # Horário de operação (9h às 17h)
            
            # Pega os dados mais recentes (ex: últimos 100 candles)
            dados_atualizados = pegando_dados(ticker, intervalo, 100)
            if dados_atualizados.empty:
                atualizar_texto("Nenhum dado atualizado disponível. Tentando novamente...")
                time.sleep(5) # Espera um pouco se não conseguir dados
                continue
            
            # Garante que as médias móveis e outras análises tenham dados suficientes
            if len(dados_atualizados) < max(mediaMovelLenta, 3): # 3 para os padrões de candlestick
                atualizar_texto(f"Dados insuficientes para as estratégias. Mínimo {max(mediaMovelLenta, 3)} candles.")
                time.sleep(60 * Atualizar)
                continue

            tick = mt5.symbol_info_tick(ticker)
            if tick is None:
                atualizar_texto(f"Erro ao obter tick para {ticker}. Pulando iteração.")
                time.sleep(1)
                continue
            
            preco_atual_ask = tick.ask
            preco_atual_bid = tick.bid

            hora_agora = datetime.now().strftime("%H:%M:%S")
            atualizar_texto(f"--- {hora_agora} ---")
            atualizar_texto(f"Preço ASK: {preco_atual_ask:.2f} | Preço BID: {preco_atual_bid:.2f}")
            
            obter_lucro_diario() # Verifica e exibe o lucro diário, pode encerrar o robô

            if not estrategia_ativa: # Se obter_lucro_diario desativou a estratégia
                break 

            # Executa as estratégias
            estrategia_medias_moveis(dados_atualizados, ticker) # Aplica a estratégia de médias móveis
            estrategia_estrela_cadente(dados_atualizados, ticker) # Aplica a estratégia de estrela cadente
            estrategia_martelo(dados_atualizados, ticker) # Aplica a estratégia martelo 
            
            # Monitora o preço e ajusta Stop (Trailing Stop)
            # Verifica o tipo de posição ANTES de tentar ajustar o stop
            posicoes_abertas_para_stop = mt5.positions_get(symbol=ticker)
            if posicoes_abertas_para_stop and len(posicoes_abertas_para_stop) > 0:
                pos = posicoes_abertas_para_stop[0] # Pega a primeira posição
                if pos.type == mt5.ORDER_TYPE_BUY: # Comprado
                    if preco_atual_bid >= preco_inicial + AcionarNovoStop: # Usa bid para comprado para trailing stop
                        atualizar_texto(f"Acionando novo stop para posição comprada. Preço atual: {preco_atual_bid:.2f}, Preço inicial: {preco_inicial:.2f}")
                        if modificar_stop(ticker, novo_stop_loss, novo_stop_gain):
                            preco_inicial = preco_atual_bid # Atualiza o preço inicial para o novo nível
                elif pos.type == mt5.ORDER_TYPE_SELL: # Vendido
                    if preco_atual_ask <= preco_inicial - AcionarNovoStop: # Usa ask para vendido para trailing stop
                        atualizar_texto(f"Acionando novo stop para posição vendida. Preço atual: {preco_atual_ask:.2f}, Preço inicial: {preco_inicial:.2f}")
                        if modificar_stop(ticker, novo_stop_loss, novo_stop_gain):
                            preco_inicial = preco_atual_ask # Atualiza o preço inicial para o novo nível
            else:
                # Se não há posições, reseta preco_inicial para o preço atual para a próxima operação
                # e tipo_posicao também já deve estar None
                preco_inicial = mt5.symbol_info_tick(ticker).ask if mt5.symbol_info_tick(ticker) else 0.0


            time.sleep(60 * Atualizar)
        else:
            atualizar_texto("Fora do horário de operação (09:00 - 17:00). Pausando até o horário de abertura.")
            # Se houver posições abertas fora do horário, você pode optar por fechá-las aqui
            # if tipo_posicao is not None:
            #     fechar_posicao_mt5(ticker)
            time.sleep(60) # Esperar 1 minuto antes de verificar novamente

#------------------------------------------------------------------
#                  Função para Alternar entre Iniciar e Pausar
#------------------------------------------------------------------
def alternar_estrategia():
    global estrategia_ativa
    
    if estrategia_ativa:
        estrategia_ativa = False
        botao_iniciar.config(text="Iniciar Estratégia")
        atualizar_texto("Estratégia pausada.")
    else:
        estrategia_ativa = True
        botao_iniciar.config(text="Pausar Estratégia")
        atualizar_texto(f"Estratégia iniciada.")
        # Iniciar a estratégia em uma thread separada para não bloquear a interface gráfica
        Thread(target=iniciar_estrategia).start()

#------------------------------------------------------------------
#                  Iniciando a Interface Gráfica
#------------------------------------------------------------------

# Criando a interface gráfica com os parâmetros
criar_interface_parametros()

# Botão para iniciar/pausar a estratégia
botao_iniciar = tk.Button(root, text="Iniciar Estratégia", command=alternar_estrategia, font=("Arial", 12))
botao_iniciar.pack(pady=10)

# Widget de texto para exibir as mensagens
texto_log = tk.Text(root, height=10, width=80, font=("Arial", 10))
texto_log.pack(padx=10, pady=10)

# Iniciando o loop da interface gráfica
root.mainloop()

# No final do script, desligar o MetaTrader 5
mt5.shutdown()