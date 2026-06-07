from datetime import datetime, timezone

from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect

from app.state import channel_state
from app.validators import validate_incoming_message

app = FastAPI(title="RescueRadio API")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "rescueradio-api"
    }


@app.websocket("/ws/channel/{channel_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    channel_id: str,
    usuario: str = Query(...)
):
    await channel_state.connect(channel_id, usuario, websocket)

    await websocket.send_json({
        "type": "CONNECTED",
        "channel_id": channel_id,
        "usuario": usuario,
        "message": "Conectado ao canal com sucesso."
    })

    await websocket.send_json({
        "type": "BRIEFING",
        "channel_id": channel_id,
        "messages": channel_state.get_briefing(channel_id)
    })

    await channel_state.broadcast(channel_id, {
        "type": "MEMBER_JOINED",
        "channel_id": channel_id,
        "usuario": usuario,
        "timestamp_iso": datetime.now(timezone.utc).isoformat(),
        "members": channel_state.get_active_members(channel_id),
        "message": f"{usuario} entrou no canal."
    })

    try:
        while True:
            data = await websocket.receive_json()

            is_valid, result = validate_incoming_message(data)

            if not is_valid:
                await websocket.send_json({
                    "type": "ERROR",
                    "channel_id": channel_id,
                    "message": result
                })
                continue

            message = result

            channel_state.add_message_to_buffer(channel_id, message)

            await channel_state.broadcast(channel_id, {
                "type": "MESSAGE_RECEIVED",
                "channel_id": channel_id,
                "payload": message
            })

    except WebSocketDisconnect:
        channel_state.disconnect(channel_id, usuario, websocket)

        await channel_state.broadcast(channel_id, {
            "type": "MEMBER_LEFT",
            "channel_id": channel_id,
            "usuario": usuario,
            "timestamp_iso": datetime.now(timezone.utc).isoformat(),
            "members": channel_state.get_active_members(channel_id),
            "message": f"{usuario} saiu do canal."
        })

        print(f"{usuario} desconectado do canal {channel_id}")