import MetaTrader5 as mt5
import pandas as pd
import time
import tkinter as tk
from tkinter import messagebox
from datetime import datetime, timedelta
from threading import Thread
import traceback # Importado para capturar trilhas de erro completas

#------------------------------------------------------------------
#                  Inicialização do MT5 
#------------------------------------------------------------------

# Variável global para rastrear o estado de conexão do MT5
global mt5_conectado
mt5_conectado = mt5.initialize()

if not mt5_conectado: #se não estiver conectado
    print("ERRO CRÍTICO: MetaTrader 5 não inicializado. Verifique a instalação e o terminal.")
    
else:
    print("MetaTrader 5 inicializado com sucesso.")


    
#------------------------------------------------------------------
#                  Status de posição e preço
#------------------------------------------------------------------

# Variável global para controlar o estado da estratégia (iniciada ou pausada)
estrategia_ativa = False
tipo_posicao = None # Inicializa como None para indicar que não há posição aberta
preco_inicial = 0.0 # Usado para o trailing stop, será atualizado

# Variáveis globais para os labels de P/L
label_pl_aberto = None
label_pl_fechado = None

#------------------------------------------------------------------
#                  Interface Gráfica
#------------------------------------------------------------------

# Criando a janela principal
root = tk.Tk()
root.title("Robo Trader - Andromeda 3.7")

# Função para criar e exibir os parâmetros na interface gráfica
def criar_interface_parametros():
    # Frame para organizar os parâmetros
    frame_parametros = tk.Frame(root)
    
    # Empacota o frame com preenchimento (fill) e expansão para que ele redimensione com a janela
    frame_parametros.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

    # Configura as colunas no frame_parametros para expandirem proporcionalmente
    frame_parametros.grid_columnconfigure(0, weight=1)
    frame_parametros.grid_columnconfigure(1, weight=1)
    frame_parametros.grid_columnconfigure(2, weight=1)
    frame_parametros.grid_columnconfigure(3, weight=1)

    # Configura algumas linhas para expandir, especialmente aquelas com campos de entrada (entries)
    # Percorre um número razoável de linhas, garantindo que elas possam expandir
    for i in range(1, 18): # Assumindo no máximo 17 linhas para parâmetros + cabeçalho
        frame_parametros.grid_rowconfigure(i, weight=1)


        
    #------------------------------------------------------------------
    #                Título da seção de parâmetros
    #------------------------------------------------------------------
    tk.Label(frame_parametros, text="Parâmetros de Operação", font=("Arial", 14, "bold")).grid(row=0, column=0, columnspan=4, pady=5, sticky="nsew")

    
    # Dicionário para armazenar os campos de entrada
    global entries #Primeiro declaro o nome da variavel global
    entries = {} #depois declaro só a váriavel e o que ela vai armazenar

    #------------------------------------------------------------------
    #               Parâmetros e seus valores padrão
    #------------------------------------------------------------------    
    parametros = {
        "Ativo a Operar": "WINJ26",
        "Contratos": 1.0,
        "Média Móvel Rápida": 17,
        "Média Móvel Lenta": 72,
        "Stop Gain (Operação em pontos)": 355,
        "Stop Loss (Operação em pontos)": 125,
        "Stop Gain (Dia)": 100.0, # Mudado para float para consistência com lucro
        "Stop Loss (Dia)": -60.0, # Mudado para float para consistência com lucro

        
        "Acionar Novo Stop (pontos)": 125,
        "Novo Stop Gain (pontos)": 125,
        "Novo Stop Loss (pontos)": 100,
        "Atualizar Operacao (minutos)": 5,
        "Atualizar Stop (minutos)": 1,
        "Hora Início Operação": 9,
        "Minuto Início Operação": 10,
        "Hora Fim Operação": 14,
        "Minuto Fim Operação": 30
    }

    # Dividindo os parâmetros em duas colunas para melhor distribuição
    metade = len(parametros) // 2
    parametros_col1 = list(parametros.items())[:metade]
    parametros_col2 = list(parametros.items())[metade:]

    # Adicionando os parâmetros à primeira coluna
    for i, (chave, valor) in enumerate(parametros_col1):
        tk.Label(frame_parametros, text=f"{chave}:", font=("Arial", 10)).grid(row=i+1, column=0, sticky="nsew", padx=5, pady=2)
        entry = tk.Entry(frame_parametros, font=("Arial", 10))
        entry.insert(0, str(valor))
        entry.grid(row=i+1, column=1, sticky="nsew", padx=5, pady=2)
        entries[chave] = entry

    # Adicionando os parâmetros à segunda coluna
    for i, (chave, valor) in enumerate(parametros_col2):
        tk.Label(frame_parametros, text=f"{chave}:", font=("Arial", 10)).grid(row=i+1, column=2, sticky="nsew", padx=20, pady=2)
        entry = tk.Entry(frame_parametros, font=("Arial", 10))
        entry.insert(0, str(valor))
        entry.grid(row=i+1, column=3, sticky="nsew", padx=5, pady=2)
        entries[chave] = entry

    # Adicionando labels para exibir P/L
    global label_pl_aberto, label_pl_fechado
    # Posicionados abaixo das duas colunas de parâmetros
    start_row_pl = max(len(parametros_col1), len(parametros_col2)) + 1 # +1 for header row
    tk.Label(frame_parametros, text="Monitoramento de Lucro/Prejuízo", font=("Arial", 12, "bold")).grid(row=start_row_pl, column=0, columnspan=4, pady=10, sticky="nsew")
    frame_parametros.grid_rowconfigure(start_row_pl, weight=1) # Make this row expand too

    label_pl_aberto = tk.Label(frame_parametros, text="P/L Aberto: R$ 0.00", font=("Arial", 10, "bold"))
    label_pl_aberto.grid(row=start_row_pl + 1, column=0, columnspan=2, sticky="nsew", padx=5, pady=2)
    frame_parametros.grid_rowconfigure(start_row_pl + 1, weight=1)

    label_pl_fechado = tk.Label(frame_parametros, text="P/L Fechado: R$ 0.00", font=("Arial", 10, "bold"))
    label_pl_fechado.grid(row=start_row_pl + 2, column=0, columnspan=2, sticky="nsew", padx=5, pady=2)
    frame_parametros.grid_rowconfigure(start_row_pl + 2, weight=1)


