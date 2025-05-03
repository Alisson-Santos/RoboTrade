import MetaTrader5 as mt5
import pandas as pd
import time
import tkinter as tk
from datetime import datetime, timedelta
from threading import Thread

# Inicializando o MetaTrader 5
mt5.initialize()

# Variável global para controlar o estado da estratégia (iniciada ou pausada)
estrategia_ativa = False

#------------------------------------------------------------------
#                  Interface Gráfica
#------------------------------------------------------------------

# Criando a janela principal
root = tk.Tk()
root.title("Robo Trader - Andromeda 2.7")

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
        "Ativo a Operar": "WINJ25",
        "Contratos": 1.0,
        "Média Móvel Rápida": 17,
        "Média Móvel Lenta": 72,
        "Stop Gain (Operação)": 500,
        "Stop Loss (Operação)": 200,
        "Stop Gain (Dia)": 500,
        "Stop Loss (Dia)": -100,
        "Acionar Novo Stop": 100,
        "Novo Stop Gain": 150,
        "Novo Stop Loss": 100,
        "Atualizar (minutos)": 5
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
    StopGain = float(entries["Stop Gain (Operação)"].get())
    StopLoss = float(entries["Stop Loss (Operação)"].get())
    StopGainDia = float(entries["Stop Gain (Dia)"].get())
    StopLossDia = float(entries["Stop Loss (Dia)"].get())
    AcionarNovoStop = float(entries["Acionar Novo Stop"].get())
    novo_stop_gain = float(entries["Novo Stop Gain"].get())
    novo_stop_loss = float(entries["Novo Stop Loss"].get())
    Atualizar = int(entries["Atualizar (minutos)"].get())

# Função para atualizar o widget de texto com as mensagens

def atualizar_texto(mensagem):
    texto_log.insert(tk.END, mensagem + "\n")  # Adiciona a mensagem ao final do widget
    texto_log.see(tk.END)  # Rola para o final do texto
    root.update_idletasks()  # Atualiza a interface gráfica

#------------------------------------------------------------------
#                  Pegando os dados
#------------------------------------------------------------------
def pegando_dados(ativo_negociado, intervalo, data_de_inicio, data_fim):
    dados = mt5.copy_rates_range(ativo_negociado, intervalo, data_de_inicio, data_fim)
    dados = pd.DataFrame(dados)
    dados["time"] = pd.to_datetime(dados["time"], unit="s")
    return dados

#------------------------------------------------------------------
#                  Função de Compra
#------------------------------------------------------------------
def comprar(ativo):
    global tipo_posicao, Contratos, StopLoss, StopGain
    preco_de_tela = mt5.symbol_info(ativo).ask

    ordem_compra = {
        "action": mt5.TRADE_ACTION_DEAL,  # trade a mercado
        "symbol": ativo,
        "volume": Contratos,
        "type": mt5.ORDER_TYPE_BUY,
        "price": preco_de_tela,
        "sl": preco_de_tela - StopLoss,
        "tp": preco_de_tela + StopGain,
        "deviation": 10,
        "type_time": mt5.ORDER_TIME_DAY,  # só manda a ordem se o mercado tiver aberto
        "type_filling": mt5.ORDER_FILLING_RETURN,
    }

    resultado = mt5.order_send(ordem_compra)
    if resultado.retcode == mt5.TRADE_RETCODE_DONE:
        tipo_posicao = "comprado"  # Atualizando o tipo de posição para "comprado"
        atualizar_texto(f"> Comprou ativo a: {preco_de_tela}")
    else:
        atualizar_texto(f"Erro ao comprar: {resultado.comment}")

#------------------------------------------------------------------
#                  Função de Venda
#------------------------------------------------------------------
def vender(ativo):
    global tipo_posicao, Contratos, StopLoss, StopGain
    preco_de_tela = mt5.symbol_info(ativo).bid

    ordem_venda = {
        "action": mt5.TRADE_ACTION_DEAL,  # trade a mercado
        "symbol": ativo,
        "volume": Contratos,
        "type": mt5.ORDER_TYPE_SELL,
        "price": preco_de_tela,
        "sl": preco_de_tela + StopLoss,
        "tp": preco_de_tela - StopGain,
        "deviation": 10,
        "type_time": mt5.ORDER_TIME_DAY,  # só manda a ordem se o mercado tiver aberto
        "type_filling": mt5.ORDER_FILLING_RETURN,
    }

    resultado = mt5.order_send(ordem_venda)
    if resultado.retcode == mt5.TRADE_RETCODE_DONE:
        tipo_posicao = "vendido"  # Atualizando o tipo de posição para "vendido"
        atualizar_texto(f"> Vendeu ativo a: {preco_de_tela}")
    else:
        atualizar_texto(f"Erro ao vender: {resultado.comment}")


