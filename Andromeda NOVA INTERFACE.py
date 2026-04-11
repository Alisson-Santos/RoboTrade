import MetaTrader5 as mt5
import pandas as pd
import time
import tkinter as tk
from tkinter import messagebox
from datetime import datetime, timedelta
from threading import Thread
import traceback

#------------------------------------------------------------------
#                  Inicialização do MT5 
#------------------------------------------------------------------

global mt5_conectado
mt5_conectado = mt5.initialize()

if not mt5_conectado:
    print("ERRO CRÍTICO: MetaTrader 5 não inicializado.")
else:
    print("MetaTrader 5 inicializado com sucesso.")

estrategia_ativa = False
tipo_posicao = None 
preco_inicial = 0.0 

#------------------------------------------------------------------
#                  Variáveis de Controle (Globais)
#------------------------------------------------------------------
root = tk.Tk()
root.title("Robo Trader - Andromeda 3.8")

# Risco
usar_limite_vitorias = tk.BooleanVar(value=False)
usar_limite_derrotas = tk.BooleanVar(value=False)
limite_vitorias = tk.IntVar(value=0)
limite_derrotas = tk.IntVar(value=0)

# Horário
hora_inicio = tk.IntVar(value=10)
min_inicio = tk.IntVar(value=30)
hora_fim = tk.IntVar(value=17)
min_fim = tk.IntVar(value=0)

# Ajuste de Stop
acionar_novo_stop = tk.DoubleVar(value=125.0)
novo_stop_gain = tk.DoubleVar(value=175.0)
novo_stop_loss = tk.DoubleVar(value=100.0)

#------------------------------------------------------------------
#                  Funções das Janelas Secundárias
#------------------------------------------------------------------

def atualizar_resumos():
    """Atualiza as informações resumidas na tela principal"""
    txt_h = f"Horário: {hora_inicio.get():02d}:{min_inicio.get():02d} às {hora_fim.get():02d}:{min_fim.get():02d}"
    label_resumo_horario.config(text=txt_h)
    
    txt_s = f"Stop Móvel: Acionar:{acionar_novo_stop.get()} | Gain:{novo_stop_gain.get()} | Loss:{novo_stop_loss.get()}"
    label_resumo_stop.config(text=txt_s)

def abrir_janela_risco():
    win = tk.Toplevel(root)
    win.title("Gestão de Risco")
    win.geometry("300x200")
    tk.Label(win, text="Limites de Operações", font=("Arial", 10, "bold")).pack(pady=10)
    
    f1 = tk.Frame(win); f1.pack(fill="x", padx=20)
    tk.Checkbutton(f1, text="Parar após vitórias:", variable=usar_limite_vitorias).pack(side="left")
    tk.Entry(f1, textvariable=limite_vitorias, width=5).pack(side="right")
    
    f2 = tk.Frame(win); f2.pack(fill="x", padx=20, pady=10)
    tk.Checkbutton(f2, text="Parar após derrotas:", variable=usar_limite_derrotas).pack(side="left")
    tk.Entry(f2, textvariable=limite_derrotas, width=5).pack(side="right")
    
    tk.Button(win, text="Confirmar", command=win.destroy, bg="#5cb85c", fg="white").pack()

def abrir_janela_horario():
    win = tk.Toplevel(root)
    win.title("Horário de Funcionamento")
    win.geometry("250x180")
    
    tk.Label(win, text="Início (Hora : Min)").pack(pady=5)
    f_i = tk.Frame(win); f_i.pack()
    tk.Entry(f_i, textvariable=hora_inicio, width=5).pack(side="left")
    tk.Label(f_i, text=":").pack(side="left")
    tk.Entry(f_i, textvariable=min_inicio, width=5).pack(side="left")
    
    tk.Label(win, text="Fim (Hora : Min)").pack(pady=5)
    f_f = tk.Frame(win); f_f.pack()
    tk.Entry(f_f, textvariable=hora_fim, width=5).pack(side="left")
    tk.Label(f_f, text=":").pack(side="left")
    tk.Entry(f_f, textvariable=min_fim, width=5).pack(side="left")
    
    tk.Button(win, text="Salvar", command=lambda:[win.destroy(), atualizar_resumos()]).pack(pady=10)

