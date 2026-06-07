from collections import deque

from fastapi import WebSocket


BUFFER_SIZE = 50


class ChannelState:
    def __init__(self):
        self.connections: dict[str, list[WebSocket]] = {}
        self.message_buffer: dict[str, deque[dict]] = {}
        self.active_members: dict[str, dict[str, dict]] = {}

    def ensure_channel(self, channel_id: str):
        if channel_id not in self.connections:
            self.connections[channel_id] = []

        if channel_id not in self.message_buffer:
            self.message_buffer[channel_id] = deque(maxlen=BUFFER_SIZE)

        if channel_id not in self.active_members:
            self.active_members[channel_id] = {}

    async def connect(self, channel_id: str, usuario: str, websocket: WebSocket):
        self.ensure_channel(channel_id)

        await websocket.accept()

        self.connections[channel_id].append(websocket)
        self.active_members[channel_id][usuario] = {
            "usuario": usuario,
            "status": "online",
        }

    def disconnect(self, channel_id: str, usuario: str, websocket: WebSocket):
        if channel_id not in self.connections:
            return

        if websocket in self.connections[channel_id]:
            self.connections[channel_id].remove(websocket)

        if channel_id in self.active_members:
            self.active_members[channel_id].pop(usuario, None)

    def add_message_to_buffer(self, channel_id: str, message: dict):
        self.ensure_channel(channel_id)
        self.message_buffer[channel_id].append(message)

    def get_briefing(self, channel_id: str) -> list[dict]:
        self.ensure_channel(channel_id)
        return list(self.message_buffer[channel_id])

    def get_active_members(self, channel_id: str) -> list[dict]:
        self.ensure_channel(channel_id)
        return list(self.active_members[channel_id].values())

    async def broadcast(self, channel_id: str, message: dict):
        if channel_id not in self.connections:
            return

        disconnected_connections = []

        for connection in self.connections[channel_id]:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected_connections.append(connection)

        for connection in disconnected_connections:
            if connection in self.connections[channel_id]:
                self.connections[channel_id].remove(connection)


channel_state = ChannelState()