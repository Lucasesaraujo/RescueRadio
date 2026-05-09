import socket
import threading
from typing import List, Optional
from datetime import datetime

class ChatServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 12345):
        '''
        
        '''
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.clients: List[socket.socket] = []
        self.names: dict[socket.socket, str] = {}
        self.history: List[bytes] = []
        self.max_history: int = 20

        self.lock = threading.Lock()
    
    #########################################
    # LOGS -----------------------------
    #########################################
    def log(self, level: str, message: str) -> None:
        '''
        
        '''
        now = datetime.now().strftime("%H:%M:%S")
        print(f"[{now}] [{level}] {message}")

    #########################################
    # START -----------------------------
    #########################################
    def start(self) -> None:
        '''
        
        '''
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen()

        self.log("INFO", f"Servidor rodando em {self.host}:{self.port}")

        while True:
            client_socket, addr = self.server_socket.accept()
            handler = ClientHandler(client_socket, addr, self)
            handler.start()

    #########################################
    # BROADCAST -----------------------------
    #########################################
    def broadcast(self, message: bytes, origin: Optional[socket.socket] = None) -> None:
        '''
        
        '''
        with self.lock:
            for client in self.clients:
                if client != origin:
                    try:
                        client.send(message)
                    except:
                        self.clients.remove(client)
    
    def broadcast_system_message(self, text: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        msg = f"[{timestamp}] [INFO] {text}\n".encode()

        self.log("INFO", text)
        self.broadcast(msg)
        self.add_to_history(msg)

    #########################################
    # CLIENT MGMT ---------------------------
    #########################################
    def add_client(self, client: socket.socket, name: str) -> None:
        '''
        
        '''
        with self.lock:
            self.clients.append(client)
            self.names[client] = name
            
    def remove_client(self, client: socket.socket) -> None:
        '''
        
        '''
        with self.lock:
            name = self.names.get(client, "Desconhecido")
            if client in self.clients:
                self.clients.remove(client)
            if client in self.names:
                del self.names[client]
            
        self.broadcast_system_message(f"{name} saiu do canal")

    #########################################
    # HISTORY -------------------------------
    #########################################
    def add_to_history(self, message: bytes) -> None:
        '''
        
        '''
        with self.lock:
            self.history.append(message)

            if len(self.history) > self.max_history:
                self.history.pop(0)
    
    def send_history(self, client: socket.socket) -> None:
        '''
        
        '''
        try:
            client.send(b"\n--- BRIEFING ---\n")
            with self.lock:
                for msg in self.history:
                    client.send(msg)
            
            client.send(b"----------------\n\n")
        
        except:
            pass

class ClientHandler(threading.Thread):
    def __init__(self, client_socket: socket.socket, addr, server: ChatServer):
        super().__init__()
        self.client_socket = client_socket
        self.addr = addr
        self.server = server
        self.name = "Desconhecido"

    def run(self) -> None:
        try:
            self.client_socket.send(b"Digite seu nome:")
            self.name = self.client_socket.recv(1024).decode().strip()

            self.server.add_client(self.client_socket, self.name)
            self.server.log("INFO", f"{self.name} conectado de {self.addr}")

            self.server.send_history(self.client_socket)

            self.server.broadcast_system_message(f"{self.name} entrou no canal")

            while True:
                message = self.client_socket.recv(1024)

                if not message:
                    break

                text = message.decode().strip()
                timestamp = datetime.now().strftime("%H:%M:%S")

                formatted = f"[{timestamp}] {self.name}: {text}\n".encode()
                self.server.log("MSG", f"{self.name}: {text}")

                self.server.add_to_history(formatted)
                self.server.broadcast(formatted, self.client_socket)

        except Exception as e:
            self.server.log("ERRO", f"{self.addr}: {e}")

        finally:
            self.server.log("INFO", f"{self.name} desconectado")
            self.server.remove_client(self.client_socket)
            self.client_socket.close()

if __name__ == "__main__":
    server = ChatServer()
    server.start()
