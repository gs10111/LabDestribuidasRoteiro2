import asyncio
import websockets

OFFSET = 16

PORTA = 8888 + OFFSET

clientes_conectados = set()


async def tratar_conexao(websocket):
    clientes_conectados.add(websocket)
    print(f"[WebSocket] Novo aluno conectado. Total: {len(clientes_conectados)}", flush=True)
    await websocket.send("Bem-vindo(a) ao mural de avisos da turma!")
    try:
        async for mensagem in websocket:
            print(f"[WebSocket] Recebido: {mensagem}", flush=True)
            aviso_formatado = f"Aviso da turma: {mensagem}"
            websockets.broadcast(clientes_conectados, aviso_formatado)
    finally:
        clientes_conectados.remove(websocket)
        print(f"[WebSocket] Aluno desconectado. Total: {len(clientes_conectados)}", flush=True)


async def main():
    print(f"[WebSocket] Servidor do mural iniciado na porta {PORTA}.", flush=True)
    async with websockets.serve(tratar_conexao, "0.0.0.0", PORTA):
        await asyncio.Future()


asyncio.run(main())
