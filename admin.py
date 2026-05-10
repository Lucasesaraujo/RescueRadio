"""
admin.py — Painel administrativo da Central de Resgate.

Gerencia o cadastro de operadores autorizados a acessar o canal de rádio.
O acesso ao painel é protegido por credenciais definidas no arquivo .env —
separadas das credenciais dos operadores para isolamento de responsabilidades.

Pré-requisitos:
    pip install python-dotenv
    Copiar .env.example → .env e preencher ADMIN_USER e ADMIN_PASSWORD

Uso:
    py admin.py              → menu interativo (solicita login)
    py admin.py add          → cadastra operador
    py admin.py list         → lista operadores
    py admin.py remove       → remove operador
    py admin.py reset        → redefine senha de operador
"""

import sys
import hmac
import getpass
import os
from pathlib import Path

from dotenv import load_dotenv
from auth import AuthManager

# ──────────────────────────────────────────────────────────────────────────────
# Carregamento do .env
# ──────────────────────────────────────────────────────────────────────────────

ENV_FILE = Path(".env")


def _load_env() -> None:
    """
    Carrega variáveis do arquivo .env.

    Encerra com mensagem clara se o arquivo não existir, evitando
    que o painel rode sem credenciais configuradas.
    """
    if not ENV_FILE.exists():
        _err(
            "Arquivo .env não encontrado.\n"
            "  Copie .env.example → .env e defina ADMIN_USER e ADMIN_PASSWORD."
        )
        sys.exit(1)

    load_dotenv(ENV_FILE)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers de terminal
# ──────────────────────────────────────────────────────────────────────────────

def _header() -> None:
    print("\033[1;36m")
    print("╔══════════════════════════════════════════╗")
    print("║   PAINEL ADMINISTRATIVO — RESGATE        ║")
    print("╚══════════════════════════════════════════╝")
    print("\033[0m")


def _ok(msg: str) -> None:
    print(f"\033[1;32m  ✔ {msg}\033[0m")


def _err(msg: str) -> None:
    print(f"\033[1;31m  ✖ {msg}\033[0m")


def _ask(prompt: str) -> str:
    return input(f"  {prompt}: ").strip()


def _ask_password(prompt: str = "Senha") -> str:
    """Coleta senha sem exibir no terminal, com confirmação obrigatória."""
    while True:
        pwd = getpass.getpass(f"  {prompt}: ")
        if len(pwd) < 6:
            _err("Senha muito curta (mínimo 6 caracteres).")
            continue
        if getpass.getpass("  Confirme a senha: ") != pwd:
            _err("Senhas não conferem.")
            continue
        return pwd


# ──────────────────────────────────────────────────────────────────────────────
# Autenticação do administrador
# ──────────────────────────────────────────────────────────────────────────────

_MAX_ADMIN_ATTEMPTS = 3


def _authenticate_admin() -> bool:
    """
    Solicita e valida as credenciais do administrador contra o .env.

    Usa hmac.compare_digest para comparação em tempo constante,
    resistente a timing attacks mesmo para segredos curtos.
    Bloqueia após MAX_ADMIN_ATTEMPTS tentativas sem sucesso.

    Returns:
        True se as credenciais conferem, False caso contrário.
    """
    expected_user = os.getenv("ADMIN_USER", "").strip()
    expected_pass = os.getenv("ADMIN_PASSWORD", "").strip()

    if not expected_user or not expected_pass:
        _err(
            "ADMIN_USER ou ADMIN_PASSWORD não definidos no .env.\n"
            "  Edite o arquivo .env antes de continuar."
        )
        return False

    # Valores default sinalizando que o .env não foi configurado
    if expected_pass == "troque_por_senha_forte":
        _err(
            "Senha padrão detectada no .env.\n"
            "  Altere ADMIN_PASSWORD antes de usar o painel."
        )
        return False

    print("\n\033[1;33m  [ACESSO RESTRITO — Credenciais de administrador]\033[0m\n")

    for attempt in range(1, _MAX_ADMIN_ATTEMPTS + 1):
        try:
            user = _ask("Usuário admin")
            pwd  = getpass.getpass("  Senha admin: ")
        except (EOFError, KeyboardInterrupt):
            print()
            return False

        # Comparação em tempo constante para ambos os campos
        user_ok = hmac.compare_digest(user.encode(), expected_user.encode())
        pass_ok = hmac.compare_digest(pwd.encode(),  expected_pass.encode())

        if user_ok and pass_ok:
            print(f"\n\033[1;32m  Acesso autorizado.\033[0m\n")
            return True

        remaining = _MAX_ADMIN_ATTEMPTS - attempt
        if remaining > 0:
            _err(f"Credenciais inválidas. {remaining} tentativa(s) restante(s).")
        else:
            _err("Acesso bloqueado após múltiplas tentativas.")

    return False


