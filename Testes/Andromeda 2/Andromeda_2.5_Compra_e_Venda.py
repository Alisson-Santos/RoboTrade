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
root.title("Robo Trader - Andromeda 2.5")

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
        "Stop Gain": 500,
        "Stop Loss": 200,
        "Stop Gain Dia": 500,
        "Stop Loss Dia": -200,
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
    StopGain = float(entries["Stop Gain"].get())
    StopLoss = float(entries["Stop Loss"].get())
    StopGainDia = float(entries["Stop Gain Dia"].get())
    StopLossDia = float(entries["Stop Loss Dia"].get())
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
#                  Definindo a estratégia
#------------------------------------------------------------------
def estrategia_trade(dados, ativo):
    global tipo_posicao  # Referenciando a variável global
    # informações para o usuário
    hora_agora = datetime.now().strftime("%H:%M")
    atualizar_texto(f"Hora atual: {hora_agora}")

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
    #                  COMPRA
    #------------------------------------------------------------------
    preco_de_tela = mt5.symbol_info(ativo).ask
    if ultima_media_rapida > ultima_media_devagar and preco_de_tela > ultima_media_rapida:
        # Verifica se já está comprado ou se há uma posição aberta
        if tipo_posicao != "comprado" and len(posicao) == 0:  # Só compra se não estiver comprado e não houver posição aberta
            preco_de_tela = mt5.symbol_info(ativo).ask

            ordem_compra = {
                "action": mt5.TRADE_ACTION_PENDING,  # trade a mercado
                "symbol": ativo,
                "volume": Contratos,
                "type": mt5.ORDER_TYPE_BUY_LIMIT,
                "price": preco_de_tela,
                "sl": preco_de_tela - StopLoss,
                "tp": preco_de_tela + StopGain,
                "deviation": 10,
                "type_time": mt5.ORDER_TIME_DAY,  # só manda a ordem se o mercado tiver aberto
                "type_filling": mt5.ORDER_FILLING_RETURN,
            }

            mt5.order_send(ordem_compra)
            tipo_posicao = "comprado"  # Atualizando o tipo de posição para "comprado"
            atualizar_texto(f"> Comprou ativo a: >{preco_de_tela}")
        else:
            atualizar_texto("Ativo está comprado.")

    #------------------------------------------------------------------
    #                  VENDA
    #------------------------------------------------------------------
    preco_de_tela = mt5.symbol_info(ativo).bid
    if ultima_media_rapida <= ultima_media_devagar and preco_de_tela <= ultima_media_rapida:
        # Verifica se já está vendido ou se há uma posição aberta
        if tipo_posicao != "vendido" and len(posicao) == 0:  # Só vende se não estiver vendido e não houver posição aberta
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

            mt5.order_send(ordem_venda)
            tipo_posicao = "vendido"  # Atualizando o tipo de posição para "vendido"
            atualizar_texto(f"> Vendeu ativo a: >{preco_de_tela}")
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
    # Obter todas as negociações fechadas de hoje
    data_de_hoje = datetime.now().date()
    data_inicial = datetime(data_de_hoje.year, data_de_hoje.month, data_de_hoje.day, 9, 0,0)
    data_final = datetime(data_de_hoje.year, data_de_hoje.month, data_de_hoje.day, 23, 59, 59)

    historico_negociacoes = mt5.history_deals_get(data_inicial, data_final)

    if historico_negociacoes is None:
        atualizar_texto("Nenhuma negociação fechada hoje.")
    else:
        # Converter o histórico para um DataFrame do Pandas
        df_negociacoes = pd.DataFrame(list(historico_negociacoes), columns=historico_negociacoes[0]._asdict().keys())

        # Calcular o lucro total das negociações de hoje
        lucro_total = df_negociacoes['profit'].sum()

    # Verificar posições em aberto
    posicoes_abertas = mt5.positions_get(symbol=AtivoAoperar)
    if posicoes_abertas is None or len(posicoes_abertas) == 0:
        atualizar_texto("Nenhuma posição em aberto.")
    else:
        for posicao in posicoes_abertas:
            preco_atual = mt5.symbol_info_tick(AtivoAoperar).bid if posicao.type == mt5.ORDER_TYPE_SELL else mt5.symbol_info_tick(AtivoAoperar).ask
            if posicao.type == mt5.ORDER_TYPE_BUY:  # Comprado
                valor_posicao = (preco_atual - posicao.price_open) * posicao.volume * 0.2
            elif posicao.type == mt5.ORDER_TYPE_SELL:  # Vendido
                valor_posicao = (posicao.price_open - preco_atual) * posicao.volume * 0.2

            atualizar_texto(f"Valor da posição: {valor_posicao:.2f}")
    
    atualizar_texto(f"Lucro total de hoje: {lucro_total:.2f}")

    # Verificar se o lucro diário atingiu os limites
    if 'lucro_total' in locals() and lucro_total >= 600:
        atualizar_texto("Encerrando MetaTrader por gain.")
        time.sleep(5)
        mt5.shutdown()

    if 'lucro_total' in locals() and lucro_total <= StopLossDia:
        atualizar_texto("Encerrando MetaTrader por loss.")
        time.sleep(5)
        mt5.shutdown()
#------------------------------------------------------------------
#                  Loop Principal para Executar a Estratégia
#------------------------------------------------------------------
def iniciar_estrategia():
    global estrategia_ativa
    obter_parametros()  # Obter os parâmetros inseridos pelo usuário
    while estrategia_ativa:
        hora_atual = datetime.now().hour

        if hora_atual >= 9 and hora_atual < 23:  # Horário de operação (10h às 18h)
            ticker = AtivoAoperar
            intervalo = mt5.TIMEFRAME_M5
            data_final = datetime.today()
            data_inicial = datetime.today() - timedelta(days=6)
            mt5.symbol_select(ticker)
            preco_inicial = mt5.symbol_info(ticker).ask
            while estrategia_ativa:
                preco_atual = mt5.symbol_info(ticker).ask
                dados_atualizados = pegando_dados(ticker, intervalo, data_inicial, data_final)
                
                estrategia_trade(dados_atualizados, ticker)
                atualizar_texto(f"Preço Atual: {preco_atual}")
                obter_lucro_diario()  
                # Monitora o preço e ajusta Stop Loss após subir 100 pontos (comprado) ou descer 100 pontos (vendido)
                if tipo_posicao == "comprado" and preco_atual >= preco_inicial + AcionarNovoStop:
                    modificar_stop(ticker, novo_stop_loss, novo_stop_gain)
                    preco_inicial = preco_atual  # Atualizando o preço inicial após reajustar o Stop Loss
                elif tipo_posicao == "vendido" and preco_atual <= preco_inicial - AcionarNovoStop:
                    modificar_stop(ticker, novo_stop_loss, novo_stop_gain)
                    preco_inicial = preco_atual  # Atualizando o preço inicial após reajustar o Stop Loss

                time.sleep(60 * Atualizar)
        else:
            # Fora do horário de operação, pausa a execução
            atualizar_texto("Fora do horário de operação. Aguardando 60 segundos para tentar novamente.")
            time.sleep(60)  # Aguardar 60 segundos antes de verificar novamente

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
        atualizar_texto("Estratégia iniciada.")
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

