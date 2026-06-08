# Estado em Memória

Na Entrega 1, o RescueRadio mantém o estado principal em memória dentro da API FastAPI.

## Objetivo

O estado em memória permite:

- controlar conexões WebSocket ativas por canal;
- listar membros online;
- armazenar as últimas mensagens para o briefing;
- remover membros quando uma conexão é encerrada.

## Estruturas principais

### `connections`

Armazena as conexões WebSocket por canal e usuário.

```python
connections = {
    "canal-geral": {
        "Lucas": websocket
    }
}
```

Se o mesmo usuário conectar novamente ao mesmo canal, a conexão antiga é fechada e substituída pela nova.

### `active_members`

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

Essa estrutura é usada para enviar a lista de membros nos eventos `MEMBER_JOINED` e `MEMBER_LEFT`.

### `message_buffer`

Armazena o histórico recente de mensagens por canal.

```python
message_buffer = {
    "canal-geral": deque(maxlen=50)
}
```

O tamanho definido para a Entrega 1 é `50` mensagens por canal.

## Briefing

Quando um usuário entra no canal, a API envia um evento `BRIEFING` contendo o conteúdo atual do `message_buffer`.

Se ainda não houver mensagens, o briefing é enviado com a lista vazia:

```json
{
  "type": "BRIEFING",
  "channel_id": "canal-geral",
  "messages": []
}
```

## Desconexão

Quando uma conexão WebSocket é encerrada, a API:

1. remove o usuário de `connections`;
2. remove o usuário de `active_members`;
3. envia um evento `MEMBER_LEFT` para os membros restantes do canal.

Durante o broadcast, a API também remove conexões que falham ao receber mensagens.

## Limitações

Como o estado está em memória:

- os dados são perdidos ao reiniciar a API;
- não há histórico persistente;
- não há compartilhamento de estado entre múltiplas instâncias da API.

Persistência e estado distribuído ficam planejados para entregas futuras com PostgreSQL, Redis e Kafka.
