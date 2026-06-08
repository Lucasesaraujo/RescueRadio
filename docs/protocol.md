# Protocolo de Comunicação

Este documento registra o protocolo atual de comunicação WebSocket do RescueRadio.

## Endpoint

```text
ws://localhost:8001/ws/channel/{channel_id}?usuario={usuario}
```

Na execução com Docker Compose, o cliente usa o Kong em `localhost:8001`.

Parâmetros:

| Campo | Origem | Descrição |
| --- | --- | --- |
| `channel_id` | path | Identificador do canal. Na interface atual, o valor padrão é `canal-geral`. |
| `usuario` | query | Nome do socorrista que está entrando no canal. |

## Mensagem enviada pelo cliente

```json
{
  "type": "SEND_MESSAGE",
  "usuario": "Lucas",
  "timestamp_iso": "2026-06-04T21:30:00Z",
  "corpo_texto": "Equipe Alfa chegou ao ponto de encontro."
}
```

Validações principais:

- `type` deve ser `SEND_MESSAGE`;
- `usuario` é obrigatório e deve ter até 80 caracteres;
- `timestamp_iso` deve estar em formato ISO 8601;
- `corpo_texto` é obrigatório e deve ter até 500 caracteres.

## Eventos enviados pelo servidor

### `CONNECTED`

Confirma que a conexão WebSocket foi aceita.

```json
{
  "type": "CONNECTED",
  "channel_id": "canal-geral",
  "usuario": "Lucas",
  "message": "Conectado ao canal com sucesso."
}
```

### `BRIEFING`

Envia as últimas mensagens armazenadas no buffer circular do canal.

```json
{
  "type": "BRIEFING",
  "channel_id": "canal-geral",
  "messages": []
}
```

### `MESSAGE_RECEIVED`

Retransmite uma mensagem válida para os membros conectados ao canal.

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

### `MEMBER_JOINED`

Informa que um membro entrou no canal e envia a lista atual de membros.

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

### `MEMBER_LEFT`

Informa que um membro saiu do canal e envia a lista atualizada de membros.

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

### `ERROR`

Indica que o payload enviado pelo cliente é inválido.

```json
{
  "type": "ERROR",
  "channel_id": "canal-geral",
  "message": "Payload inválido"
}
```