def enviar_ordem_fechamento(ativo):
    """
    Função para enviar uma ordem de fechamento da posição atual no ativo especificado.
    """
    global tipo_posicao

    # Verifica se há uma posição aberta para fechar
    if tipo_posicao is None:
        atualizar_texto(f"Nenhuma posição aberta para fechar em {ativo}.")
        return

    # Lógica para fechar a posição (depende da API da corretora)
    try:
        # Exemplo de como enviar uma ordem de fechamento
        if tipo_posicao == "comprado":
            # Se a posição for comprada, vende para fechar
            quantidade = Contratos(ativo)  # Função para obter a quantidade da posição
            vender(ativo, quantidade)  # Função para enviar ordem de venda
            atualizar_texto(f"Ordem de fechamento enviada: Vendido {quantidade} de {ativo}.")
        elif tipo_posicao == "vendido":
            # Se a posição for vendida, compra para fechar
            quantidade = Contratos(ativo)  # Função para obter a quantidade da posição
            comprar(ativo, quantidade)  # Função para enviar ordem de compra
            atualizar_texto(f"Ordem de fechamento enviada: Comprado {quantidade} de {ativo}.")
        
        # Reseta o tipo de posição após o fechamento
        tipo_posicao = None
    except Exception as e:
        atualizar_texto(f"Erro ao enviar ordem de fechamento: {e}")


def fechar_posicao(ativo):
    global tipo_posicao
    # Lógica para fechar a posição (depende da API da corretora)
    enviar_ordem_fechamento(ativo)  # Exemplo de função para enviar ordem de fechamento
    atualizar_texto(f"Posição em {ativo} fechada.")
    tipo_posicao = None  # Reseta o estado da posição

#------------------------------------------------------------------
#                 Estégia Estrela Cadente
#------------------------------------------------------------------
def estrategia_estrela_cadente(dados, ativo):
    hora_agora = datetime.now().strftime("%H:%M")
    atualizar_texto(f"Hora atual: {hora_agora}")

    """
    Função que verifica se há um padrão de estrela cadente após uma tendência de alta
    e executa uma ordem de venda se o padrão for identificado.
    Encerra qualquer posição anterior antes de vender.
    """
    global tipo_posicao

    # Verifica se há dados suficientes para análise
    if len(dados) < 3:
        atualizar_texto("Dados insuficientes para identificar padrão de estrela cadente.")
        return

    # Obtém os últimos 3 candles
    candle_atual = dados.iloc[-1]
    candle_anterior = dados.iloc[-2]
    candle_antecessor = dados.iloc[-3]

    # Verifica a tendência de alta (últimos 3 candles com fechamentos crescentes)
    tendencia_alta = (
        candle_antecessor["close"] < candle_anterior["close"] and
        candle_anterior["close"] < candle_atual["close"]
    )

    # Verifica o padrão de estrela cadente no candle atual
    corpo_candle = abs(candle_atual["close"] - candle_atual["open"])
    sombra_superior = candle_atual["high"] - max(candle_atual["open"], candle_atual["close"])
    sombra_inferior = min(candle_atual["open"], candle_atual["close"]) - candle_atual["low"]

    # Condições para identificar uma estrela cadente
    estrela_cadente = (
        corpo_candle > 0 and  # Evita candles de doji (corpo muito pequeno)
        sombra_superior >= 2 * corpo_candle and  # Sombra superior longa
        sombra_inferior <= corpo_candle  # Sombra inferior pequena
    )

    # Se houver tendência de alta e padrão de estrela cadente
    if tendencia_alta and estrela_cadente:
        # Verifica se há uma posição aberta
        if tipo_posicao == "comprado":
            atualizar_texto("Fechando posição comprada existente.")
            fechar_posicao(ativo)  # Função para fechar a posição atual
            tipo_posicao = None  # Reseta o tipo de posição

        # Executa a ordem de venda
        if tipo_posicao != "vendido":  # Só vende se não estiver vendido
            vender(ativo)
            tipo_posicao = "vendido"  # Atualiza o tipo de posição
            atualizar_texto("Vendido por estrela cadente.")  # Mensagem de confirmação
        else:
            atualizar_texto("Ativo já está vendido.")
    else:
        atualizar_texto("Padrão de estrela cadente não identificado.")

