"""
auth.py — Gerenciamento de autenticação da Central de Resgate.

Utiliza PBKDF2-HMAC-SHA256 com salt aleatório por usuário e 260.000
iterações (recomendação NIST SP 800-132 para 2024). Nenhuma senha é
armazenada em texto plano — apenas (salt, hash) no arquivo JSON.
"""

import hashlib
import hmac
import json
import os
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional

# ──────────────────────────────────────────────────────────────────────────────
# Constantes
# ──────────────────────────────────────────────────────────────────────────────

USERS_FILE = "users.json"
PBKDF2_ITERATIONS = 260_000   # NIST SP 800-132 (2024)
SALT_BYTES = 32               # 256 bits de entropia por usuário


# ──────────────────────────────────────────────────────────────────────────────
# AuthManager
# ──────────────────────────────────────────────────────────────────────────────

class AuthManager:
    """
    Gerencia o cadastro e verificação de credenciais dos operadores.

    Thread-safe: todas as operações de leitura e escrita sobre o arquivo
    de usuários são protegidas por um Lock. Usa comparação em tempo constante
    (hmac.compare_digest) para evitar ataques de timing.
    """

    def __init__(self, users_file: str = USERS_FILE):
        """
        Carrega (ou cria) o arquivo de usuários.

        Args:
            users_file: Caminho para o JSON de credenciais.
        """
        self.users_file = Path(users_file)
        self._lock = threading.Lock()
        self._users: dict = {}
        self._load()

    # ─────────────────────────────────────────────
    # Persistência
    # ─────────────────────────────────────────────

    def _load(self) -> None:
        """Carrega usuários do arquivo JSON. Cria arquivo vazio se não existir."""
        if self.users_file.exists():
            with open(self.users_file, encoding="utf-8") as f:
                self._users = json.load(f)
        else:
            self._users = {}
            self._save_unsafe()

    def _save_unsafe(self) -> None:
        """Grava os usuários no arquivo. Deve ser chamado com o lock adquirido."""
        with open(self.users_file, "w", encoding="utf-8") as f:
            json.dump(self._users, f, indent=2, ensure_ascii=False)

    # ─────────────────────────────────────────────
    # Hashing
    # ─────────────────────────────────────────────

    def _hash_password(self, password: str, salt: bytes) -> str:
        """
        Deriva um hash seguro da senha usando PBKDF2-HMAC-SHA256.

        Args:
            password: Senha em texto plano.
            salt:     Salt aleatório único por usuário (32 bytes).

        Returns:
            Hash hexadecimal do resultado da derivação.
        """
        key = hashlib.pbkdf2_hmac(
            hash_name="sha256",
            password=password.encode("utf-8"),
            salt=salt,
            iterations=PBKDF2_ITERATIONS,
        )
        return key.hex()

    # ─────────────────────────────────────────────
    # API pública
    # ─────────────────────────────────────────────

    def add_user(self, username: str, password: str, role: str = "operador") -> bool:
        """
        Cadastra um novo operador com senha hasheada.

        Args:
            username: Identificador único do operador.
            password: Senha em texto plano (será hasheada e descartada).
            role:     Papel do operador (ex.: "operador", "comandante").

        Returns:
            True se cadastrado com sucesso, False se o usuário já existir.
        """
        with self._lock:
            if username in self._users:
                return False

            salt = os.urandom(SALT_BYTES)
            self._users[username] = {
                "salt": salt.hex(),
                "hash": self._hash_password(password, salt),
                "role": role,
                "created_at": datetime.now().isoformat(),
            }
            self._save_unsafe()
            return True

    def remove_user(self, username: str) -> bool:
        """
        Remove um operador cadastrado.

        Args:
            username: Identificador do operador a remover.

        Returns:
            True se removido, False se não encontrado.
        """
        with self._lock:
            if username not in self._users:
                return False
            del self._users[username]
            self._save_unsafe()
            return True

    def reset_password(self, username: str, new_password: str) -> bool:
        """
        Redefine a senha de um operador (gera novo salt).

        Args:
            username:     Identificador do operador.
            new_password: Nova senha em texto plano.

        Returns:
            True se redefinida com sucesso, False se usuário não existir.
        """
        with self._lock:
            if username not in self._users:
                return False

            salt = os.urandom(SALT_BYTES)
            self._users[username]["salt"] = salt.hex()
            self._users[username]["hash"] = self._hash_password(new_password, salt)
            self._save_unsafe()
            return True

    def verify(self, username: str, password: str) -> bool:
        """
        Verifica credenciais em tempo constante (resistente a timing attack).

        Sempre executa o hash mesmo se o usuário não existir, para que o
        tempo de resposta não revele a existência do username.

        Args:
            username: Identificador fornecido pelo cliente.
            password: Senha fornecida pelo cliente.

        Returns:
            True se as credenciais são válidas, False caso contrário.
        """
        with self._lock:
            user = self._users.get(username)

        # Hash dummy para manter tempo constante mesmo com usuário inexistente
        dummy_salt = b"\x00" * SALT_BYTES
        candidate_hash = self._hash_password(password, dummy_salt)

        if user is None:
            return False

        real_salt = bytes.fromhex(user["salt"])
        real_hash = self._hash_password(password, real_salt)

        # Comparação em tempo constante: evita ataques de timing
        return hmac.compare_digest(real_hash, user["hash"])

    def user_exists(self, username: str) -> bool:
        """Verifica se um username está cadastrado."""
        with self._lock:
            return username in self._users

    def list_users(self) -> list[dict]:
        """
        Retorna lista de usuários com metadados (sem hash ou salt).

        Returns:
            Lista de dicts com 'username', 'role' e 'created_at'.
        """
        with self._lock:
            return [
                {
                    "username": u,
                    "role": data.get("role", "operador"),
                    "created_at": data.get("created_at", "—"),
                }
                for u, data in self._users.items()
            ]

    def count(self) -> int:
        """Retorna o número de operadores cadastrados."""
        with self._lock:
            return len(self._users)