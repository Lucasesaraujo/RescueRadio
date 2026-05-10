import socket
import threading
from collections import deque
from typing import List, Optional
from datetime import datetime

from auth import AuthManager

MAX_AUTH_ATTEMPTS = 3  # tentativas antes de bloquear a conexão


class ChatServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 12345):
        """
        Inicializa o servidor de comunicação de emergência.

        Configura o socket TCP com SO_REUSEADDR para permitir reinicialização
        rápida após queda, e prepara estruturas de dados thread-safe para
        gerenciar clientes conectados e histórico de mensagens.

        Args:
            host: Endereço de escuta. Padrão "0.0.0.0" aceita todas as interfaces.
            port: Porta TCP. Padrão 12345.
        """
        self.host = host
        self.port = port

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Evita "Address already in use" em reinicializações rápidas
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.clients: List[socket.socket] = []
        self.names: dict[socket.socket, str] = {}

        # deque com maxlen garante O(1) no append e descarte automático do mais antigo
        self.history: deque[bytes] = deque(maxlen=20)

        self.lock = threading.Lock()

        # Carrega (ou cria) o arquivo de credenciais dos operadores
        self.auth = AuthManager()
        if self.auth.count() == 0:
            self.log("AVISO", "Nenhum operador cadastrado! Execute admin.py antes de conectar clientes.")

    # ─────────────────────────────────────────────
    # LOGS
    # ─────────────────────────────────────────────

    def log(self, level: str, message: str) -> None:
        """
        Registra uma entrada de log no stdout com timestamp e nível.

        Args:
            level: Rótulo do nível (INFO, MSG, ERRO, AVISO).
            message: Texto descritivo do evento.
        """
        now = datetime.now().strftime("%H:%M:%S")
        print(f"[{now}] [{level}] {message}")

    # ─────────────────────────────────────────────
    # START
    # ─────────────────────────────────────────────

    def start(self) -> None:
        """
        Inicia o loop principal de aceitação de conexões.

        Bloqueia indefinidamente, criando uma thread daemon para cada
        cliente aceito. Threads daemon encerram automaticamente quando o
        processo principal termina, evitando vazamento de threads.
        """
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen()
        self.log("INFO", f"Servidor rodando em {self.host}:{self.port}")

        while True:
            client_socket, addr = self.server_socket.accept()
            handler = ClientHandler(client_socket, addr, self)
            handler.daemon = True  # encerra junto com o processo principal
            handler.start()

    # ─────────────────────────────────────────────
    # BROADCAST
    # ─────────────────────────────────────────────

    def broadcast(self, message: bytes, origin: Optional[socket.socket] = None) -> None:
        """
        Retransmite uma mensagem para todos os clientes conectados, exceto o remetente.

        Coleta clientes com falha de envio e os remove *após* liberar o lock,
        evitando deadlock com remove_client (que também adquire o lock) e
        eliminando o bug de modificar a lista durante a iteração.

        Args:
            message: Payload já codificado a ser enviado.
            origin:  Socket do remetente; será excluído da retransmissão.
        """
        failed: List[socket.socket] = []

        with self.lock:
            for client in self.clients:
                if client != origin:
                    try:
                        client.send(message)
                    except OSError:
                        failed.append(client)

        # remove_client adquire o lock internamente — não deve ser chamado
        # enquanto o lock está sendo mantido (Lock não é reentrante)
        for client in failed:
            self.remove_client(client)

    def broadcast_system_message(self, text: str) -> None:
        """
        Formata e envia uma mensagem do sistema para todos os clientes.

        A mensagem também é registrada no log do servidor e adicionada ao
        histórico para que novos membros recebam contexto ao entrar.

        Args:
            text: Texto da mensagem de sistema (sem prefixo de timestamp).
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        msg = f"[{timestamp}] [SISTEMA] {text}\n".encode()

        self.log("INFO", text)
        self.broadcast(msg)
        self.add_to_history(msg)

    # ─────────────────────────────────────────────
    # CLIENT MANAGEMENT
    # ─────────────────────────────────────────────

    def add_client(self, client: socket.socket, name: str) -> None:
        """
        Registra um novo cliente na lista de conexões ativas.

        Deve ser chamado após validação do nome, antes de enviar o histórico
        e anunciar a entrada no canal.

        Args:
            client: Socket TCP do cliente.
            name:   Identificador/nome escolhido pelo socorrista.
        """
        with self.lock:
            self.clients.append(client)
            self.names[client] = name

    def remove_client(self, client: socket.socket) -> None:
        """
        Remove um cliente da lista de conexões e anuncia sua saída.

        Idempotente: pode ser chamado mesmo que o cliente já tenha sido
        removido (ex.: falha detectada em broadcast e em ClientHandler.run).

        Args:
            client: Socket TCP do cliente a ser removido.
        """
        with self.lock:
            name = self.names.pop(client, "Desconhecido")
            try:
                self.clients.remove(client)
            except ValueError:
                pass  # já foi removido por outra thread

        self.broadcast_system_message(f"{name} saiu do canal")

    def list_clients(self, requester: socket.socket) -> None:
        """
        Envia ao solicitante a lista de membros atualmente conectados.

        Args:
            requester: Socket do cliente que solicitou o comando /membros.
        """
        with self.lock:
            names = list(self.names.values())

        header = f"\n--- MEMBROS NO CANAL ({len(names)}) ---\n"
        body = "\n".join(f"  • {n}" for n in names) + "\n"
        footer = "──────────────────────────────\n\n"

        try:
            requester.send((header + body + footer).encode())
        except OSError:
            pass

    # ─────────────────────────────────────────────
    # HISTORY
    # ─────────────────────────────────────────────

    def add_to_history(self, message: bytes) -> None:
        """
        Adiciona uma mensagem ao buffer de histórico circular.

        O deque com maxlen descarta automaticamente a mensagem mais antiga
        quando o limite é atingido — sem necessidade de pop(0) explícito.

        Args:
            message: Mensagem já formatada e codificada.
        """
        with self.lock:
            self.history.append(message)

    def send_history(self, client: socket.socket) -> None:
        """
        Envia o buffer de histórico (briefing) para um cliente recém-conectado.

        Permite que o socorrista se contextualize rapidamente sobre as últimas
        comunicações do canal antes de começar a transmitir.

        Args:
            client: Socket do cliente que receberá o histórico.
        """
        try:
            client.send(b"\n\033[1;33m========= BRIEFING =========\033[0m\n")
            with self.lock:
                snapshot = list(self.history)

            if snapshot:
                for msg in snapshot:
                    client.send(msg)
            else:
                client.send(b"  (canal sem mensagens anteriores)\n")

            client.send(b"\033[1;33m============================\033[0m\n\n")
        except OSError:
            pass


# ══════════════════════════════════════════════════════════════════
# CLIENT HANDLER
# ══════════════════════════════════════════════════════════════════

class ClientHandler(threading.Thread):
    def __init__(self, client_socket: socket.socket, addr, server: ChatServer):
        """
        Thread responsável pelo ciclo de vida de um cliente conectado.

        Gerencia handshake de nome, envio de histórico, recebimento de
        mensagens e tratamento de comandos especiais.

        Args:
            client_socket: Socket TCP do cliente.
            addr:          Tupla (ip, porta) do cliente.
            server:        Referência ao ChatServer para operações compartilhadas.
        """
        super().__init__()
        self.client_socket = client_socket
        self.addr = addr
        self.server = server
        self.name = "Desconhecido"

    def _handle_command(self, text: str) -> bool:
        """
        Processa comandos especiais prefixados com '/'.

        Args:
            text: Texto recebido do cliente (já decodificado e sem espaços extras).

        Returns:
            True se o texto era um comando (e foi processado), False caso contrário.
        """
        cmd = text.lower()

        if cmd == "/sair":
            self.client_socket.send(b"Encerrando conexao. Ate logo!\n")
            return True  # sinaliza para encerrar o loop

        if cmd == "/membros":
            self.server.list_clients(self.client_socket)
            return True

        if cmd == "/ajuda":
            help_text = (
                "\n--- COMANDOS DISPONÍVEIS ---\n"
                "  /membros  Lista membros no canal\n"
                "  /ajuda    Exibe esta mensagem\n"
                "  /sair     Encerra a conexão\n"
                "----------------------------\n\n"
            )
            try:
                self.client_socket.send(help_text.encode())
            except OSError:
                pass
            return True

        return False  # não era um comando

    def _authenticate(self) -> tuple[bool, str]:
        """
        Conduz o protocolo de autenticação com o cliente via troca de linhas TCP.

        Protocolo (linha a linha, terminadas em \\n):
          S→C  Banner + "USUARIO:\\n"
          C→S  username\\n
          S→C  "SENHA:\\n"              (repetido até MAX_AUTH_ATTEMPTS)
          C→S  password\\n
          S→C  "AUTH_OK\\n"            → acesso concedido
               "AUTH_ERR:X/Y\\n"       → falha, tente novamente
               "AUTH_BAN\\n"           → bloqueado, conexão encerrada

        Mensagens de erro são genéricas (não revelam se o usuário existe)
        para evitar enumeração de usernames.

        Returns:
            Tupla (success, username). username é a string de identificação
            que será usada no canal — vazia em caso de falha.
        """
        try:
            # Banner + prompt de usuário (enviados juntos num único send)
            self.client_socket.send(
                b"\033[1;36m=== CENTRAL DE COMUNICACAO DE RESGATE ===\033[0m\n"
                b"\033[1;31m[CANAL RESTRITO - Autenticacao obrigatoria]\033[0m\n"
                b"\n"
                b"USUARIO:\n"
            )

            raw = self.client_socket.recv(1024)
            if not raw:
                return False, ""
            username = raw.decode(errors="replace").strip()

            if not username:
                self.client_socket.send(b"AUTH_BAN\n")
                return False, ""

            # Loop de senha com limite de tentativas
            for attempt in range(1, MAX_AUTH_ATTEMPTS + 1):
                self.client_socket.send(b"SENHA:\n")

                raw = self.client_socket.recv(1024)
                if not raw:
                    return False, ""
                password = raw.decode(errors="replace").strip()

                if self.server.auth.verify(username, password):
                    self.server.log("INFO", f"Auth OK: '{username}' de {self.addr}")
                    self.client_socket.send(b"AUTH_OK\n")
                    return True, username

                # Falha — mesma mensagem independente de usuário existir ou não
                self.server.log(
                    "AVISO",
                    f"Auth FAIL: '{username}' tentativa {attempt}/{MAX_AUTH_ATTEMPTS} de {self.addr}",
                )
                if attempt < MAX_AUTH_ATTEMPTS:
                    self.client_socket.send(
                        f"AUTH_ERR:{attempt}/{MAX_AUTH_ATTEMPTS}\n".encode()
                    )
                else:
                    self.client_socket.send(b"AUTH_BAN\n")
                    self.server.log(
                        "AVISO",
                        f"Bloqueado: '{username}' de {self.addr} apos {MAX_AUTH_ATTEMPTS} tentativas",
                    )

            return False, ""

        except OSError as e:
            self.server.log("ERRO", f"Erro de auth em {self.addr}: {e}")
            return False, ""

    def run(self) -> None:
        """
        Loop principal da thread do cliente.

        Fluxo:
          1. Autentica o operador via _authenticate().
          2. Registra o cliente no servidor.
          3. Envia o briefing (histórico recente).
          4. Anuncia entrada no canal.
          5. Recebe mensagens em loop, processando comandos ou retransmitindo.
          6. Em qualquer exceção ou desconexão, remove o cliente e fecha o socket.
        """
        try:
            # ── Fase 1: autenticação ──────────────────────────────────────
            success, username = self._authenticate()
            if not success:
                self.client_socket.close()
                return

            self.name = username

            # ── Fase 2: entrada no canal ──────────────────────────────────
            self.server.add_client(self.client_socket, self.name)
            self.server.log("INFO", f"{self.name} autenticado e conectado de {self.addr}")

            self.server.send_history(self.client_socket)
            self.server.broadcast_system_message(f"{self.name} entrou no canal")

            # ── Fase 3: loop de mensagens ─────────────────────────────────
            while True:
                message = self.client_socket.recv(1024)

                if not message:
                    break  # cliente fechou a conexão

                text = message.decode(errors="replace").strip()
                if not text:
                    continue

                # comandos especiais
                if text.startswith("/"):
                    should_exit = self._handle_command(text)
                    if should_exit and text.lower() == "/sair":
                        break
                    continue

                timestamp = datetime.now().strftime("%H:%M:%S")
                formatted = f"[{timestamp}] {self.name}: {text}\n".encode()

                self.server.log("MSG", f"{self.name}: {text}")
                self.server.add_to_history(formatted)
                self.server.broadcast(formatted, origin=self.client_socket)

        except ConnectionResetError:
            self.server.log("AVISO", f"Conexão resetada por {self.addr}")
        except Exception as e:
            self.server.log("ERRO", f"{self.addr}: {e}")
        finally:
            self.server.log("INFO", f"{self.name} desconectado")
            self.server.remove_client(self.client_socket)
            self.client_socket.close()


# ══════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    server = ChatServer()
    server.start()