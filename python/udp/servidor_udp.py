import socket

OFFSET = 0

HOST = "0.0.0.0"
PORTA = 5001 + OFFSET

with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as servidor:
    servidor.bind((HOST, PORTA))
    print(f"[UDP] Servidor aguardando datagramas na porta {PORTA}...", flush=True)

    while True:
        try:
            dados, endereco_cliente = servidor.recvfrom(1024)
        except ConnectionResetError:
            print("[UDP] Um cliente anterior fechou o socket (ICMP port unreachable). Continuando.", flush=True)
            continue
        mensagem = dados.decode("utf-8")
        print(f"[UDP] Recebido de {endereco_cliente}: {mensagem}", flush=True)

        resposta = f'Monitor responde: recebi sua mensagem -> "{mensagem}"'
        servidor.sendto(resposta.encode("utf-8"), endereco_cliente)
