# VisioVoz CAA

Aplicação de comunicação aumentativa e alternativa com interface PyQt6 e
rastreamento ocular por webcam.

## Requisitos

- Python 3.10 a 3.12.
- Webcam conectada e acessível pelo sistema.
- Conexão com a internet para a síntese de voz neural (`edge-tts`).
- Saída de áudio para ouvir voz e sons da interface.

As dependências Python estão listadas em [`requirements.txt`](./requirements.txt).

## Instalação

Abra um terminal na pasta do projeto e crie um ambiente virtual:

```bash
python -m venv .venv
```

Ative o ambiente virtual.

Linux ou macOS:

```bash
source .venv/bin/activate
```

Windows (PowerShell):

```powershell
.\.venv\Scripts\Activate.ps1
```

Com o ambiente ativo, instale as dependências:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Executar

Com o ambiente virtual ativado:

```bash
python main.py
```

Permita o acesso à webcam se o sistema solicitar. Em Linux, caso haja erros ao
abrir a interface ou reproduzir áudio, instale também as bibliotecas de sistema
necessárias pelo gerenciador de pacotes da sua distribuição (Qt e SDL/áudio).

## Calibração ocular (opcional)

Para executar o utilitário de calibração:

```bash
python calibrate.py
```

Siga os pontos exibidos na tela. Ao concluir, o programa salva os dados em
`calibration_data.json` na pasta atual. Pressione `Esc` para sair antes de
terminar.