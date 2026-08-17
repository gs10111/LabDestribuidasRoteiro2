# Central de Avisos da Turma — Lab de Redes

Roteiro 2 (U0, Nivelamento de Redes) da disciplina de Laboratório de Desenvolvimento de
Aplicações Móveis e Distribuídas. O mesmo cenário, uma central de avisos da turma, foi
implementado com quatro protocolos, cada um em Java e em Python.

| Parte | Protocolo | Papel no cenário | Porta base |
|---|---|---|---|
| A | TCP | conversa privada e confiável com o monitor | 5000 |
| B | UDP | mesmo pedido, sem garantia de entrega | 5001 |
| C | Multicast | aviso do professor para todos de uma vez | 4446 |
| D | WebSocket | mural de avisos em tempo real | 8887 (Java) / 8888 (Python) |

## Estrutura

```
java/          tcp/ udp/ multicast/ websocket/
python/        tcp/ udp/ multicast/ websocket/
evidencias/    prints de execução, um por protocolo/linguagem
logs/          saída capturada nas execuções de teste
scripts/       demo.ps1, abre os terminais de cada parte
RESPOSTAS.md   as 12 questões do roteiro
```

## Ambiente

Testado no Windows 10 com OpenJDK 21.0.12, Python 3.12.10, `websockets` 17.0.1 e
`Java-WebSocket` 1.5.6.

```powershell
java -version
python --version
python -m pip install websockets
```

O `pom.xml` da Parte D está no repositório conforme o roteiro, mas a compilação usa a
alternativa da seção 7.2, com os `.jar` em `java/websocket/lib/`. Para baixá-los:

```powershell
cd java/websocket/lib
$base = "https://repo1.maven.org/maven2"
Invoke-WebRequest "$base/org/java-websocket/Java-WebSocket/1.5.6/Java-WebSocket-1.5.6.jar" -OutFile "Java-WebSocket-1.5.6.jar"
Invoke-WebRequest "$base/org/slf4j/slf4j-api/2.0.9/slf4j-api-2.0.9.jar" -OutFile "slf4j-api-2.0.9.jar"
Invoke-WebRequest "$base/org/slf4j/slf4j-simple/2.0.9/slf4j-simple-2.0.9.jar" -OutFile "slf4j-simple-2.0.9.jar"
```

## OFFSET das portas

Cada arquivo tem uma constante `OFFSET` no topo, somada à porta base (seção 3.3 do roteiro).
Ela está em `0` e deve ser trocada pelos dois últimos dígitos do RA antes de rodar em máquina
compartilhada, usando o mesmo valor no servidor e no cliente da mesma parte.

## Como executar

O script abaixo abre os terminais já na pasta certa, com `Get-Date` na tela para a evidência,
compilando o Java quando necessário:

```powershell
.\scripts\demo.ps1 -Parte tcp       -Linguagem java
.\scripts\demo.ps1 -Parte udp       -Linguagem python
.\scripts\demo.ps1 -Parte multicast -Linguagem java
.\scripts\demo.ps1 -Parte websocket -Linguagem python
```

Manualmente, seguindo o roteiro:

```powershell
cd java/tcp;   javac ServidorTCP.java ClienteTCP.java;  java ServidorTCP;  java ClienteTCP
cd java/udp;   javac ServidorUDP.java ClienteUDP.java;  java ServidorUDP;  java ClienteUDP
cd java/multicast; javac ServidorMulticast.java ClienteMulticast.java; java ClienteMulticast; java ServidorMulticast
cd python/tcp;       python servidor_tcp.py;       python cliente_tcp.py
cd python/udp;       python servidor_udp.py;       python cliente_udp.py
cd python/multicast; python cliente_multicast.py;  python servidor_multicast.py
cd python/websocket; python mural_servidor.py;     python mural_cliente.py
```

Parte D em Java:

```powershell
cd java/websocket
javac -cp "lib/*" -d out src/main/java/MuralServidor.java
javac -d out src/main/java/MuralCliente.java
java -cp "out;lib/*" MuralServidor
java -cp out MuralCliente
```

No multicast e no WebSocket, suba os clientes antes do servidor e abra dois deles para ver a
entrega simultânea.

Na primeira execução de cada servidor o Firewall do Windows pede autorização. É preciso clicar
em "Permitir acesso", senão as mensagens não chegam.

## Diferenças em relação ao código do roteiro

Os servidores TCP respondem à mensagem `hora` com o horário atual, como pede a tarefa 4.5.3. O
`accept()` continua sendo chamado uma vez só, então apenas um cliente é atendido; esse
comportamento está analisado na questão A3 do `RESPOSTAS.md`.

O servidor UDP em Python trata `ConnectionResetError`, porque no Windows um cliente que fecha o
socket gera um ICMP port unreachable que derrubaria o servidor na iteração seguinte.

O cliente multicast em Java se inscreve no grupo por todas as interfaces ativas que suportam
multicast, em vez de depender de `InetAddress.getLocalHost()`, que escolhe a interface errada
quando a máquina tem adaptadores virtuais de Hyper-V, WSL ou VPN.
