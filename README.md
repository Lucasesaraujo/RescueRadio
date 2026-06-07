# RescueRadio

**Equipe 11 - Central de Comunicação de Equipe de Resgate**

O RescueRadio é um sistema de comunicação em tempo real para equipes de resgate. A proposta é simular um canal de rádio digital via texto, permitindo que socorristas conectados a um mesmo canal enviem mensagens, recebam atualizações em tempo real e recebam automaticamente um briefing com as últimas mensagens ao entrar.

## Objetivo da Entrega 1

A Entrega 1 tem como foco a definição da arquitetura, organização inicial do repositório, protocolo de comunicação, estado central em memória e servidor base funcionando com WebSocket.

Nesta versão, o sistema já possui:

- API FastAPI funcionando;
- rota de health check;
- WebSocket por canal;
- broadcast de mensagens;
- buffer circular de histórico;
- briefing automático ao entrar no canal;
- entrada e saída de membros;
- validação básica de mensagens;
- frontend Angular simples;
- Kong como gateway/middleware;
- execução com Docker Compose.

## Arquitetura da Entrega 1

```text
Angular Web App
      ↓
Kong Gateway
      ↓
FastAPI WebSocket API
      ↓
Estado em memória
```

## Tecnologias utilizadas

| Tecnologia | Papel |
| --- | --- |
| Angular | Interface gráfica do usuário |
| FastAPI | API principal e WebSocket |
| WebSocket | Comunicação em tempo real |
| Kong | Middleware/API Gateway |
| Docker Compose | Execução local dos serviços |
| Python | Lógica do backend |
| TypeScript | Lógica do frontend |

## Estrutura do projeto

```text
RescueRadio/
├── apps/
│   └── web/                  # Aplicação Angular
├── services/
│   └── api/                  # API FastAPI + WebSocket
├── infra/
│   ├── docker/               # Dockerfiles
│   └── kong/                 # Configuração do Kong
├── docs/                     # Documentação do projeto
├── contracts/                # Contratos futuros de comunicação
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

## Como rodar o projeto

### Pré-requisitos

É necessário ter instalado:

- Docker;
- Docker Compose;
- Git.

### Subir os serviços

Na raiz do projeto, execute:

```bash
docker compose up --build
```

Após subir, acesse:

| Serviço | URL |
| --- | --- |
| Frontend Angular | <http://localhost:4200> |
| API FastAPI direta | <http://localhost:8000/health> |
| API via Kong | <http://localhost:8001/health> |

## Fluxo principal

1. O usuário acessa o frontend Angular.
2. Informa seu nome.
3. Entra no canal geral.
4. O Angular abre uma conexão WebSocket passando pelo Kong.
5. A API FastAPI registra o usuário como membro ativo.
6. O usuário recebe um briefing com as últimas mensagens do canal.
7. Ao enviar uma mensagem, a API retransmite para todos os membros conectados.
8. Ao sair, o sistema emite um evento de saída.

## Protocolo de comunicação

### Envio de mensagem

```json
{
  "type": "SEND_MESSAGE",
  "usuario": "Lucas",
  "timestamp_iso": "2026-06-04T21:30:00Z",
  "corpo_texto": "Equipe Alfa chegou ao ponto de encontro."
}
```

### Evento de mensagem recebida

```json
{
  "type": "MESSAGE_RECEIVED",
  "channel_id": "canal-geral",
  "payload": {
    "type": "SEND_MESSAGE",
    "usuario": "Lucas",
    "timestamp_iso": "2026-06-04T21:30:00Z",
    "corpo_texto": "Equipe Alfa chegou ao ponto de encontro."
  }
}
```

### Evento de briefing

```json
{
  "type": "BRIEFING",
  "channel_id": "canal-geral",
  "messages": []
}
```

### Evento de entrada de membro

```json
{
  "type": "MEMBER_JOINED",
  "channel_id": "canal-geral",
  "usuario": "Lucas",
  "timestamp_iso": "2026-06-04T21:30:00Z",
  "members": [
    {
      "usuario": "Lucas",
      "status": "online"
    }
  ],
  "message": "Lucas entrou no canal."
}
```

### Evento de saída de membro

```json
{
  "type": "MEMBER_LEFT",
  "channel_id": "canal-geral",
  "usuario": "Lucas",
  "timestamp_iso": "2026-06-04T21:35:00Z",
  "members": [],
  "message": "Lucas saiu do canal."
}
```

### Evento de erro

```json
{
  "type": "ERROR",
  "channel_id": "canal-geral",
  "message": "Payload inválido"
}
```

## Estado em memória

Nesta entrega, o estado principal ainda é mantido em memória dentro da API.

### Conexões WebSocket

Armazena os usuários conectados por canal.

```python
connections = {
    "canal-geral": {
        "Lucas": websocket
    }
}
```

### Membros ativos

Armazena os membros online por canal.

```python
active_members = {
    "canal-geral": {
        "Lucas": {
            "usuario": "Lucas",
            "status": "online"
        }
    }
}
```

### Buffer circular

Armazena as últimas 50 mensagens do canal para enviar como briefing a novos membros.

```python
message_buffer = {
    "canal-geral": deque(maxlen=50)
}
```

## Validações implementadas

O backend valida:

- `type` obrigatório e permitido;
- `usuario` obrigatório;
- `timestamp_iso` em formato ISO;
- `corpo_texto` obrigatório;
- tamanho máximo da mensagem.

Mensagens inválidas retornam um evento `ERROR`.


## Próximas evoluções

Para as próximas entregas, estão planejados:

- autenticação JWT;
- roles de usuário;
- mensagens críticas com ACK;
- integração com PostgreSQL;
- integração com Redis;
- integração com Kafka;
- observabilidade com Prometheus, Grafana e Loki;
- testes de carga;
- melhoria da interface gráfica.
