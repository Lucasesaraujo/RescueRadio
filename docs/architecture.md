# Arquitetura da Entrega 1

Este documento descreve a arquitetura atual do RescueRadio para a Entrega 1.

## Visão geral

```text
Angular Web App
      ↓
Kong Gateway
      ↓
FastAPI WebSocket API
      ↓
Estado em memória
```

O objetivo desta arquitetura é demonstrar comunicação em tempo real entre múltiplos clientes usando WebSocket, com um ponto central de entrada via Kong e estado mantido no backend.

## Componentes

| Componente | Responsabilidade |
| --- | --- |
| Angular Web App | Interface do usuário, entrada no canal, envio e exibição de mensagens, membros e eventos. |
| Kong Gateway | Gateway/middleware que encaminha HTTP e WebSocket para a API. |
| FastAPI WebSocket API | Health check, endpoint WebSocket, validação de mensagens, broadcast, briefing e presença. |
| Estado em memória | Armazena conexões ativas, membros online e as últimas mensagens do canal. |

## Fluxo principal

1. O usuário acessa o frontend Angular.
2. O usuário informa o nome e entra no canal geral.
3. O frontend abre uma conexão WebSocket por meio do Kong.
4. A API registra a conexão e envia um evento `CONNECTED`.
5. A API envia o `BRIEFING` com as últimas mensagens do canal.
6. A API emite eventos de entrada, mensagens e saída para os membros conectados.

## Limites da Entrega 1

Nesta entrega, o sistema ainda não possui:

- autenticação JWT;
- roles de usuário;
- mensagens críticas com ACK;
- persistência em PostgreSQL;
- cache ou presença em Redis;
- eventos com Kafka;
- observabilidade com Prometheus, Grafana ou Loki.

Esses itens ficam planejados para entregas futuras.
