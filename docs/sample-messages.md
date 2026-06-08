# Exemplos de Mensagens

Este documento reúne exemplos de payloads para testar e apresentar o protocolo da Entrega 1.

## Mensagem válida

```json
{
  "type": "SEND_MESSAGE",
  "usuario": "Lucas",
  "timestamp_iso": "2026-06-04T21:30:00Z",
  "corpo_texto": "Equipe Alfa chegou ao ponto de encontro."
}
```

## Mensagem válida com outro usuário

```json
{
  "type": "SEND_MESSAGE",
  "usuario": "Marcelo",
  "timestamp_iso": "2026-06-04T21:31:00Z",
  "corpo_texto": "Equipe Bravo iniciando varredura no setor norte."
}
```

## Mensagem válida para briefing

```json
{
  "type": "SEND_MESSAGE",
  "usuario": "Júlia",
  "timestamp_iso": "2026-06-04T21:32:00Z",
  "corpo_texto": "Briefing recebido. Seguindo para o ponto de apoio."
}
```

## Tipo inválido

```json
{
  "type": "INVALID_MESSAGE",
  "usuario": "Lucas",
  "timestamp_iso": "2026-06-04T21:30:00Z",
  "corpo_texto": "Esta mensagem deve retornar erro."
}
```

Resultado esperado:

```json
{
  "type": "ERROR",
  "channel_id": "canal-geral",
  "message": "Tipo de mensagem inválido: INVALID_MESSAGE"
}
```

## Timestamp inválido

```json
{
  "type": "SEND_MESSAGE",
  "usuario": "Lucas",
  "timestamp_iso": "04/06/2026 21:30",
  "corpo_texto": "Esta mensagem deve retornar erro de timestamp."
}
```

Resultado esperado:

```json
{
  "type": "ERROR",
  "channel_id": "canal-geral",
  "message": "timestamp_iso deve estar no formato ISO 8601"
}
```

## Texto vazio

```json
{
  "type": "SEND_MESSAGE",
  "usuario": "Lucas",
  "timestamp_iso": "2026-06-04T21:30:00Z",
  "corpo_texto": ""
}
```

Resultado esperado:

```json
{
  "type": "ERROR",
  "channel_id": "canal-geral",
  "message": "Mensagem de validação informando erro no campo corpo_texto"
}
```
