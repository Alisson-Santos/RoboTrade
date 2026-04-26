import tkinter as tk

#   inicializar o mt5

# horario de funcionametno
horaInicio = 10
minutoInicio = 00
horaFim = 14
minutoFim = 00


# Criando a janela principal
root = tk.Tk()
root.title("Robo Trader - Andromeda 3.7")
root.geometry("400x500")

def criar_interface_parametros():
    # Frame para organizar os parâmetros
    frame_parametros = tk.Frame(root)    
    # Empacota o frame com preenchimento (fill) e expansão para que ele redimensione com a janela
    frame_parametros.pack(padx=20, pady=20, fill=tk.BOTH, expand=True)
    #label
    tk.Label(frame_parametros, text= "Configurações Do Robo"). grid(row=0, column=0, sticky= "W" )
    
#coluna horario 
    frame_horario = tk.Frame(root, bd=1,)
    frame_horario.pack(padx=10, pady=20, fill=tk.X)
    tk.Label(frame_horario, text= "Horario de funcionamento"). grid(row=1, column=2, sticky= "W" )
    
    
    
#chamadas de funções
criar_interface_parametros()


root.mainloop()

