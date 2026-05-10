# RescueRadio

Central de comunicação (estilo “rádio digital”) via TCP, voltada para cenários de resposta a incidentes/resgate. Inclui:

- Servidor de canal (broadcast + histórico/briefing)
- Cliente de terminal com reconexão e comandos
- Autenticação de operadores com senha hasheada (PBKDF2-HMAC-SHA256)
- Painel administrativo para cadastrar/remover operadores

> Nota importante: este projeto **não implementa criptografia/TLS**. A autenticação protege o acesso ao canal, mas o tráfego ainda pode ser interceptado em redes não confiáveis. Para uso real em campo, execute atrás de **VPN**, **SSH tunnel** ou implemente **TLS**.

## Estrutura do repositório

- `server.py`: servidor TCP do canal (broadcast, histórico, comandos)
- `client.py`: cliente de terminal (handshake síncrono + loop de chat)
- `auth.py`: gerenciamento de credenciais (PBKDF2 + salt por usuário)
- `admin.py`: painel administrativo (login via `.env` + CRUD de operadores)
- `.env.example`: exemplo de variáveis para acesso ao painel admin
- `users.json`: banco local de operadores (gerado/atualizado pelo `admin.py`)

## Requisitos

- Python 3.10+ (recomendado)
- Dependência: `python-dotenv` (usada somente no `admin.py`)

## Instalação (Windows / PowerShell)

Crie e ative um ambiente virtual:

```powershell
py -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
```

Instale a dependência:

```powershell
pip install -r requirements.txt
```

Alternativa (equivalente):

```powershell
pip install python-dotenv
```

## Configuração do painel administrativo

1) Copie o arquivo de exemplo:

```bash
cp .env.example .env
```

No Windows (Prompt/PowerShell), você também pode usar:

```powershell
copy .env.example .env
```

2) Edite `.env` e defina:

- `ADMIN_USER`
- `ADMIN_PASSWORD` (troque o valor padrão por uma senha forte)

O `admin.py` **não** roda sem `.env` válido.

## Como usar

### 1) Cadastrar operadores (obrigatório antes de conectar clientes)

Abra um terminal e rode:

```bash
py admin.py
```

Faça login com o usuário/senha do `.env` e use o menu para:

- Cadastrar operador (role padrão: `operador`)
- Listar operadores
- Remover operador
- Redefinir senha

Atalhos por comando:

```bash
py admin.py add
py admin.py list
py admin.py remove
py admin.py reset
```

As credenciais dos operadores ficam em `users.json` (com `salt` + `hash`, sem senha em texto plano).

### 2) Subir o servidor

Em outro terminal:

```bash
py server.py
```

Por padrão, o servidor escuta em `0.0.0.0:12345`.

### 3) Conectar clientes

Em cada máquina/terminal de operador:

```bash
py client.py
```

Para apontar para outro host/porta:

```bash
py client.py 192.168.0.10 12345
```

O cliente fará o handshake de autenticação (usuário e senha) e, ao entrar, receberá um **briefing** com as últimas mensagens.

## Comandos no chat

Comandos que o servidor entende:

- `/membros` — lista membros conectados
- `/ajuda` — exibe ajuda do servidor
- `/sair` — encerra a conexão

Comando local do cliente:

- `/help` — exibe a ajuda local (não envia ao servidor)

## Notas de segurança e operação

- **Sem criptografia**: use VPN/SSH/TLS se estiver em rede não confiável.
- Tentativas de login: o servidor bloqueia após `3` tentativas por conexão.
- Hashing: PBKDF2-HMAC-SHA256 com `salt` aleatório por usuário e `260000` iterações.
- Backup: faça backup do `users.json` se não quiser perder cadastros.
- Segredos: não commite `.env` nem `users.json` (já estão no `.gitignore`).

## Troubleshooting

- “Nenhum operador cadastrado”: rode `py admin.py add` antes de conectar.
- “Servidor recusou a conexão”: verifique IP/porta e se o `server.py` está rodando.
- Problema ao ativar venv no Windows: rode `Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned` na sessão atual.