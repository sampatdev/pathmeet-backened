from fastapi import WebSocket
import uuid

class ConnectionManager:
    def __init__(self):
        # {session_id: {user_id: WebSocket}}
        self.active_connections: dict[uuid.UUID, dict[uuid.UUID, WebSocket]] = {}

    async def connect(self, session_id: uuid.UUID, user_id: uuid.UUID, websocket: WebSocket):
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = {}
        self.active_connections[session_id][user_id] = websocket

    def disconnect(self, session_id: uuid.UUID, user_id: uuid.UUID):
        if session_id in self.active_connections:
            self.active_connections[session_id].pop(user_id, None)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]

    async def send_to_session(self, session_id: uuid.UUID, sender_id: uuid.UUID, message: dict):
        if session_id not in self.active_connections:
            return
        dead_users = []
        for user_id, websocket in self.active_connections[session_id].items():
            if user_id != sender_id:
                try:
                    await websocket.send_json(message)
                except Exception:
                    dead_users.append(user_id)
        for user_id in dead_users:
            self.disconnect(session_id, user_id)


                        

manager = ConnectionManager()