def abrir_janela_ajuste_stop():
    win = tk.Toplevel(root)
    win.title("Configurar Ajuste de Stop")
    win.geometry("280x220")
    
    tk.Label(win, text="Acionar Novo Stop (pontos):").pack(pady=2)
    tk.Entry(win, textvariable=acionar_novo_stop).pack()
    
    tk.Label(win, text="Novo Stop Gain (pontos):").pack(pady=2)
    tk.Entry(win, textvariable=novo_stop_gain).pack()
    
    tk.Label(win, text="Novo Stop Loss (pontos):").pack(pady=2)
    tk.Entry(win, textvariable=novo_stop_loss).pack()
    
    tk.Button(win, text="Salvar", command=lambda:[win.destroy(), atualizar_resumos()]).pack(pady=10)

#------------------------------------------------------------------
#                  Lógica de Negócio e Monitoramento
#------------------------------------------------------------------

def obter_lucro_diario():
    global AtivoAoperar, StopGainDia, StopLossDia, label_pl_aberto, label_pl_fechado, estrategia_ativa
    
    lucro_realizado = 0.0
    wins, losses = 0, 0
    hoje = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    deals = mt5.history_deals_get(hoje, datetime.now())
    if deals:
        for d in deals:
            if d.entry == mt5.DEAL_ENTRY_OUT and d.symbol == AtivoAoperar:
                lucro_realizado += d.profit
                if d.profit > 0: wins += 1
                elif d.profit < 0: losses += 1
    
    posicoes = mt5.positions_get(symbol=AtivoAoperar)
    lucro_aberto = sum(p.profit for p in posicoes) if posicoes else 0.0

    label_pl_aberto.config(text=f"P/L Aberto: R$ {lucro_aberto:.2f}")
    label_pl_fechado.config(text=f"P/L Fechado: R$ {lucro_realizado:.2f} | Vitórias: {wins} | Derrotas: {losses}")

    # Verificação de Risco
    if usar_limite_vitorias.get() and wins >= limite_vitorias.get() and limite_vitorias.get() > 0:
        messagebox.showinfo("Risco", f"Meta de vitórias ({wins}) atingida!"); parar_por_seguranca()
    elif usar_limite_derrotas.get() and losses >= limite_derrotas.get() and limite_derrotas.get() > 0:
        messagebox.showwarning("Risco", f"Limite de derrotas ({losses}) atingido!"); parar_por_seguranca()
    elif lucro_realizado >= StopGainDia or lucro_realizado <= StopLossDia:
        messagebox.showwarning("Risco", "Stop Financeiro Diário atingido!"); parar_por_seguranca()

def parar_por_seguranca():
    global estrategia_ativa
    if estrategia_ativa:
        fechar_posicao_mt5(AtivoAoperar)
        estrategia_ativa = False
        atualizar_botoes()

#------------------------------------------------------------------
#                  Interface Gráfica Principal
#------------------------------------------------------------------

def criar_interface_parametros():
    frame = tk.Frame(root)
    frame.pack(padx=10, pady=5, fill=tk.BOTH)
    
    tk.Label(frame, text="Configurações do Ativo", font=("Arial", 12, "bold")).grid(row=0, column=0, columnspan=2, pady=5)
    
    global entries
    entries = {}
    params = {
        "Ativo a Operar": "WINZ25", "Contratos": 1.0,
        "Média Móvel Rápida": 17, "Média Móvel Lenta": 72,
        "Stop Gain (Pontos)": 500, "Stop Loss (Pontos)": 125,
        "Stop Gain (Dia R$)": 180.0, "Stop Loss (Dia R$)": -60.0
    }
    
    for i, (k, v) in enumerate(params.items()):
        tk.Label(frame, text=f"{k}:").grid(row=i+1, column=0, sticky="e", padx=5)
        e = tk.Entry(frame); e.insert(0, str(v)); e.grid(row=i+1, column=1, sticky="w", padx=5)
        entries[k] = e

    global label_pl_aberto, label_pl_fechado, label_resumo_horario, label_resumo_stop
    
    # Monitoramento
    label_pl_aberto = tk.Label(root, text="P/L Aberto: R$ 0.00", fg="blue", font=("Arial", 10, "bold"))
    label_pl_aberto.pack(pady=2)
    label_pl_fechado = tk.Label(root, text="P/L Fechado: R$ 0.00", fg="darkgreen", font=("Arial", 10, "bold"))
    label_pl_fechado.pack(pady=2)
    
    # Resumos das Janelas
    label_resumo_horario = tk.Label(root, text="", font=("Arial", 9, "italic"), fg="#555")
    label_resumo_horario.pack()
    label_resumo_stop = tk.Label(root, text="", font=("Arial", 9, "italic"), fg="#555")
    label_resumo_stop.pack()
    
    atualizar_resumos()

