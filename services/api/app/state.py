from collections import deque

from fastapi import WebSocket


BUFFER_SIZE = 50


class ChannelState:
    def __init__(self):
        self.connections: dict[str, dict[str, WebSocket]] = {}
        self.message_buffer: dict[str, deque[dict]] = {}
        self.active_members: dict[str, dict[str, dict]] = {}

    def ensure_channel(self, channel_id: str):
        if channel_id not in self.connections:
            self.connections[channel_id] = {}

        if channel_id not in self.message_buffer:
            self.message_buffer[channel_id] = deque(maxlen=BUFFER_SIZE)

        if channel_id not in self.active_members:
            self.active_members[channel_id] = {}

    async def connect(self, channel_id: str, usuario: str, websocket: WebSocket):
        self.ensure_channel(channel_id)

        old_connection = self.connections[channel_id].get(usuario)

        if old_connection is not None:
            try:
                await old_connection.close()
            except Exception:
                pass

        await websocket.accept()

        self.connections[channel_id][usuario] = websocket
        self.active_members[channel_id][usuario] = {
            "usuario": usuario,
            "status": "online",
        }

    def disconnect(self, channel_id: str, usuario: str, websocket: WebSocket):
        if channel_id not in self.connections:
            return

        current_connection = self.connections[channel_id].get(usuario)

        if current_connection == websocket:
            self.connections[channel_id].pop(usuario, None)
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

        disconnected_users = []

        for usuario, connection in self.connections[channel_id].items():
            try:
                await connection.send_json(message)
            except Exception:
                disconnected_users.append(usuario)

        for usuario in disconnected_users:
            self.connections[channel_id].pop(usuario, None)
            self.active_members[channel_id].pop(usuario, None)


channel_state = ChannelState()