# Função para obter os parâmetros inseridos pelo usuário
def obter_parametros():
    global AtivoAoperar, Contratos, mediaMovelRapida, mediaMovelLenta, StopGain, StopLoss, StopGainDia, StopLossDia, AcionarNovoStop, novo_stop_gain, novo_stop_loss, AtualizarOperacao, AtualizarStop, HoraInicioOperacao, MinutoInicioOperacao, HoraFimOperacao, MinutoFimOperacao
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
    AtualizarOperacao = int(entries["Atualizar Operacao (minutos)"].get())
    AtualizarStop = int(entries["Atualizar Stop (minutos)"].get())
    HoraInicioOperacao = int(entries["Hora Início Operação"].get())
    MinutoInicioOperacao = int(entries["Minuto Início Operação"].get())
    HoraFimOperacao = int(entries["Hora Fim Operação"].get())
    MinutoFimOperacao = int(entries["Minuto Fim Operação"].get())


# Função para atualizar o widget de texto com as mensagens
def atualizar_texto(mensagem):
    texto_log.insert(tk.END, mensagem + "\n")  # Adiciona a mensagem ao final do widget
    texto_log.see(tk.END)  # Rola para o final do texto
    root.update_idletasks()  # Atualiza a interface gráfica

#------------------------------------------------------------------
#                  Pegando os dados 
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

