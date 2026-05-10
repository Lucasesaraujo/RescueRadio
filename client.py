import socket
import threading
import sys
import os
from datetime import datetime


# ──────────────────────────────────────────────────────────────────────────────
# Constantes de configuração
# ──────────────────────────────────────────────────────────────────────────────

SERVER_HOST: str = "127.0.0.1"
SERVER_PORT: int = 12345
BUFFER_SIZE: int = 4096
RECONNECT_DELAY: int = 5  # segundos entre tentativas de reconexão


# ──────────────────────────────────────────────────────────────────────────────
# Utilitários de terminal
# ──────────────────────────────────────────────────────────────────────────────

def clear_line() -> None:
    """Apaga a linha atual do terminal (onde o usuário está digitando)."""
    sys.stdout.write("\r\033[K")
    sys.stdout.flush()


def print_message(text: str) -> None:
    """
    Imprime uma mensagem recebida sem sobrescrever o prompt do usuário.

    Limpa a linha atual, imprime a mensagem e reescreve o prompt vazio,
    garantindo que a entrada do usuário fique sempre na última linha.

    Args:
        text: Mensagem já formatada a ser exibida.
    """
    clear_line()
    print(text, end="", flush=True)


def local_log(level: str, message: str) -> None:
    """
    Exibe um log local do cliente (não enviado ao servidor).

    Args:
        level:   Rótulo do nível (INFO, ERRO, AVISO).
        message: Descrição do evento.
    """
    now = datetime.now().strftime("%H:%M:%S")
    print_message(f"[{now}] [{level}] {message}\n")


# ──────────────────────────────────────────────────────────────────────────────
# Cliente de Chat
# ──────────────────────────────────────────────────────────────────────────────

