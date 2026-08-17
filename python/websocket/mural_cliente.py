import asyncio
import websockets

OFFSET = 0

PORTA = 8888 + OFFSET


async def escutar(websocket):
    async for mensagem in websocket:
        print(f"\n{mensagem}", flush=True)
        print("> ", end="", flush=True)


async def main():
    uri = f"ws://localhost:{PORTA}"
    async with websockets.connect(uri) as websocket:
        print("[WebSocket] Conectado ao mural. Digite 'sair' para encerrar.", flush=True)
        tarefa_escuta = asyncio.create_task(escutar(websocket))

        loop = asyncio.get_running_loop()
        while True:
            try:
                mensagem = await loop.run_in_executor(None, input, "> ")
            except EOFError:
                break
            if mensagem.lower() == "sair":
                break
            await websocket.send(mensagem)

        tarefa_escuta.cancel()


asyncio.run(main())