#------------------------------------------------------------------
# Função de fechamento de posição 
#------------------------------------------------------------------
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

    success = False
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
            success = True
        else:
            atualizar_texto(f"Erro ao fechar posição {pos.ticket}: {result.comment} (Retcode: {result.retcode})")
    return success # Retorna True se pelo menos uma posição foi fechada

#------------------------------------------------------------------
#                  Estratégia de Médias Móveis
#------------------------------------------------------------------
def estrategia_medias_moveis(dados, ativo):
    global tipo_posicao

    # Certifica-se de que há dados suficientes para as médias móveis
    if len(dados) < mediaMovelLenta:
        # atualizar_texto(f"Dados insuficientes para médias móveis. Necessário pelo menos {mediaMovelLenta} candles.") # Comentado para reduzir logs frequentes
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
        # atualizar_texto(f"Posição atual (MT5): {tipo_posicao} - Volume: {pos.volume} - Preço Abertura: {pos.price_open:.2f}") # Comentado para reduzir logs frequentes
    else:
        if tipo_posicao is not None: # Se a posição interna estava setada, mas não há no MT5, reseta
            atualizar_texto("Nenhuma posição aberta no MT5. Resetando tipo_posicao.")
        tipo_posicao = None  # Nenhuma posição aberta


    #------------------------------------------------------------------
    #                  COMPRAR
    #------------------------------------------------------------------
    tick_ask = mt5.symbol_info_tick(ativo)
    if tick_ask is None or tick_ask.ask == 0.0:
        atualizar_texto(f"Erro ao obter preço ASK para {ativo}.")
        return
    preco_ask = tick_ask.ask

    if ultima_media_rapida > ultima_media_devagar and preco_ask > ultima_media_rapida:
        if tipo_posicao != "comprado":  # Só compra se não estiver comprado
            if tipo_posicao == "vendido": # Se estiver vendido, fecha antes de comprar
                atualizar_texto("Fechando posição vendida antes de comprar por média móvel.")
                fechar_posicao_mt5(ativo)
                time.sleep(1) # Pequena pausa para a ordem de fechamento processar
            if comprar(ativo):
                atualizar_texto("Comprado pela média.")
        else:
            # atualizar_texto("Ativo já está comprado pela média.") # Comentado para reduzir logs frequentes
            pass

    #------------------------------------------------------------------
    #                  VENDER
    #------------------------------------------------------------------
    tick_bid = mt5.symbol_info_tick(ativo)
    if tick_bid is None or tick_bid.bid == 0.0:
        atualizar_texto(f"Erro ao obter preço BID para {ativo}.")
        return
    preco_bid = tick_bid.bid

    if ultima_media_rapida <= ultima_media_devagar and preco_bid <= ultima_media_rapida:
        if tipo_posicao != "vendido":  # Só vende se não estiver vendido
            if tipo_posicao == "comprado": # Se estiver comprado, fecha antes de vender
                atualizar_texto("Fechando posição comprada antes de vender por média móvel.")
                fechar_posicao_mt5(ativo)
                time.sleep(1) # Pequena pausa para a ordem de fechamento processar
            if vender(ativo):
                atualizar_texto("Vendido pela média.")
        else:
            # atualizar_texto("Ativo já está vendido pela média.") # Comentado para reduzir logs frequentes
            pass

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
            # O novo stoploss será o preço de tela menos os pontos. TP será o preço mais os pontos.
            novo_sl_preco = preco_atual_para_stop - (novo_stop_loss_pontos * point)
            novo_tp_preco = preco_atual_para_stop + (novo_stop_gain_pontos * point)
        
        elif pos.type == mt5.ORDER_TYPE_SELL:  # Se estiver vendido
            # O novo stoploss será o preço de tela mais os pontos. TP será o preço menos os pontos.
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
            # atualizar_texto("O novo Stop Loss e Take Profit são iguais aos atuais. Nenhuma mudança feita.") # Comentado para reduzir logs frequentes
            return False
    else:
        # atualizar_texto("Nenhuma posição aberta para modificar o Stop Loss.") # Comentado para reduzir logs frequentes
        return False

