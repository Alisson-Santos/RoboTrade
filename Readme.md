Andromeda 3.7 - Robo Trader para MetaTrader 5
O Andromeda 3.7 é um robô de negociação automatizada (Expert Advisor em Python) que utiliza o cruzamento de Médias Móveis e um sistema de Trailing Stop dinâmico para operar ativos na plataforma MetaTrader 5. Ele possui uma interface gráfica (GUI) intuitiva para ajuste de parâmetros em tempo real.

🚀 Funcionalidades
Estratégia de Médias Móveis: Opera baseado no cruzamento de uma média rápida e uma média lenta.

Trailing Stop Customizado: Sistema que ajusta automaticamente o Stop Loss e Take Profit conforme o preço se move a favor da operação.

Gestão de Risco Diária: Encerra as atividades automaticamente ao atingir o Stop Gain ou Stop Loss financeiro do dia (Lucro Realizado).

Interface Gráfica (Tkinter): Permite configurar ativos, quantidade de contratos, horários de operação e níveis de stop sem precisar mexer no código.

Multithreading: A lógica de execução roda em uma thread separada, mantendo a interface gráfica sempre responsiva.

Logs em Tempo Real: Monitoramento detalhado de cada ação do robô diretamente na janela do aplicativo.

🛠️ Pré-requisitos
Antes de iniciar, você precisará ter instalado:

Python 3.8 ou superior.

Terminal MetaTrader 5 instalado e conectado à sua conta (Demo ou Real).

Bibliotecas Python necessárias:

pip install MetaTrader5 pandas

Parâmetro,Descrição
Ativo a Operar,    "Código do ativo no MT5 (Ex: WINJ26, WDOJ26, PETR4)."
Contratos,    Volume da posição (lotes).
Médias (Rápida/Lenta),    Período das médias móveis para o sinal de entrada.
Stop Gain/Loss (Pontos),    Alvos iniciais da operação.
Stop Gain/Loss (Dia),Limites financeiros (em R$) para parar o robô no dia.
Acionar Novo Stop,Quantos pontos a favor o preço deve andar para mover o stop.
Atualizar Operação,Intervalo em minutos para checagem de sinal de entrada.
Horário Início/Fim,Janela de tempo permitida para abertura de novas ordens.

📦 Como Usar
Abra o seu terminal MetaTrader 5.

Certifique-se de que a opção "Negociação Algorítmica" esteja ativada no topo do terminal.

Execute o script Python:

python "Andromeda 3.7.py"

Configure os parâmetros na janela que aparecerá.

Clique em "Iniciar Estratégia".

⚠️ Avisos e Erros Comuns
Conexão MT5: Se o robô exibir um erro de inicialização, verifique se o terminal MT5 está aberto e se você está logado em uma conta ativa.

Ativo não encontrado: Verifique se o ativo digitado (ex: WINJ26) está visível na "Observação de Mercado" do seu MT5.

Preenchimento de Ordem: O código usa ORDER_FILLING_RETURN. Dependendo da sua corretora, pode ser necessário alterar para ORDER_FILLING_IOC ou ORDER_FILLING_FOK.

🛑 Isenção de Responsabilidade
A negociação de ativos financeiros envolve riscos significativos. Este software foi desenvolvido para fins educacionais e de automação. O autor não se responsabiliza por eventuais perdas financeiras decorrentes do uso deste robô. Sempre teste suas estratégias em conta DEMO antes de operar no mercado real.

Desenvolvido por: [Alisson /Allnix]

Versão: 3.7 (Estável)
