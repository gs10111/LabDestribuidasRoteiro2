import socket

OFFSET = 16

HOST = "localhost"
PORTA = 5000 + OFFSET

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as cliente:
    cliente.connect((HOST, PORTA))
    print("[TCP] Conectado ao servidor. Digite 'sair' para encerrar.", flush=True)
    arquivo = cliente.makefile("r")

    while True:
        try:
            mensagem = input("> ")
        except EOFError:
            break
        cliente.sendall((mensagem + "\n").encode("utf-8"))
        print(arquivo.readline().strip(), flush=True)
        if mensagem.lower() == "sair":
            break