#------------------------------------------------------------------
#                 Estégia Martelo
#------------------------------------------------------------------

def estrategia_martelo(dados, ativo):
    """
    Função que verifica se há um padrão de martelo após uma tendência de baixa
    e executa uma ordem de compra se o padrão for identificado.
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

    # Verifica a tendência de baixa (últimos 3 candles com fechamentos decrescentes)
    tendencia_baixa = (
        candle_antecessor["close"] > candle_anterior["close"] and
        candle_anterior["close"] > candle_atual["close"]
    )

    # Verifica o padrão de martelo no candle atual
    corpo_candle = abs(candle_atual["close"] - candle_atual["open"])
    sombra_inferior = min(candle_atual["open"], candle_atual["close"]) - candle_atual["low"]
    sombra_superior = candle_atual["high"] - max(candle_atual["open"], candle_atual["close"])

    # Condições para identificar um martelo
    martelo = (
        corpo_candle > 0 and  # Evita candles de doji (corpo muito pequeno)
        sombra_inferior >= 2 * corpo_candle and  # Sombra inferior longa
        sombra_superior <= corpo_candle  # Sombra superior pequena
    )

    # Se houver tendência de baixa e padrão de martelo, compra
    if tendencia_baixa and martelo:
        if tipo_posicao != "comprado":  # Só compra se não estiver comprado
            comprar(ativo)
        else:
            atualizar_texto("Ativo já está comprado.")
    else:
        atualizar_texto("Padrão de martelo não identificado.")

#------------------------------------------------------------------
#                  Estratégia de Médias Móveis
#------------------------------------------------------------------
def estrategia_medias_moveis(dados, ativo):
    global tipo_posicao

    dados["media_rapida"] = dados["close"].rolling(mediaMovelRapida).mean()
    dados["media_devagar"] = dados["close"].rolling(mediaMovelLenta).mean()

    ultima_media_rapida = dados["media_rapida"].iloc[-1]
    ultima_media_devagar = dados["media_devagar"].iloc[-1]

    posicao = mt5.positions_get(symbol=ativo)

    # Atualiza o tipo_posicao com base nas posições abertas
    if len(posicao) > 0:
        if posicao[0].type == mt5.ORDER_TYPE_BUY:
            tipo_posicao = "comprado"
        elif posicao[0].type == mt5.ORDER_TYPE_SELL:
            tipo_posicao = "vendido"
    else:
        tipo_posicao = None  # Nenhuma posição aberta

    #------------------------------------------------------------------
    #                  COMPRAR
    #------------------------------------------------------------------
    preco_de_tela = mt5.symbol_info(ativo).ask
    if ultima_media_rapida > ultima_media_devagar and preco_de_tela > ultima_media_rapida:
        if tipo_posicao != "comprado":  # Só compra se não estiver comprado
            comprar(ativo)
        else:
            atualizar_texto("Ativo está comprado.")

    #------------------------------------------------------------------
    #                  VENDER
    #------------------------------------------------------------------
    preco_de_tela = mt5.symbol_info(ativo).bid
    if ultima_media_rapida <= ultima_media_devagar and preco_de_tela <= ultima_media_rapida:
        if tipo_posicao != "vendido":  # Só vende se não estiver vendido
            vender(ativo)
        else:
            atualizar_texto("Ativo está vendido.")
#------------------------------------------------------------------
#                   Modificando stoploss
#------------------------------------------------------------------
def modificar_stop(ativo, novo_stop_loss, novo_stop_gain):
    # Obter posições abertas:
    posicao = mt5.positions_get(symbol=ativo)
    if posicao and len(posicao) > 0:  # garantindo que tem uma posição aberta
        # Obter Informações da Posição
        ticket = posicao[0].ticket
        preco_de_tela = mt5.symbol_info(ativo).bid if posicao[0].type == mt5.ORDER_TYPE_SELL else mt5.symbol_info(ativo).ask
        sl_atual = posicao[0].sl  # obtendo valor de stoploss
        tp_atual = posicao[0].tp  # obtendo valor de stopgain

        # Verificar se o Novo Stop é Diferente do Atual
        if posicao[0].type == mt5.ORDER_TYPE_BUY:  # Se estiver comprado
            if sl_atual != preco_de_tela - novo_stop_loss or tp_atual != preco_de_tela + novo_stop_gain:
                # Dicionário:
                ordem_modificacao = {
                    "action": mt5.TRADE_ACTION_SLTP,
                    "symbol": ativo,
                    "position": ticket,
                    "sl": preco_de_tela - novo_stop_loss,
                    "tp": preco_de_tela + novo_stop_gain,
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": mt5.ORDER_FILLING_RETURN,
                }
                resultado = mt5.order_send(ordem_modificacao)
                atualizar_texto(f"Resultado da modificação do Stop Loss (Comprado)")
                if resultado.retcode == mt5.TRADE_RETCODE_DONE:
                    atualizar_texto(f"Stop Loss e Take Profit modificados com sucesso!")
                else:
                    atualizar_texto(f"Erro ao modificar Stop Loss: {resultado.comment}")
            else:
                atualizar_texto("O novo Stop Loss é igual ao Stop Loss atual. Nenhuma mudança feita.")
        
        elif posicao[0].type == mt5.ORDER_TYPE_SELL:  # Se estiver vendido
            if sl_atual != preco_de_tela + novo_stop_loss or tp_atual != preco_de_tela - novo_stop_gain:
                # Dicionário:
                ordem_modificacao = {
                    "action": mt5.TRADE_ACTION_SLTP,
                    "symbol": ativo,
                    "position": ticket,
                    "sl": preco_de_tela + novo_stop_loss,
                    "tp": preco_de_tela - novo_stop_gain,
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": mt5.ORDER_FILLING_RETURN,
                }
                resultado = mt5.order_send(ordem_modificacao)
                atualizar_texto(f"Resultado da modificação do Stop Loss (Vendido)")
                if resultado.retcode == mt5.TRADE_RETCODE_DONE:
                    atualizar_texto(f"Stop Loss e Take Profit modificados com sucesso!")
                else:
                    atualizar_texto(f"Erro ao modificar Stop Loss: {resultado.comment}")
            else:
                atualizar_texto("O novo Stop Loss é igual ao Stop Loss atual. Nenhuma mudança feita.")
    else:
        atualizar_texto("Nenhuma posição aberta para modificar o Stop Loss.")

#------------------------------------------------------------------
#                  Lucro diário
#------------------------------------------------------------------


def obter_lucro_diario():
    # Inicializa a variável lucro_total com 0
    lucro_total = 0.0

    # Obter todas as negociações fechadas de hoje
    data_de_hoje = datetime.now().date()
    data_inicial = datetime(data_de_hoje.year, data_de_hoje.month, data_de_hoje.day, 9, 0, 0)
    data_final = datetime(data_de_hoje.year, data_de_hoje.month, data_de_hoje.day, 23, 59, 59)

    # Obtém o histórico de negociações fechadas no dia
    historico_negociacoes = mt5.history_deals_get(data_inicial, data_final)

    if historico_negociacoes is None:
        atualizar_texto("Erro ao obter o histórico de negociações. Verifique a conexão com o MetaTrader 5.")
        return

    if len(historico_negociacoes) > 0:
        # Converte o histórico de negociações para um DataFrame
        df_negociacoes = pd.DataFrame(list(historico_negociacoes), columns=historico_negociacoes[0]._asdict().keys())

        # Filtra apenas as negociações fechadas (ordens de fechamento)
        df_negociacoes_fechadas = df_negociacoes[df_negociacoes["entry"] == mt5.DEAL_ENTRY_OUT]

        # Soma o lucro de todas as negociações fechadas
        lucro_total = df_negociacoes_fechadas['profit'].sum()
        atualizar_texto(f"Negociações fechadas hoje: {len(df_negociacoes_fechadas)}")
    else:
        atualizar_texto("Nenhuma negociação fechada encontrada no histórico de hoje.")

    # Verificar posições em aberto
    posicoes_abertas = mt5.positions_get(symbol=AtivoAoperar)
    if posicoes_abertas is None:
        atualizar_texto("Erro ao obter as posições abertas. Verifique a conexão com o MetaTrader 5.")
    elif len(posicoes_abertas) == 0:
        atualizar_texto("Nenhuma posição em aberto.")
    else:
        for posicao in posicoes_abertas:
            preco_atual = mt5.symbol_info_tick(AtivoAoperar).bid if posicao.type == mt5.ORDER_TYPE_SELL else mt5.symbol_info_tick(AtivoAoperar).ask
            if posicao.type == mt5.ORDER_TYPE_BUY:  # Comprado
                valor_posicao = (preco_atual - posicao.price_open) * posicao.volume * 0.2
            elif posicao.type == mt5.ORDER_TYPE_SELL:  # Vendido
                valor_posicao = (posicao.price_open - preco_atual) * posicao.volume * 0.2

            atualizar_texto(f"Valor da posição: {valor_posicao:.2f}")

    # Exibir o lucro total de hoje
    atualizar_texto(f"Lucro total de hoje: {lucro_total:.2f}")

    # Verificar se o lucro diário atingiu os limites
    if lucro_total >= StopGainDia:
        atualizar_texto("Encerrando MetaTrader por gain.")
        time.sleep(5)
        mt5.shutdown()

    if lucro_total <= StopLossDia:
        atualizar_texto("Encerrando MetaTrader por loss.")
        time.sleep(5)
        mt5.shutdown()
#----------------------------------------
#                  Loop Principal para Executar a Estratégia
#------------------------------------------------------------------
def iniciar_estrategia():
    global estrategia_ativa
    obter_parametros()  # Obter os parâmetros inseridos pelo usuário
    while estrategia_ativa:
        hora_atual = datetime.now().hour # Atualizar a hora

        if hora_atual >= 9 and hora_atual < 17:  # Horário de operação (9h às 17h)
            ticker = AtivoAoperar
            intervalo = mt5.TIMEFRAME_M5    #Qual periodo dos candles
            data_final = datetime.today()   
            data_inicial = datetime.today() - timedelta(days=6)
            mt5.symbol_select(ticker)
            preco_inicial = mt5.symbol_info(ticker).ask
            while estrategia_ativa:
                preco_atual = mt5.symbol_info(ticker).ask
                dados_atualizados = pegando_dados(ticker, intervalo, data_inicial, data_final)# Atualiza os dados para serem usados nas estratégis
              
                estrategia_estrela_cadente(dados_atualizados, ticker)# Aplica a estratégia de estrela cadente
                estrategia_martelo(dados_atualizados, ticker)# Aplica a estratégia matelo 
                estrategia_medias_moveis(dados_atualizados, ticker)# Aplica a estratégia de médias móveis

                # Preço
                atualizar_texto(f"Preço Atual: {preco_atual}")
                obter_lucro_diario()  

                # Monitora o preço e ajusta Stop
                if tipo_posicao == "comprado" and preco_atual >= preco_inicial + AcionarNovoStop:
                    modificar_stop(ticker, novo_stop_loss, novo_stop_gain)
                    preco_inicial = preco_atual  # Atualizando o preço inicial após reajustar o Stop Loss
                elif tipo_posicao == "vendido" and preco_atual <= preco_inicial - AcionarNovoStop:
                    modificar_stop(ticker, novo_stop_loss, novo_stop_gain)
                    preco_inicial = preco_atual  # Atualizando o preço inicial após reajustar o Stop Loss

                time.sleep(60 * Atualizar)
        else:
            # Fora do horário de operação, pausa a execução
            time.sleep(1)  # Aguardar 1 segundos antes de verificar novamente

#------------------------------------------------------------------
#                  Função para Alternar entre Iniciar e Pausar
#------------------------------------------------------------------
def alternar_estrategia():
    global estrategia_ativa
    
    hora_agora = datetime.now().strftime("%H:%M")
    atualizar_texto(f"Hora atual: {hora_agora}")

    if estrategia_ativa:
        estrategia_ativa = False
        botao_iniciar.config(text="Iniciar Estratégia")
        atualizar_texto("Estratégia pausada.")
    else:
        estrategia_ativa = True
        botao_iniciar.config(text="Pausar Estratégia")
        atualizar_texto(f"Estratégia iniciada .")
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

