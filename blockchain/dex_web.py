# -*- coding: utf-8 -*-
# c:/Users/Work/Desktop/DEX SOL MARBL/dex_web.py
import json
import os
import time
import mimetypes
from urllib.parse import parse_qs
from wsgiref.util import setup_testing_defaults
from .cosmic_blockchain import CosmicAccount

# Variáveis globais sobrescritas por main.py
blockchain = None
explorer = None
pool_contract_id = None
network = None
contract_manager = None
bridge = None
ai = None

# Função auxiliar para verificar dependências
def check_dependencies():
    if not blockchain or not explorer or not contract_manager:
        return False, {"error": "Server dependencies not initialized"}, 500
    return True, None, 200

# Função para criar respostas JSON
def json_response(data, status=200):
    body = json.dumps(data).encode('utf-8')
    headers = [
        ('Content-Type', 'application/json'),
        ('Content-Length', str(len(body)))
    ]
    return status, headers, body
    
# Função para ler e retornar templates HTML
def template_response(template_name, status=200):
    template_path = os.path.join('templates', template_name)
    try:
        with open(template_path, 'rb') as f:
            body = f.read()
        headers = [
            ('Content-Type', 'text/html; charset=utf-8'),
            ('Content-Length', str(len(body)))
        ]
        return status, headers, body
    except FileNotFoundError:
        return json_response({"error": f"Template {template_name} not found"}, 404)
        
# Função para servir arquivos estáticos
def static_response(file_path, status=200):
    try:
        with open(file_path, 'rb') as f:
            body = f.read()
        
        content_type, _ = mimetypes.guess_type(file_path)
        if not content_type:
            content_type = 'application/octet-stream'
            
        headers = [
            ('Content-Type', content_type),
            ('Content-Length', str(len(body)))
        ]
        return status, headers, body
    except FileNotFoundError:
        return json_response({"error": f"File {file_path} not found"}, 404)

# Função principal WSGI
def application(environ, start_response):
    setup_testing_defaults(environ)
    path = environ.get('PATH_INFO', '')
    method = environ.get('REQUEST_METHOD', 'GET')
    content_length = int(environ.get('CONTENT_LENGTH', 0))
    body = environ['wsgi.input'].read(content_length).decode('utf-8') if content_length > 0 else ''
    
    # Verifica dependências para todas as rotas
    dep_ok, error_data, status = check_dependencies()
    if not dep_ok:
        status_str = f"{status} Internal Server Error"
        headers, response_body = json_response(error_data)[1:]
        start_response(status_str, headers)
        return [response_body]

    # Roteamento
    # Rota para arquivos estáticos
    if path.startswith('/static/') and method == "GET":
        file_path = path[1:]  # Remove a barra inicial
        status, headers, response = static_response(file_path)
        start_response(f"{status} OK" if status == 200 else f"{status} Not Found", headers)
        return [response]
        
    # Rota raiz para a interface HTML
    if path == "/" and method == "GET":
        status, headers, response = template_response('index.html')
        start_response(f"{status} OK" if status == 200 else f"{status} Not Found", headers)
        return [response]

    elif path == "/status" and method == "GET":
        data = {
            "status": "online",
            "blockchain_height": len(blockchain.chain),
            "pending_transactions": len(blockchain.pending_transactions),
            "timestamp": time.time()
        }
        status, headers, response = json_response(data)
        start_response(f"{status} OK", headers)
        return [response]

    elif path.startswith("/account/") and method == "GET":
        address = path.split("/account/")[-1]
        account = blockchain.accounts.get(address)
        if not account:
            data = {"error": "Account not found"}
            status, headers, response = json_response(data, 404)
            start_response(f"{status} Not Found", headers)
            return [response]
        data = {
            "address": account.address,
            "energy_balance": str(account.get_balance("ENERGY", blockchain.db_path)),
            "cecle_balance": str(account.get_balance("5vmiteBPb7SYj4s1HmNFbb3kWSuaUu4waENx4vSQDmbs", blockchain.db_path)),
            "stake": str(account.stake),
            "validator": account.validator
        }
        status, headers, response = json_response(data)
        start_response(f"{status} OK", headers)
        return [response]

    elif path == "/account/create" and method == "POST":
        new_account = blockchain.register_account()
        data = {
            "address": new_account.address,
            "private_key": new_account.private_key.hex(),  # Apenas para teste!
            "message": "Account created successfully"
        }
        status, headers, response = json_response(data)
        start_response(f"{status} OK", headers)
        return [response]

    elif path.startswith("/balance/") and method == "GET":
        token = path.split("/balance/")[-1]
        balance = explorer.get_balance(token, blockchain.db_path)
        data = {"token": token, "balance": str(balance)}
        status, headers, response = json_response(data)
        start_response(f"{status} OK", headers)
        return [response]

    elif path == "/transfer" and method == "POST":
        try:
            data = json.loads(body)
            recipient = data.get("recipient")
            amount = float(data.get("amount"))
            token = data.get("token")
            if not all([recipient, amount, token]):
                data = {"error": "Missing required fields: recipient, amount, token"}
                status, headers, response = json_response(data, 400)
                start_response(f"{status} Bad Request", headers)
                return [response]
            
            if explorer.get_balance(token, blockchain.db_path) < amount:
                data = {"error": "Insufficient balance"}
                status, headers, response = json_response(data, 400)
                start_response(f"{status} Bad Request", headers)
                return [response]
            
            tx_data = {
                "sender": explorer.address,
                "recipient": recipient,
                "amount": amount,
                "token": token,
                "timestamp": time.time()
            }
            signature = explorer.sign(tx_data)
            success, message = blockchain.add_transaction("transfer", tx_data, signature, explorer.address)
            
            if success:
                data = {"message": message, "tx_data": tx_data}
                status, headers, response = json_response(data)
                start_response(f"{status} OK", headers)
                return [response]
            else:
                data = {"error": message}
                status, headers, response = json_response(data, 400)
                start_response(f"{status} Bad Request", headers)
                return [response]
        except (ValueError, json.JSONDecodeError):
            data = {"error": "Invalid request data"}
            status, headers, response = json_response(data, 400)
            start_response(f"{status} Bad Request", headers)
            return [response]

    elif path == "/stake" and method == "POST":
        try:
            data = json.loads(body)
            amount = float(data.get("amount"))
            if not amount:
                data = {"error": "Missing required field: amount"}
                status, headers, response = json_response(data, 400)
                start_response(f"{status} Bad Request", headers)
                return [response]
            
            success, message = explorer.stake_tokens(amount, blockchain.db_path)
            if success:
                data = {"message": message}
                status, headers, response = json_response(data)
                start_response(f"{status} OK", headers)
                return [response]
            else:
                data = {"error": message}
                status, headers, response = json_response(data, 400)
                start_response(f"{status} Bad Request", headers)
                return [response]
        except (ValueError, json.JSONDecodeError):
            data = {"error": "Invalid request data"}
            status, headers, response = json_response(data, 400)
            start_response(f"{status} Bad Request", headers)
            return [response]

    else:
        data = {"error": "Not Found"}
        status, headers, response = json_response(data, 404)
        start_response(f"{status} Not Found", headers)
        return [response]

# Para rodar standalone (opcional, para testes locais)
if __name__ == "__main__":
    # Inicializar o sistema de MIME types
    mimetypes.init()
    
    from wsgiref.simple_server import make_server
    httpd = make_server('localhost', 8000, application)
    print("Serving on http://localhost:8000...")
    print("Templates directory:", os.path.abspath('templates'))
    print("Static files directory:", os.path.abspath('static'))
    httpd.serve_forever()