def obter_parametros():
    global AtivoAoperar, Contratos, mediaMovelRapida, mediaMovelLenta, StopGain, StopLoss, StopGainDia, StopLossDia
    global HoraInicio, MinInicio, HoraFim, MinFim, AcionarNovoStop, NovoStopGain, NovoStopLoss
    
    # Campos da tela principal
    AtivoAoperar = entries["Ativo a Operar"].get()
    Contratos = float(entries["Contratos"].get())
    mediaMovelRapida = int(entries["Média Móvel Rápida"].get())
    mediaMovelLenta = int(entries["Média Móvel Lenta"].get())
    StopGain = float(entries["Stop Gain (Pontos)"].get())
    StopLoss = float(entries["Stop Loss (Pontos)"].get())
    StopGainDia = float(entries["Stop Gain (Dia R$)"].get())
    StopLossDia = float(entries["Stop Loss (Dia R$)"].get())
    
    # Campos das janelas (variáveis globais tk)
    HoraInicio = hora_inicio.get()
    MinInicio = min_inicio.get()
    HoraFim = hora_fim.get()
    MinFim = min_fim.get()
    AcionarNovoStop = acionar_novo_stop.get()
    NovoStopGain = novo_stop_gain.get()
    NovoStopLoss = novo_stop_loss.get()

#------------------------------------------------------------------
#                  Controles de Execução
#------------------------------------------------------------------

frame_botoes = tk.Frame(root)
frame_botoes.pack(pady=10, fill=tk.X)

def iniciar_robo():
    global estrategia_ativa
    if not estrategia_ativa:
        estrategia_ativa = True
        atualizar_botoes()
        Thread(target=loop_principal, daemon=True).start()

def atualizar_botoes():
    btn_iniciar.config(state=tk.DISABLED if estrategia_ativa else tk.NORMAL)
    btn_pausar.config(state=tk.NORMAL if estrategia_ativa else tk.DISABLED)

btn_iniciar = tk.Button(frame_botoes, text="▶ Iniciar", command=iniciar_robo, bg="#d9ffdb", width=10)
btn_iniciar.pack(side=tk.LEFT, padx=5, expand=True)

tk.Button(frame_botoes, text="🛡️ Risco", command=abrir_janela_risco, width=10).pack(side=tk.LEFT, padx=2)
tk.Button(frame_botoes, text="🕒 Horário", command=abrir_janela_horario, width=10).pack(side=tk.LEFT, padx=2)
tk.Button(frame_botoes, text="🛑 Stop", command=abrir_janela_ajuste_stop, width=10).pack(side=tk.LEFT, padx=2)

btn_pausar = tk.Button(frame_botoes, text="⏸ Pausar", command=parar_por_seguranca, bg="#ffdbdb", width=10)
btn_pausar.pack(side=tk.LEFT, padx=5, expand=True)

texto_log = tk.Text(root, height=8, width=80, font=("Consolas", 9))
texto_log.pack(padx=10, pady=10)

def atualizar_texto(msg):
    texto_log.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")
    texto_log.see(tk.END)

# --- Loop da Estratégia ---
def loop_principal():
    obter_parametros()
    atualizar_texto(f"Robô iniciado no ativo {AtivoAoperar}")
    while estrategia_ativa:
        try:
            obter_lucro_diario()
            # Inserir aqui a chamada das suas funções de estratégia (Cruzamento/Martelo/etc)
            time.sleep(1)
        except Exception as e:
            atualizar_texto(f"Erro no loop: {e}")
            break

# Funções de Fechamento MT5 (Devem ser mantidas as originais do seu script)
def fechar_posicao_mt5(ativo):
    positions = mt5.positions_get(symbol=ativo)
    if not positions: return
    for p in positions:
        tick = mt5.symbol_info_tick(ativo)
        request = {
            "action": mt5.TRADE_ACTION_DEAL, "symbol": ativo, "volume": p.volume,
            "type": mt5.ORDER_TYPE_SELL if p.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY,
            "position": p.ticket, "price": tick.bid if p.type == mt5.ORDER_TYPE_BUY else tick.ask,
            "deviation": 10, "magic": 123456, "comment": "Close Risk",
            "type_time": mt5.ORDER_TIME_GTC, "type_filling": mt5.ORDER_FILLING_RETURN,
        }
        mt5.order_send(request)

criar_interface_parametros()
root.mainloop()