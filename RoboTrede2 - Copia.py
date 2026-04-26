import tkinter as tk
import MetaTrader5 as mt5 # Importação necessária para o projeto

# Variáveis de funcionamento
horaInicio = 10
minutoInicio = 00
horaFim = 14
minutoFim = 00

# Criando a janela principal
root = tk.Tk()
root.title("Robo Trader - Andromeda 3.7")
root.geometry("400x500")

def criar_interface_parametros():
    # Frame para organizar os parâmetros gerais
    frame_parametros = tk.Frame(root)    
    frame_parametros.pack(padx=20, pady=10, fill=tk.X) # Removido expand=True para não empurrar o resto

    # Corrigido: sticky="w" para alinhar à esquerda ou remova para centralizar
    tk.Label(frame_parametros, text="Configurações Do Robo", font=("Arial", 12, "bold")).grid(row=0, column=0, pady=10)
    
    # --- Coluna Horário ---
    frame_horario = tk.Frame(root, bd=1, relief=tk.SOLID) # Adicionado relevo para ver a divisão
    frame_horario.pack(padx=10, pady=10, fill=tk.X)
    
    tk.Label(frame_horario, text="Configurações De Horário", font=("Arial", 11, "bold")).grid(row=0, column=0, columnspan=2, pady=10)

    # Coluna Início
    tk.Label(frame_horario, text="Início:").grid(row=1, column=0, sticky="e", padx=5)
    tk.Label(frame_horario, text=f"{horaInicio:02d}:{minutoInicio:02d}", fg="blue").grid(row=1, column=1, sticky="w")

    # Coluna Fim
    tk.Label(frame_horario, text="Término:").grid(row=2, column=0, sticky="e", padx=5)
    tk.Label(frame_horario, text=f"{horaFim:02d}:{minutoFim:02d}", fg="red").grid(row=2, column=1, sticky="w")

    # Centraliza as colunas no frame
    frame_horario.grid_columnconfigure(0, weight=1)
    frame_horario.grid_columnconfigure(1, weight=1)

# Chamadas de funções
criar_interface_parametros()

# Lembre-se de inicializar o MT5 aqui antes do mainloop se for rodar o robô
# mt5.initialize()

root.mainloop()