#------------------------------------------------------------------
#                  Lucro diário (Melhorado)
#------------------------------------------------------------------
def obter_lucro_diario():
    global AtivoAoperar, StopGainDia, StopLossDia, label_pl_aberto, label_pl_fechado, tipo_posicao, estrategia_ativa
    lucro_total_hoje_realizado = 0.0

    # Obter todas as negociações fechadas de hoje
    data_de_hoje = datetime.now().date()
    # Define o início do dia de negociação para o cálculo de lucro
    data_inicial_hoje = datetime(data_de_hoje.year, data_de_hoje.month, data_de_hoje.day, 0, 0, 0)
    data_final_hoje = datetime.now() # Vai até o momento atual

    historico_negociacoes = mt5.history_deals_get(data_inicial_hoje, data_final_hoje)

    if historico_negociacoes is None:
        # Se houver erro, apenas exibe a mensagem de erro mas não encerra a estratégia
        atualizar_texto(f"Erro ao obter histórico de negociações: {mt5.last_error()}")
        return

    if len(historico_negociacoes) > 0:
        for deal in historico_negociacoes:
            # Verifica se é uma negociação de fechamento e se é do ativo atual
            if deal.entry == mt5.DEAL_ENTRY_OUT and deal.symbol == AtivoAoperar:
                # O MT5 fornece o timestamp em segundos, o timestamp() retorna em segundos.
                if deal.time_msc >= data_inicial_hoje.timestamp() * 1000:
                    lucro_total_hoje_realizado += deal.profit
    
    # Adicionar lucro/prejuízo de posições em aberto para exibição, mas não para o stop diário
    posicoes_abertas = mt5.positions_get(symbol=AtivoAoperar)
    lucro_posicoes_abertas = 0.0

    if posicoes_abertas:
        for posicao in posicoes_abertas:
            lucro_posicoes_abertas += posicao.profit
        label_pl_aberto.config(text=f"P/L Aberto: R$ {lucro_posicoes_abertas:.2f}")
    else:
        label_pl_aberto.config(text="P/L Aberto: R$ 0.00")

    # Atualiza o P/L Fechado na GUI
    label_pl_fechado.config(text=f"P/L Fechado: R$ {lucro_total_hoje_realizado:.2f}")

    # A verificação do stop diário agora usa apenas o lucro realizado
    if lucro_total_hoje_realizado >= StopGainDia:
        if estrategia_ativa: # Apenas encerra se estiver ativa
            atualizar_texto("Encerrando por gain diário (lucro REALIZADO).")
            if tipo_posicao is not None:
                fechar_posicao_mt5(AtivoAoperar)
            estrategia_ativa = False
            atualizar_texto("Estratégia finalizada por Stop Gain Diário.")
            return

    if lucro_total_hoje_realizado <= StopLossDia:
        if estrategia_ativa: # Apenas encerra se estiver ativa
            atualizar_texto("Encerrando por loss diário (prejuízo REALIZADO).")
            if tipo_posicao is not None:
                fechar_posicao_mt5(AtivoAoperar)
            estrategia_ativa = False
            atualizar_texto("Estratégia finalizada por Stop Loss Diário.")
            return

