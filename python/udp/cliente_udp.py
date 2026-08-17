import socket

OFFSET = 0

HOST = "localhost"
PORTA = 5001 + OFFSET

with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as cliente:
    print("[UDP] Pronto para enviar. Digite 'sair' para encerrar.", flush=True)
    while True:
        try:
            mensagem = input("> ")
        except EOFError:
            break
        cliente.sendto(mensagem.encode("utf-8"), (HOST, PORTA))
        if mensagem.lower() == "sair":
            break
        dados, _ = cliente.recvfrom(1024)
        print(dados.decode("utf-8"), flush=True)