# ──────────────────────────────────────────────────────────────────────────────
# Ações do painel
# ──────────────────────────────────────────────────────────────────────────────

def cmd_add(auth: AuthManager) -> None:
    """Cadastra um novo operador."""
    print("\n  — CADASTRAR OPERADOR —")
    username = _ask("Nome de usuário")
    if not username:
        _err("Nome não pode ser vazio.")
        return

    if auth.user_exists(username):
        _err(f"Usuário '{username}' já está cadastrado.")
        return

    role = _ask("Cargo (operador/comandante) [operador]") or "operador"
    password = _ask_password()

    if auth.add_user(username, password, role):
        _ok(f"Operador '{username}' ({role}) cadastrado.")
    else:
        _err("Falha ao cadastrar. Tente novamente.")


def cmd_list(auth: AuthManager) -> None:
    """Lista todos os operadores cadastrados."""
    users = auth.list_users()
    print(f"\n  — OPERADORES CADASTRADOS ({len(users)}) —\n")

    if not users:
        print("  (nenhum operador cadastrado)")
        return

    col = "{:<20} {:<14} {}"
    print("  " + col.format("USUÁRIO", "CARGO", "CADASTRADO EM"))
    print("  " + "─" * 56)
    for u in users:
        print("  " + col.format(u["username"], u["role"], u["created_at"][:19]))
    print()


def cmd_remove(auth: AuthManager) -> None:
    """Remove um operador cadastrado."""
    print("\n  — REMOVER OPERADOR —")
    cmd_list(auth)
    username = _ask("Nome do usuário a remover")
    if not username:
        return

    if _ask(f"Confirma remoção de '{username}'? (s/N)").lower() != "s":
        print("  Cancelado.")
        return

    if auth.remove_user(username):
        _ok(f"Operador '{username}' removido.")
    else:
        _err(f"Usuário '{username}' não encontrado.")


def cmd_reset(auth: AuthManager) -> None:
    """Redefine a senha de um operador."""
    print("\n  — REDEFINIR SENHA —")
    cmd_list(auth)
    username = _ask("Nome do usuário")
    if not username:
        return

    if not auth.user_exists(username):
        _err(f"Usuário '{username}' não encontrado.")
        return

    if auth.reset_password(username, _ask_password("Nova senha")):
        _ok(f"Senha de '{username}' redefinida.")
    else:
        _err("Falha ao redefinir.")


# ──────────────────────────────────────────────────────────────────────────────
# Menu interativo
# ──────────────────────────────────────────────────────────────────────────────

_MENU = {
    "1": ("Cadastrar operador", cmd_add),
    "2": ("Listar operadores",  cmd_list),
    "3": ("Remover operador",   cmd_remove),
    "4": ("Redefinir senha",    cmd_reset),
    "0": ("Sair",               None),
}


def _interactive_menu(auth: AuthManager) -> None:
    while True:
        print("\n  ─── MENU ───────────────────────")
        for key, (label, _) in _MENU.items():
            print(f"  [{key}] {label}")
        print("  ────────────────────────────────")

        choice = _ask("Opção")
        action = _MENU.get(choice)

        if action is None:
            _err("Opção inválida.")
            continue

        label, fn = action
        if fn is None:
            print("\n  Encerrando.\n")
            break

        try:
            fn(auth)
        except KeyboardInterrupt:
            print("\n  Operação cancelada.\n")


# ──────────────────────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────────────────────

_COMMANDS: dict[str, object] = {
    "add":    cmd_add,
    "list":   cmd_list,
    "remove": cmd_remove,
    "reset":  cmd_reset,
}


def main() -> None:
    _load_env()
    _header()

    # Portão de autenticação — nada do painel é acessível antes daqui
    if not _authenticate_admin():
        sys.exit(1)

    auth = AuthManager()

    if auth.count() == 0:
        print("\033[1;33m  AVISO: Nenhum operador cadastrado ainda.\033[0m\n")

    # Modo direto via argumento de linha de comando
    if len(sys.argv) > 1:
        cmd_name = sys.argv[1].lower()
        fn = _COMMANDS.get(cmd_name)
        if fn:
            try:
                fn(auth)
            except KeyboardInterrupt:
                print("\n  Cancelado.\n")
        else:
            _err(f"Comando desconhecido: '{cmd_name}'")
            print(f"  Disponíveis: {', '.join(_COMMANDS)}")
        return

    # Modo interativo
    try:
        _interactive_menu(auth)
    except KeyboardInterrupt:
        print("\n\n  Saindo.\n")


if __name__ == "__main__":
    main()