#----------------------------------------
#                  Loop Principal para Executar a Estratégia (Corrigido)
#------------------------------------------------------------------
def iniciar_estrategia_thread():
    global estrategia_ativa, tipo_posicao, preco_inicial, AtualizarOperacao, AtualizarStop, HoraInicioOperacao, MinutoInicioOperacao, HoraFimOperacao, MinutoFimOperacao, mt5_conectado
    
    # **CORREÇÃO 2: Impedir execução se MT5 falhou na inicialização**
    if not mt5_conectado:
        atualizar_texto("ERRO: A estratégia não pode ser iniciada. Conexão MT5 falhou na inicialização.")
        estrategia_ativa = False
        atualizar_botoes()
        return

    # **CORREÇÃO 3: Bloco try-except para a thread de negociação**
    try:
        # Obter os parâmetros inseridos pelo usuário
        try:
            obter_parametros()
        except ValueError as e:
            atualizar_texto(f"Erro nos parâmetros: {e}. Certifique-se de que todos os campos numéricos estão corretos.")
            estrategia_ativa = False
            atualizar_botoes()
            return

        ticker = AtivoAoperar
        intervalo = mt5.TIMEFRAME_M5 # Qual periodo dos candles

        # Selecionar o símbolo uma vez no início da estratégia
        if not mt5.symbol_select(ticker, True):
            atualizar_texto(f"Falha ao selecionar o ativo {ticker}. Verifique se ele está visível no MetaTrader 5.")
            estrategia_ativa = False
            atualizar_botoes()
            return

        # Inicializa preco_inicial com o preço atual ao iniciar a estratégia
        tick_info = mt5.symbol_info_tick(ticker)
        if tick_info is None:
            atualizar_texto(f"Erro ao obter informações de tick para {ticker}. Encerrando estratégia.")
            estrategia_ativa = False
            atualizar_botoes()
            return

        # Define o preco_inicial baseado na primeira posição, se houver
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

        # Variáveis para controlar a frequência das operações e do ajuste de stop
        last_operation_time = datetime.now() - timedelta(minutes=AtualizarOperacao + 1) # Garante que a primeira operação pode ocorrer imediatamente
        last_stop_adjustment_time = datetime.now() - timedelta(minutes=AtualizarStop + 1) # Garante que o primeiro ajuste de stop pode ocorrer imediatamente
        last_log_print_time = datetime.now() - timedelta(minutes=AtualizarOperacao + 1) # Para controlar a frequência dos logs de preço e hora


        while estrategia_ativa:
            hora_atual = datetime.now().hour
            minuto_atual = datetime.now().minute
            current_time = datetime.now()

            # Atualiza P/L Aberto e Fechado a cada iteração (aproximadamente a cada segundo)
            obter_lucro_diario() # Verifica e exibe o lucro diário, pode encerrar o robô

            if not estrategia_ativa: # Se obter_lucro_diario desativou a estratégia
                break 

            # Horário de operação ajustável pela interface
            if hora_atual >= HoraInicioOperacao and (hora_atual < HoraFimOperacao or (hora_atual == HoraFimOperacao and minuto_atual < MinutoFimOperacao)):
                
                # Pega os dados mais recentes (ex: últimos 100 candles)
                dados_atualizados = pegando_dados(ticker, intervalo, 100)
                if dados_atualizados.empty:
                    # atualizar_texto("Nenhum dado atualizado disponível. Tentando novamente...")
                    time.sleep(5) # Espera um pouco se não conseguir dados
                    continue
                
                # Garante que as médias móveis e outras análises tenham dados suficientes
                if len(dados_atualizados) < max(mediaMovelLenta, 3): # 3 para os padrões de candlestick
                    # atualizar_texto(f"Dados insuficientes para as estratégias. Mínimo {max(mediaMovelLenta, 3)} candles.") # Comentado para reduzir logs frequentes
                    time.sleep(60 * AtualizarStop) # Espera pelo tempo de atualização do stop
                    continue

                tick = mt5.symbol_info_tick(ticker)
                if tick is None:
                    atualizar_texto(f"Erro ao obter tick para {ticker}. Pulando iteração.")
                    time.sleep(1)
                    continue
                
                preco_atual_ask = tick.ask
                preco_atual_bid = tick.bid

                # Controla a frequência das mensagens de log de preço e hora (a cada AtualizarOperacao minutos)
                if (current_time - last_log_print_time).total_seconds() >= (AtualizarOperacao * 60):
                    hora_agora = datetime.now().strftime("%H:%M:%S")
                    atualizar_texto(f"--- {hora_agora} ---")
                    atualizar_texto(f"Preço ASK: {preco_atual_ask:.2f} | Preço BID: {preco_atual_bid:.2f}")
                    last_log_print_time = current_time # Atualiza o tempo da última impressão de log

                # Executa as estratégias de operação apenas se o tempo definido tiver passado (a cada AtualizarOperacao minutos)
                if (current_time - last_operation_time).total_seconds() >= (AtualizarOperacao * 60):
                    atualizar_texto(f"Executando estratégias de operação (a cada {AtualizarOperacao} minutos).")
                    estrategia_medias_moveis(dados_atualizados, ticker) # Aplica a estratégia de médias móveis
                    last_operation_time = current_time # Atualiza o tempo da última operação

                # Monitora o preço e ajusta Stop (Trailing Stop) a cada 'AtualizarStop' minutos
                if (current_time - last_stop_adjustment_time).total_seconds() >= (AtualizarStop * 60):
                    atualizar_texto(f"Verificando e ajustando stop (a cada {AtualizarStop} minuto).")
                    

                    posicoes_abertas_para_stop = mt5.positions_get(symbol=ticker)
                    if posicoes_abertas_para_stop and len(posicoes_abertas_para_stop) > 0:
                        pos = posicoes_abertas_para_stop[0] # Pega a primeira posição
                        
                        # Precisa re-obter o preço de abertura da posição para o trailing stop funcionar corretamente
                        # O preço inicial deve ser o preço onde o trailing stop foi acionado pela última vez.
                        # Aqui estamos ajustando para garantir que o preço inicial seja o preço de abertura
                        # se ainda não houve nenhum ajuste de trailing stop.
                        
                        if pos.type == mt5.ORDER_TYPE_BUY: # Comprado
                            # Se o preço atual (BID) for igual ou superior ao preço que aciona o novo stop
                            if preco_atual_bid >= preco_inicial + AcionarNovoStop: 
                                atualizar_texto(f"Acionando novo stop para posição comprada. Preço atual: {preco_atual_bid:.2f}, Preço inicial: {preco_inicial:.2f}")
                                if modificar_stop(ticker, novo_stop_loss, novo_stop_gain):
                                    preco_inicial = preco_atual_bid # Atualiza o preço inicial para o novo nível
                        elif pos.type == mt5.ORDER_TYPE_SELL: # Vendido
                            # Se o preço atual (ASK) for igual ou inferior ao preço que aciona o novo stop
                            if preco_atual_ask <= preco_inicial - AcionarNovoStop: 
                                atualizar_texto(f"Acionando novo stop para posição vendida. Preço atual: {preco_atual_ask:.2f}, Preço inicial: {preco_inicial:.2f}")
                                if modificar_stop(ticker, novo_stop_loss, novo_stop_gain):
                                    preco_inicial = preco_atual_ask # Atualiza o preço inicial para o novo nível
                    else:
                        # Se não há posições, reseta preco_inicial para o preço atual para a próxima operação
                        preco_inicial = mt5.symbol_info_tick(ticker).ask if mt5.symbol_info_tick(ticker) else 0.0
                    last_stop_adjustment_time = current_time # Atualiza o tempo do último ajuste de stop

                # Pequena pausa para não sobrecarregar a CPU
                time.sleep(1) 
            else:
                atualizar_texto(f"Fora do horário de operação ({HoraInicioOperacao:02d}:{MinutoInicioOperacao:02d} - {HoraFimOperacao:02d}:{MinutoFimOperacao:02d}). Pausando até o horário de abertura.")
                # Se houver posições abertas fora do horário, você pode optar por fechá-las aqui
                if tipo_posicao is not None:
                     atualizar_texto("Fechando posição fora do horário de operação (opcional).")
                     fechar_posicao_mt5(ticker)
                time.sleep(60) # Esperar 1 minuto antes de verificar novamente
        
        # Fim do while loop

    except Exception as e:
        # Registra o erro completo no log
        estrategia_ativa = False
        atualizar_texto("--- ERRO FATAL NA THREAD DA ESTRATÉGIA ---")
        atualizar_texto(f"Tipo de Erro: {type(e).__name__}")
        atualizar_texto(f"Mensagem: {e}")
        atualizar_texto(f"Traceback Completo:\n{traceback.format_exc()}")
        
    finally:
        atualizar_botoes() # Garante que os botões sejam atualizados
        atualizar_texto("Estratégia finalizada (Loop encerrado).")


