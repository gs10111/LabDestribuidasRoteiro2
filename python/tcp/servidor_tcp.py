import socket
from datetime import datetime

OFFSET = 16

HOST = "0.0.0.0"
PORTA = 5000 + OFFSET

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as servidor:
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    servidor.bind((HOST, PORTA))
    servidor.listen(1)
    print(f"[TCP] Servidor aguardando conexoes na porta {PORTA}...", flush=True)

    conexao, endereco = servidor.accept()
    with conexao:
        print(f"[TCP] Cliente conectado: {endereco}", flush=True)
        while True:
            dados = conexao.recv(1024).decode("utf-8").strip()
            if not dados:
                break
            print(f"[TCP] Recebido: {dados}", flush=True)
            if dados.lower() == "sair":
                conexao.sendall("Encerrando conexao. Ate mais!\n".encode("utf-8"))
                break
            if dados.lower() == "hora":
                agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                conexao.sendall(f"Monitor responde: agora sao {agora}\n".encode("utf-8"))
                continue
            resposta = f'Monitor responde: recebi sua mensagem -> "{dados}"\n'
            conexao.sendall(resposta.encode("utf-8"))

print("[TCP] Servidor encerrado.", flush=True)
