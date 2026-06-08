# Cenários de Teste Manual

Este roteiro valida a Entrega 1 do RescueRadio usando Docker Compose.

## Pré-requisitos

- Docker instalado;
- Docker Compose instalado;
- portas `4200`, `8000`, `8001` e `8002` disponíveis.

## Subir o projeto

Na raiz do repositório:

```powershell
docker compose up --build
```

Validar URLs:

| Serviço | URL esperada |
| --- | --- |
| Frontend Angular | <http://localhost:4200> |
| API direta | <http://localhost:8000/health> |
| API via Kong | <http://localhost:8001/health> |

Resposta esperada do health check:

```json
{
  "status": "ok",
  "service": "rescueradio-api"
}
```

## Teste 1: entrada no canal

1. Abrir <http://localhost:4200>.
2. Informar o nome `Lucas`.
3. Clicar em `Entrar`.

Resultado esperado:

- status muda para conectado;
- canal exibido como `canal-geral`;
- evento de conexão aparece na interface;
- `Lucas` aparece como membro ativo.

## Teste 2: broadcast entre dois usuários

1. Manter a aba de `Lucas` aberta.
2. Abrir uma segunda aba em <http://localhost:4200>.
3. Entrar como `Marcelo`.
4. Na aba de `Lucas`, enviar: `Equipe Alfa chegou ao ponto de encontro.`

Resultado esperado:

- a mensagem aparece para `Lucas`;
- a mensagem aparece para `Marcelo`;
- a lista de membros mostra os usuários conectados.

## Teste 3: briefing para novo usuário

1. Depois do Teste 2, abrir uma terceira aba.
2. Entrar como `Júlia`.

Resultado esperado:

- `Júlia` recebe o briefing com as mensagens anteriores do canal;
- os demais usuários recebem evento de entrada de `Júlia`.

## Teste 4: saída de membro

1. Fechar a aba de `Marcelo` ou clicar em `Sair do canal`.

Resultado esperado:

- os usuários restantes recebem evento de saída;
- `Marcelo` é removido da lista de membros ativos.

## Teste 5: payload inválido

Este teste pode ser feito com uma ferramenta WebSocket externa, caso disponível.

Conectar em:

```text
ws://localhost:8001/ws/channel/canal-geral?usuario=Teste
```

Enviar payload inválido:

```json
{
  "type": "INVALID_MESSAGE",
  "usuario": "Teste",
  "timestamp_iso": "2026-06-04T21:30:00Z",
  "corpo_texto": "Mensagem inválida."
}
```

Resultado esperado:

- o servidor responde com evento `ERROR`;
- a mensagem inválida não é adicionada ao briefing;
- a mensagem inválida não é retransmitida aos demais usuários.

## Encerrar o projeto

Para parar os serviços:

```powershell
docker compose down
```