#------------------------------------------------------------------
#                  Função para Atualizar o Estado dos Botões
#------------------------------------------------------------------
def atualizar_botoes():
    if estrategia_ativa:
        botao_iniciar.config(state=tk.DISABLED)
        botao_pausar.config(state=tk.NORMAL)
    else:
        botao_iniciar.config(state=tk.NORMAL)
        botao_pausar.config(state=tk.DISABLED)


#------------------------------------------------------------------
#                  Funções dos Botões Iniciar e Pausar
#------------------------------------------------------------------
def iniciar_robo():
    global estrategia_ativa, mt5_conectado
    
    # Se o MT5 não está conectado, exibe o erro e não inicia
    if not mt5_conectado:
        messagebox.showerror("Erro de Conexão", "O MetaTrader 5 não está conectado. Verifique o terminal e tente novamente.")
        return

    if not estrategia_ativa:
        estrategia_ativa = True
        atualizar_texto("Estratégia iniciada.")
        Thread(target=iniciar_estrategia_thread).start()
        atualizar_botoes()
    else:
        atualizar_texto("A estratégia já está em execução.")

def pausar_robo():
    global estrategia_ativa
    if estrategia_ativa:
        estrategia_ativa = False
        atualizar_texto("Estratégia pausada. Aguardando a finalização do ciclo atual...")
        # A função iniciar_estrategia_thread() irá chamar atualizar_botoes() ao finalizar seu loop
    else:
        atualizar_texto("A estratégia já está pausada.")

