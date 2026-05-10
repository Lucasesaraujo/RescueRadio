"""
Testes unitários para o sistema RescueRadio

Testa:
  - Autenticação (AuthManager)
  - Funcionalidades de servidor (ChatServer)
  - Funcionalidades de cliente (ChatClient)

Execução:
  python -m pytest test_rescueradio.py -v
  ou
  python -m unittest test_rescueradio.py -v
"""

import unittest
import tempfile
import json
import os
import shutil
from pathlib import Path
from auth import AuthManager


class TestAuthManager(unittest.TestCase):
    """Testes para o gerenciador de autenticação"""

    def setUp(self):
        """Cria um arquivo temporário de usuários para cada teste"""
        # Cria arquivo temporário com JSON válido
        self.temp_dir = tempfile.mkdtemp()
        self.temp_file_path = os.path.join(self.temp_dir, "test_users.json")
        with open(self.temp_file_path, 'w') as f:
            json.dump({}, f)
        self.auth = AuthManager(self.temp_file_path)

    def tearDown(self):
        """Remove o arquivo e diretório temporários após cada teste"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_add_user_success(self):
        """Testa cadastro bem-sucedido de um novo usuário"""
        result = self.auth.add_user("alice", "senha123", "operador")
        self.assertTrue(result, "Falha ao adicionar usuário")
        self.assertTrue(self.auth.user_exists("alice"), "Usuário não foi cadastrado")

    def test_add_user_duplicate(self):
        """Testa que não pode adicionar usuário duplicado"""
        self.auth.add_user("bob", "senha123", "operador")
        result = self.auth.add_user("bob", "outra_senha", "operador")
        self.assertFalse(result, "Deveria rejeitar usuário duplicado")

    def test_verify_password_correct(self):
        """Testa verificação com senha correta"""
        self.auth.add_user("charlie", "correto123", "operador")
        result = self.auth.verify("charlie", "correto123")
        self.assertTrue(result, "Falha ao verificar senha correta")

    def test_verify_password_incorrect(self):
        """Testa verificação com senha incorreta"""
        self.auth.add_user("diana", "correto123", "operador")
        result = self.auth.verify("diana", "errado123")
        self.assertFalse(result, "Aceitou senha incorreta")

    def test_verify_nonexistent_user(self):
        """Testa verificação de usuário que não existe"""
        result = self.auth.verify("inexistente", "qualquer_senha")
        self.assertFalse(result, "Deveria rejeitar usuário inexistente")

    def test_user_exists(self):
        """Testa método user_exists"""
        self.auth.add_user("eve", "senha123", "operador")
        self.assertTrue(self.auth.user_exists("eve"), "user_exists retornou False")
        self.assertFalse(self.auth.user_exists("frank"), "user_exists retornou True para inexistente")

    def test_list_users(self):
        """Testa listagem de usuários"""
        self.auth.add_user("user1", "pwd1", "operador")
        self.auth.add_user("user2", "pwd2", "comandante")
        
        users = self.auth.list_users()
        self.assertEqual(len(users), 2, "Deveria ter 2 usuários")
        usernames = [u["username"] for u in users]
        self.assertIn("user1", usernames)
        self.assertIn("user2", usernames)

    def test_count_users(self):
        """Testa contagem de usuários"""
        self.assertEqual(self.auth.count(), 0, "Deveria começar com 0 usuários")
        
        self.auth.add_user("alice", "pwd", "operador")
        self.assertEqual(self.auth.count(), 1, "Deveria ter 1 usuário")
        
        self.auth.add_user("bob", "pwd", "operador")
        self.assertEqual(self.auth.count(), 2, "Deveria ter 2 usuários")

    def test_remove_user(self):
        """Testa remoção de usuário"""
        self.auth.add_user("grace", "pwd", "operador")
        self.assertTrue(self.auth.user_exists("grace"))
        
        result = self.auth.remove_user("grace")
        self.assertTrue(result, "Falha ao remover usuário")
        self.assertFalse(self.auth.user_exists("grace"), "Usuário não foi removido")

    def test_remove_nonexistent_user(self):
        """Testa remoção de usuário que não existe"""
        result = self.auth.remove_user("inexistente")
        self.assertFalse(result, "Deveria retornar False ao remover usuário inexistente")

    def test_password_hashing_changes_per_user(self):
        """Testa que cada usuário tem um salt diferente (hashes diferentes)"""
        self.auth.add_user("user1", "mesmasenha", "operador")
        self.auth.add_user("user2", "mesmasenha", "operador")
        
        # Carrega os dados brutos
        with open(self.temp_file_path, 'r') as f:
            data = json.load(f)
        
        hash1 = data["user1"]["hash"]
        hash2 = data["user2"]["hash"]
        
        # Hashes devem ser diferentes (salts diferentes)
        self.assertNotEqual(hash1, hash2, "Usuários com mesma senha não devem ter mesmo hash")

    def test_reset_password(self):
        """Testa redefinição de senha"""
        self.auth.add_user("henry", "senha_antiga", "operador")
        
        result = self.auth.reset_password("henry", "senha_nova")
        self.assertTrue(result, "Falha ao redefinir senha")
        
        # Verifica que a senha antiga não funciona mais
        self.assertFalse(self.auth.verify("henry", "senha_antiga"))
        
        # Verifica que a nova senha funciona
        self.assertTrue(self.auth.verify("henry", "senha_nova"))


class TestChatServerBasics(unittest.TestCase):
    """Testes básicos para o ChatServer"""

    def test_server_initialization(self):
        """Testa inicialização do servidor"""
        from server import ChatServer
        
        server = ChatServer(host="127.0.0.1", port=12346)
        self.assertEqual(server.host, "127.0.0.1")
        self.assertEqual(server.port, 12346)
        self.assertEqual(len(server.clients), 0, "Deveria começar sem clientes")
        self.assertEqual(len(server.history), 0, "Deveria começar com histórico vazio")

    def test_history_buffer_maxlen(self):
        """Testa que o histórico respeita maxlen=20"""
        from server import ChatServer
        
        server = ChatServer()
        # Adiciona 30 mensagens
        for i in range(30):
            server.add_to_history(f"Mensagem {i}".encode())
        
        # Verifica que tem no máximo 20
        self.assertLessEqual(len(server.history), 20, "Histórico excedeu maxlen")


class TestIntegrationBasic(unittest.TestCase):
    """Testes de integração básicos (sem threads/sockets)"""

    def test_auth_flow(self):
        """Testa fluxo completo de autenticação"""
        temp_dir = tempfile.mkdtemp()
        temp_file = os.path.join(temp_dir, "auth_test.json")
        
        try:
            with open(temp_file, 'w') as f:
                json.dump({}, f)
            
            auth = AuthManager(temp_file)
            
            # Cadastra operador
            self.assertTrue(auth.add_user("operador1", "senha_forte", "operador"))
            
            # Verifica que foi cadastrado
            self.assertTrue(auth.user_exists("operador1"))
            
            # Verifica autenticação
            self.assertTrue(auth.verify("operador1", "senha_forte"))
            self.assertFalse(auth.verify("operador1", "errada"))
            
        finally:
            shutil.rmtree(temp_dir)


if __name__ == "__main__":
    unittest.main()