class ChatClient:
    def __init__(self, host: str = SERVER_HOST, port: int = SERVER_PORT):
        """
        Inicializa o cliente de comunicação de emergência.

        Args:
            host: Endereço IP ou hostname do servidor.
            port: Porta TCP do servidor.
        """
        self.host = host
        self.port = port
        self.sock: socket.socket | None = None
        self.connected: bool = False

        # Evento usado para sinalizar encerramento entre threads
        self._stop_event = threading.Event()

    # ─────────────────────────────────────────────
    # CONEXÃO
    # ─────────────────────────────────────────────

    def connect(self) -> bool:
        """
        Tenta estabelecer conexão TCP com o servidor.

        Configura TCP keepalive para detectar quedas silenciosas de conexão
        (comum em redes de campo durante emergências).

        Returns:
            True se a conexão foi estabelecida com sucesso, False caso contrário.
        """
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            # Keepalive: detecta links mortos sem mensagens explícitas
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

            # Plataformas Linux: ajusta parâmetros de keepalive
            if hasattr(socket, "TCP_KEEPIDLE"):
                self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 10)
                self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 5)
                self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3)

            self.sock.connect((self.host, self.port))
            self.connected = True
            return True

        except ConnectionRefusedError:
            local_log("ERRO", f"Servidor {self.host}:{self.port} recusou a conexão.")
        except OSError as e:
            local_log("ERRO", f"Falha ao conectar: {e}")

        return False

    def disconnect(self) -> None:
        """
        Encerra a conexão de forma limpa, sinalizando todas as threads.
        """
        self._stop_event.set()
        self.connected = False
        if self.sock:
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
                self.sock.close()
            except OSError:
                pass
            self.sock = None

    # ─────────────────────────────────────────────
    # THREAD DE RECEBIMENTO
    # ─────────────────────────────────────────────

    def _receive_loop(self) -> None:
        """
        Loop de recebimento executado em thread separada.

        Recebe dados do servidor continuamente e os exibe no terminal.
        Ao detectar desconexão (recv retorna b""), sinaliza encerramento.
        Tolera fragmentação TCP acumulando dados no buffer até encontrar
        newline completa.
        """
        buffer = b""

        while not self._stop_event.is_set():
            try:
                chunk = self.sock.recv(BUFFER_SIZE)

                if not chunk:
                    # Servidor encerrou a conexão
                    local_log("AVISO", "Servidor encerrou a conexão.")
                    self._stop_event.set()
                    break

                buffer += chunk

                # Processa mensagens completas (delimitadas por \n)
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    text = line.decode(errors="replace")
                    if text:
                        print_message(text + "\n")

            except OSError:
                if not self._stop_event.is_set():
                    local_log("ERRO", "Conexão perdida com o servidor.")
                    self._stop_event.set()
                break

    # ─────────────────────────────────────────────
    # ENVIO
    # ─────────────────────────────────────────────

    def send(self, text: str) -> bool:
        """
        Envia uma mensagem ao servidor.

        Args:
            text: Mensagem a ser enviada (sem encoding).

        Returns:
            True se enviado com sucesso, False em caso de falha.
        """
        if not self.connected or not self.sock:
            return False
        try:
            self.sock.send((text + "\n").encode())
            return True
        except OSError as e:
            local_log("ERRO", f"Falha ao enviar: {e}")
            self._stop_event.set()
            return False

    def _recv_line(self) -> str:
        """
        Lê exatamente uma linha do servidor (bloqueante, byte a byte).

        Usado exclusivamente durante o handshake, onde o protocolo é
        estritamente sequencial e o volume de dados é mínimo — o custo
        de recv(1) em loop é irrelevante nesse contexto.

        Returns:
            Linha recebida, decodificada e sem '\\n' ou espaços extras.

        Raises:
            ConnectionError: Se o servidor fechar a conexão antes do '\\n'.
        """
        buf = b""
        while True:
            byte = self.sock.recv(1)
            if not byte:
                raise ConnectionError("Servidor encerrou a conexão durante o handshake.")
            if byte == b"\n":
                return buf.decode(errors="replace").strip()
            buf += byte

    # ─────────────────────────────────────────────
    # HANDSHAKE (síncrono — antes de qualquer thread)
    # ─────────────────────────────────────────────

    def _handshake(self) -> bool:
        """
        Conduz o protocolo de autenticação de forma totalmente síncrona.

        Lê linha a linha do servidor usando _recv_line(), garantindo que
        banner, prompts e status codes sejam processados na ordem exata
        do protocolo — sem nenhuma thread de recebimento concorrente ativa.

        Protocolo esperado do servidor:
          S→C  banner (múltiplas linhas) + "USUARIO:\\n"
          C→S  username\\n
          S→C  "SENHA:\\n"
          C→S  password\\n  (ocultado via getpass)
          S→C  "AUTH_OK\\n"  →  sucesso
               "AUTH_ERR:X/Y\\n" + "SENHA:\\n"  →  tenta novamente
               "AUTH_BAN\\n"  →  bloqueado, retorna False

        Returns:
            True se autenticado com sucesso, False caso contrário.
        """
        import getpass

        try:
            # ── Banner ────────────────────────────────────────────────────
            # O servidor envia banner + "USUARIO:\n" num único send().
            # Lemos linha a linha até encontrar o sentinel "USUARIO:".
            banner_lines = []
            while True:
                line = self._recv_line()
                if line == "USUARIO:":
                    break
                banner_lines.append(line)

            # Exibe o banner recebido
            for bl in banner_lines:
                print(bl)

            # ── Username ──────────────────────────────────────────────────
            try:
                username = input("  Usuário: ").strip()
            except (EOFError, KeyboardInterrupt):
                return False

            if not username:
                local_log("ERRO", "Nome de usuário não pode ser vazio.")
                return False

            self.sock.send((username + "\n").encode())

            # ── Loop de senha ─────────────────────────────────────────────
            while True:
                status = self._recv_line()

                if status == "SENHA:":
                    try:
                        password = getpass.getpass("  Senha: ")
                    except (EOFError, KeyboardInterrupt):
                        return False
                    self.sock.send((password + "\n").encode())

                elif status == "AUTH_OK":
                    print("\n\033[1;32m  [ACESSO AUTORIZADO]\033[0m\n")
                    return True

                elif status.startswith("AUTH_ERR:"):
                    attempt_info = status.split(":", 1)[1]  # ex.: "1/3"
                    print(f"\033[1;31m  Credenciais inválidas — tentativa {attempt_info}.\033[0m")
                    # Servidor enviará "SENHA:\n" novamente; loop continua

                elif status == "AUTH_BAN":
                    print(
                        "\n\033[1;31m  ACESSO BLOQUEADO.\033[0m\n"
                        "  Número máximo de tentativas excedido.\n"
                    )
                    return False

                # Linhas vazias ou desconhecidas são ignoradas silenciosamente

        except (OSError, ConnectionError) as e:
            local_log("ERRO", f"Falha no handshake: {e}")
            return False

    # ─────────────────────────────────────────────
    # INTERFACE DE USUÁRIO
    # ─────────────────────────────────────────────

    def _print_help(self) -> None:
        """Exibe os comandos disponíveis localmente (sem acionar o servidor)."""
        help_lines = [
            "",
            "┌─ COMANDOS ─────────────────────────────┐",
            "│  /membros   Lista membros no canal      │",
            "│  /ajuda     Exibe comandos no servidor  │",
            "│  /sair      Encerra a conexão           │",
            "│  /help      Exibe esta ajuda local      │",
            "└─────────────────────────────────────────┘",
            "",
        ]
        for line in help_lines:
            print(line)

    def _input_loop(self) -> None:
        """
        Loop de entrada do usuário (thread principal).

        Lê linhas do stdin e as encaminha ao servidor. Trata interrupções
        de teclado (Ctrl+C) e comandos locais (/help) sem enviar ao servidor.
        """
        try:
            while not self._stop_event.is_set():
                try:
                    text = input()
                except EOFError:
                    # Pipe fechado ou stdin encerrado
                    break

                text = text.strip()
                if not text:
                    continue

                # Comando local — não enviado ao servidor
                if text.lower() == "/help":
                    self._print_help()
                    continue

                # Envia ao servidor (incluindo /sair, /membros etc.)
                sent = self.send(text)

                # Se o usuário pediu pra sair e o envio funcionou, encerra
                if sent and text.lower() == "/sair":
                    self._stop_event.set()
                    break

        except KeyboardInterrupt:
            print("\n")
            local_log("INFO", "Encerrando por Ctrl+C...")
            self.send("/sair")
            self._stop_event.set()

    # ─────────────────────────────────────────────
    # PONTO DE ENTRADA PRINCIPAL
    # ─────────────────────────────────────────────

    def run(self) -> None:
        """
        Orquestra o ciclo completo de conexão e comunicação.

        1. Conecta ao servidor.
        2. Inicia thread de recebimento (daemon).
        3. Roda o loop de entrada na thread principal.
        4. Aguarda encerramento e fecha recursos.
        """
        print("\033[1;36m")
        print("╔═══════════════════════════════════════════╗")
        print("║   CENTRAL DE COMUNICAÇÃO DE RESGATE       ║")
        print("║   Canal de Rádio Digital — TCP Seguro     ║")
        print("╚═══════════════════════════════════════════╝")
        print(f"\033[0mConectando em {self.host}:{self.port}...")

        if not self.connect():
            sys.exit(1)

        # Fase 1: autenticacao sincrona (sem threads concorrentes)
        # So apos auth bem-sucedida o canal de mensagens e liberado.
        if not self._handshake():
            self.disconnect()
            sys.exit(1)

        # Fase 2: comunicacao concorrente
        local_log("INFO", "Canal aberto. Use /help para ver os comandos disponiveis.")

        # Thread de recebimento roda em paralelo com a entrada do usuario
        recv_thread = threading.Thread(target=self._receive_loop, daemon=True)
        recv_thread.start()

        # Loop de entrada ocupa a thread principal
        self._input_loop()

        # Aguarda a thread de recebimento encerrar (timeout de segurança)
        recv_thread.join(timeout=2)
        self.disconnect()

        print("\n\033[1;33mConexão encerrada. Fique seguro.\033[0m\n")


# ──────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ──────────────────────────────────────────────────────────────────────────────

def parse_args() -> tuple[str, int]:
    """
    Lê host e porta a partir dos argumentos de linha de comando.

    Uso: python client.py [host] [porta]

    Returns:
        Tupla (host, porta) com os valores fornecidos ou os padrões.
    """
    host = sys.argv[1] if len(sys.argv) > 1 else SERVER_HOST
    try:
        port = int(sys.argv[2]) if len(sys.argv) > 2 else SERVER_PORT
    except ValueError:
        print(f"Porta inválida '{sys.argv[2]}'. Usando padrão {SERVER_PORT}.")
        port = SERVER_PORT
    return host, port


if __name__ == "__main__":
    host, port = parse_args()
    client = ChatClient(host=host, port=port)
    client.run()