#------------------------------------------------------------------
#                  Iniciando a Interface Gráfica
#------------------------------------------------------------------

# Criando a interface gráfica com os parâmetros
criar_interface_parametros()

# Frame para os botões Iniciar/Pausar
frame_botoes = tk.Frame(root)
# Also pack this frame with fill and expand
frame_botoes.pack(pady=10, fill=tk.X, expand=True) # Fill X for horizontal expansion

# Botões Iniciar e Pausar
botao_iniciar = tk.Button(frame_botoes, text="Iniciar Estratégia", command=iniciar_robo, font=("Arial", 12))
botao_iniciar.pack(side=tk.LEFT, padx=5, expand=True) # Expand the button within the frame

botao_pausar = tk.Button(frame_botoes, text="Pausar Estratégia", command=pausar_robo, font=("Arial", 12))
botao_pausar.pack(side=tk.RIGHT, padx=5, expand=True) # Expand the button within the frame

# Initialize button states
atualizar_botoes()

# Widget de texto para exibir as mensagens
texto_log = tk.Text(root, height=10, width=80, font=("Arial", 10))
texto_log.pack(padx=10, pady=10, fill=tk.BOTH, expand=True) # Make the text log expand too

# Exibe o erro de conexão MT5 em uma caixa de diálogo se a inicialização falhou
if not mt5_conectado:
    messagebox.showerror("Erro de Inicialização", "O MetaTrader 5 falhou ao inicializar. A interface gráfica abrirá, mas a estratégia não poderá ser iniciada. Verifique o terminal.")
    atualizar_texto("ERRO: MT5 não conectado. Apenas a interface gráfica está funcionando.")
else:
     atualizar_texto("MT5 conectado. Pronto para operar.")


# Iniciando o loop da interface gráfica
root.mainloop()

# No final do script, desligar o MetaTrader 5 (Corrigido)
if mt5_conectado: # Apenas desliga se foi inicializado com sucesso
    mt5.shutdown()