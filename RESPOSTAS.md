# RESPOSTAS — Central de Avisos da Turma

Testes feitos no Windows 10, com OpenJDK 21.0.12, Python 3.12.10, `websockets` 17.0.1 e
`Java-WebSocket` 1.5.6. Servidor e clientes rodaram sempre na mesma máquina (`localhost`).
As saídas citadas estão gravadas na pasta `logs/`.

---

## Parte A — TCP

### 1. O que acontece se você iniciar o cliente antes do servidor?

O cliente nem chega a rodar: ele quebra na hora de abrir o socket, antes de enviar qualquer
coisa. Em Java sai `java.net.ConnectException: Connection refused` na linha do
`new Socket(host, porta)`, e em Python sai `ConnectionRefusedError: [WinError 10061]` na linha
do `cliente.connect(...)`.

Isso acontece porque o TCP é orientado a conexão. Antes de trafegar qualquer byte de dados é
preciso concluir o handshake de três vias (SYN, SYN-ACK, ACK). O cliente manda o SYN para a
porta 5000, mas não existe nenhum socket em estado LISTEN ali, então o sistema operacional do
destino responde com um RST e o `connect()` falha na hora.

O que vale destacar é que a falha é imediata e explícita: o cliente descobre na hora que não
tem ninguém do outro lado. É justamente o contrário do que acontece no UDP da Parte B, onde o
envio "funciona" mesmo sem servidor nenhum.

### 2. Qual mecanismo do TCP garante a ordem das mensagens?

O número de sequência do cabeçalho TCP, junto com os ACKs e o buffer de reordenação do
receptor.

Cada byte do fluxo recebe um número de sequência, e o cabeçalho de cada segmento informa o
número do primeiro byte que ele carrega. Como os segmentos são roteados de forma independente,
eles podem chegar fora de ordem. O receptor então não entrega os dados na ordem de chegada:
ele usa os números de sequência para remontar o fluxo num buffer interno antes de passar para
a aplicação. Se faltar um segmento no meio, os posteriores ficam segurados no buffer até a
lacuna ser preenchida (é o head-of-line blocking).

A perda é resolvida pelos ACKs: o receptor confirma o que recebeu e, se o transmissor não
recebe a confirmação dentro do tempo esperado ou recebe ACKs duplicados, ele retransmite. Ou
seja, o número de sequência cuida da ordem e o ACK com retransmissão cuida da perda.

Na nossa implementação nada disso aparece no código, de propósito. O `readLine()` do Java e o
`recv()` do Python simplesmente recebem as linhas na ordem certa, porque quem faz esse
trabalho é o sistema operacional.

### 3. E se dois clientes tentassem se conectar ao mesmo tempo?

O código atual não suporta. O servidor atende um cliente só e depois encerra.

Testei com dois clientes Java no mesmo servidor (logs em `logs/q-a3-*.log`). O resultado me
surpreendeu: o cliente B chegou a imprimir "[TCP] Conectado ao servidor". Ou seja, o
`connect()` dele teve sucesso, porque o handshake TCP é feito pelo sistema operacional e a
conexão ficou parada na fila de conexões pendentes (o backlog do `ServerSocket`). Mas quando o
B mandou a mensagem dele, não veio resposta nenhuma: ele ficou travado no `readLine()`. E
quando o cliente A digitou `sair`, o servidor encerrou de vez, com o B ainda conectado. O log
do servidor mostra um único "Cliente conectado".

A causa está no `ServidorTCP.java`, onde o `accept()` é chamado uma vez só, fora de qualquer
laço:

```java
try (Socket cliente = servidor.accept();
     ...) {
    while ((mensagem = entrada.readLine()) != null) { ... }
}
```

O `while` de dentro percorre as mensagens daquele cliente, não os clientes. Quando ele termina,
o `try-with-resources` fecha tudo e o `main` retorna. A versão Python tem o mesmo problema, com
um `accept()` único.

Para aceitar vários clientes seriam necessárias duas mudanças: colocar o `accept()` dentro de
um laço infinito, para o servidor voltar a aceitar novas conexões em vez de encerrar, e tratar
cada cliente aceito numa thread separada. Sem a thread, mesmo com o laço o servidor ficaria
preso conversando com o primeiro cliente e só atenderia o segundo depois que o primeiro
saísse, que foi exatamente o comportamento serializado que observei.

---

## Parte B — UDP

### 1. O que aconteceu ao enviar mensagem com o servidor desligado?

O envio em si funcionou normalmente nas duas linguagens, sem erro nenhum. O problema só
apareceu na hora de esperar a resposta, e de um jeito diferente em cada uma: o cliente Java
travou indefinidamente no `receive()` (deixei 15 segundos e matei o processo), enquanto o
Python levantou `ConnectionResetError: [WinError 10054]` no `recvfrom()`.

Essa diferença tem uma explicação de plataforma. Quando o datagrama chega em `127.0.0.1:5001`
e não tem ninguém escutando, o Windows devolve um ICMP port unreachable. O Python repassa isso
para a aplicação como exceção, e o Java, num `DatagramSocket` não conectado, ignora o ICMP e
continua esperando para sempre. Nenhum dos dois está errado: o UDP simplesmente não define
nada sobre isso, então cada implementação decide o que fazer.

Comparando com o TCP da Parte A, lá o cliente falhou na hora, com "Connection refused", e nem
chegou a enviar dados. Aqui o cliente achou que tinha enviado com sucesso e só foi descobrir o
problema muito depois (ou nem descobriu, no caso do Java). É isso que significa ser sem
conexão: não existe handshake, não existe estado de conexão nem confirmação. O `sendto()` não
quer dizer "a mensagem chegou", e sim "entreguei o datagrama para o sistema operacional
tentar mandar". Quem quiser saber se chegou precisa implementar isso na aplicação.

Um efeito colateral disso apareceu no servidor Python: quando o cliente fechava o socket
depois do `sair`, a resposta do servidor batia numa porta já fechada, o ICMP voltava e
derrubava o servidor na iteração seguinte. Como um servidor sem conexão não pode morrer só
porque um cliente sumiu, tratei o caso no `servidor_udp.py`:

```python
try:
    dados, endereco_cliente = servidor.recvfrom(1024)
except ConnectionResetError:
    print("[UDP] Um cliente anterior fechou o socket (ICMP port unreachable). Continuando.")
    continue
```

### 2. Dois exemplos reais de aplicações que usam UDP

O primeiro é o DNS. Uma consulta é uma pergunta curta com resposta curta, as duas cabendo num
único datagrama. Abrir uma conexão TCP para isso custaria três pacotes de handshake (mais os
de fechamento) só para trafegar dois pacotes de dados, o que praticamente dobraria a latência
de toda a navegação. Como a transação é atômica e sem estado, a confiabilidade fica muito
mais barata na aplicação: se a resposta não voltar em alguns milissegundos, o resolver
simplesmente repete a pergunta ou tenta outro servidor. Não há ordem a preservar nem sessão a
manter.

O segundo é streaming de voz e vídeo em tempo real, como VoIP, videochamada e jogos online.
Aqui a confiabilidade do TCP não só é desnecessária como atrapalha. Se um pacote de áudio de
20 ms se perde, o TCP retransmitiria, mas quando a retransmissão chegasse o momento de tocar
aquele trecho já teria passado: o dado chegaria correto e inútil. Pior ainda, por causa do
head-of-line blocking o TCP seguraria todos os pacotes seguintes esperando o que faltou,
transformando uma perda de 20 ms num travamento de centenas de milissegundos. Com UDP a
aplicação descarta o pacote perdido, disfarça o buraco e segue com o áudio atual. Para mídia
em tempo real, latência baixa e constante vale mais que integridade perfeita.

### 3. Seria possível o servidor UDP saber quem está conectado?

Seria, mas o registro passaria a ser responsabilidade da aplicação, e não do transporte.

A informação já existe: o `recvfrom()` do Python devolve `(dados, endereco_cliente)` com o par
IP:porta do remetente, e no Java dá para pegar com `getAddress()` e `getPort()`. O servidor já
sabe de quem veio cada datagrama, ele só não guarda isso em lugar nenhum. Bastaria manter um
dicionário `{(ip, porta): ultimo_contato}` e criar mensagens de controle tipo `ENTRAR` e
`SAIR`.

O que muda na arquitetura é a parte interessante. Primeiro, detectar quem saiu vira um
problema: em TCP o servidor recebe um EOF quando o cliente fecha, mas em UDP não existe evento
de desconexão, e um cliente que fechou a janela é indistinguível de um cliente calado. A saída
seria heartbeat, com o cliente mandando um sinal periódico e o servidor expirando quem passou
do timeout, o que adiciona tráfego constante e um parâmetro chato de calibrar. Segundo, o
endereço não serve como identidade confiável: um cliente atrás de NAT pode ter a porta
remapeada e um celular que troca de Wi-Fi para 4G muda de IP, então seria preciso um ID de
sessão dentro da própria mensagem. Terceiro, como o UDP permite duplicação e reordenação, um
`ENTRAR` duplicado ou um `SAIR` atrasado poderia corromper o registro, exigindo números de
sequência. E ainda tem a segurança: sem handshake é trivial forjar o IP de origem e mandar um
`SAIR` no nome de outro aluno.

Repare que essa lista toda é basicamente uma reimplementação manual, e pior, de coisas que o
TCP já entrega prontas. É esse o trade-off entre os dois: o UDP não é um TCP mais simples, é
um TCP sem as garantias, com a conta de implementá-las sobrando para quem precisar delas.

---

## Parte C — Multicast

### 1. Unicast repetido 3 vezes contra um único envio multicast

A diferença está em onde as cópias da mensagem são criadas.

No unicast repetido, o remetente monta e transmite três pacotes independentes, cada um com um
IP de destino diferente, e os três saem pelo mesmo enlace. Se cada aviso tem 1 KB, o servidor
gasta 3 KB de upload; com 30 alunos são 30 KB, com 300 são 300 KB. O custo no remetente cresce
junto com o número de destinatários, e o enlace do servidor vira o gargalo. Fora que a
aplicação precisa manter a lista de todo mundo e saber o endereço de cada um.

No multicast, o remetente transmite um pacote só, endereçado ao grupo `230.0.0.1` e não a
alguém específico. A replicação é feita pela própria rede: switches e roteadores duplicam o
pacote apenas nos pontos de ramificação, e só nos ramos onde existe pelo menos um inscrito.
Assim cada enlace carrega no máximo uma cópia, não importa quantos receptores tenha adiante, e
o custo no remetente fica constante.

Isso ficou visível no teste: os dois clientes receberam os cinco avisos, mas o servidor
imprimiu "Enviado" só cinco vezes, uma por aviso e não uma por cliente. Cinco envios para dez
recebimentos.

A contrapartida é que o multicast só funciona onde a rede coopera, com suporte a IGMP nos
switches e roteadores configurados para encaminhá-lo. Por isso ele é comum em redes
controladas, como IPTV de operadora e redes corporativas, e praticamente inexistente na
Internet aberta.

### 2. O que é o TTL e por que ele importa

O TTL é um campo de 8 bits do cabeçalho IP que funciona como contador de saltos, e não como
medida de tempo, apesar do nome. O remetente define um valor inicial, cada roteador que
encaminha o pacote decrementa em 1, e quando chega a zero o pacote é descartado.

No nosso código o TTL é 2 nas duas linguagens, com
`sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)` em Python e
`socket.setTimeToLive(2)` em Java. Isso quer dizer que os avisos atravessam no máximo dois
roteadores antes de morrer.

Ele importa por dois motivos. O principal é delimitar o alcance do grupo. Em unicast o pacote
vai para um destino conhecido e o TTL é só uma proteção contra loops, mas em multicast o
pacote é entregue a qualquer um que se inscreva, e o endereço de grupo não diz nada sobre
localização. O TTL vira então o controle de até onde o aviso deve chegar: com 1 ele não passa
de nenhum roteador e fica na sub-rede local, valores abaixo de 32 costumam cobrir o mesmo
campus, e 255 é sem restrição. No cenário do roteiro, um aviso da turma não deveria escapar do
laboratório; um TTL alto demais faria esse tráfego vazar para o resto da rede da instituição.

O segundo motivo é evitar tempestade de pacotes. Como o multicast é replicado pela rede, um
erro de configuração ou um loop de roteamento poderia multiplicar um único pacote
indefinidamente, e o TTL garante que todo pacote tenha vida finita.

Nos meus testes o TTL nunca chegou a ser decrementado, porque servidor e clientes estavam na
mesma máquina e os pacotes não passaram por roteador nenhum. Até TTL 1 teria funcionado. O
efeito só apareceria com as máquinas em sub-redes diferentes.

### 3. Um cliente que ficou offline recebe os avisos que perdeu?

Não, os avisos perdidos somem de vez.

Testei isso de propósito (log em `logs/q-c3-cliente-atrasado.log`): deixei o servidor começar a
enviar os cinco avisos e só subi o cliente uns cinco segundos depois. Ele recebeu apenas os
avisos #4 e #5, que foram enviados depois de ele entrar no grupo:

```
[Multicast] Inscrito no grupo 230.0.0.1:4446. Aguardando avisos...
[Multicast] Recebido: Aviso #4: a aula comeca em 1 minuto(s)!
[Multicast] Recebido: Aviso #5: a aula comeca em 0 minuto(s)!
```

Os avisos #1 a #3 nunca chegaram e não há nada no protocolo que permita recuperá-los. O
multicast roda sobre UDP, então não existe buffer nem retransmissão: o datagrama é enviado uma
vez e descartado, sem fila de pendências nem histórico em lugar nenhum, nem no remetente nem
na rede.

Mas o motivo mais de fundo é que o remetente não sabe quem são os destinatários. Essa é
justamente a característica que dá escalabilidade ao multicast, só que ela tem um preço: como
o servidor não mantém lista de membros, ele não tem como perceber que alguém ficou de fora, e
muito menos para quem reenviar. Ele envia para o grupo, não para uma pessoa. É um modelo de
publish/subscribe sem estado, parecido com transmissão de rádio: quem não estava sintonizado
na hora não ouviu. E a inscrição via `IP_ADD_MEMBERSHIP` diz à rede "a partir de agora me
encaminhe o tráfego deste grupo", que é sobre o presente e não uma assinatura com histórico.

Para o cliente atrasado receber o que perdeu, seria preciso construir uma camada acima do
multicast: numerar os avisos (o nosso já tem "Aviso #N", o que permitiria detectar a lacuna),
manter um servidor de histórico consultável por unicast e fazer o cliente pedir o que faltou
ao entrar. É o tipo de garantia que protocolos de reliable multicast, como PGM e NORM,
precisam acrescentar.

Esse é o contraste direto com a Parte D: lá o servidor mantém a lista de conexões, então ele
poderia guardar e reenviar o histórico para quem chega depois, coisa que o multicast não
consegue fazer por construção.

---

## Parte D — WebSocket

### 1. O que muda depois do handshake `Upgrade: websocket`?

O que muda é o protocolo falado sobre a conexão TCP, não a conexão em si.

Tudo começa como uma requisição HTTP normal, com os cabeçalhos `Upgrade: websocket`,
`Connection: Upgrade` e uma `Sec-WebSocket-Key` aleatória. O servidor responde com o status
`101 Switching Protocols`, em vez do 200 de sempre, devolvendo em `Sec-WebSocket-Accept` um
hash da chave enviada, que prova que ele entendeu o protocolo. Daí em diante a mesma conexão
TCP para de transportar HTTP e passa a transportar quadros WebSocket.

Na prática mudam quatro coisas. A primeira é que a comunicação deixa de ser
requisição/resposta e vira full-duplex: no HTTP clássico o servidor só fala quando perguntado,
e depois do upgrade os dois lados podem enviar a qualquer momento. É o que torna o mural
possível, porque quando um cliente publicou um aviso o servidor empurrou a mensagem para o
outro, que não tinha pedido nada. A segunda é o tamanho: cada mensagem HTTP carrega dezenas ou
centenas de bytes de cabeçalho, enquanto um quadro WebSocket tem de 2 a 14 bytes, o que faz
muita diferença em mensagens curtas e frequentes. A terceira é que a conexão fica aberta até
alguém fechá-la, o que permite ao servidor manter identidade de cada cliente; é exatamente o
que faz o `getConnections()` do Java e o `clientes_conectados` do Python funcionarem, e os
logs mostram esse estado sendo mantido em "Total: 1", "Total: 2" e "Total: 0". A quarta é que
passa a existir um protocolo de controle próprio, com quadros de ping/pong para manter a
conexão viva e um quadro de close com código de encerramento, que no `MuralCliente.java` é o
`sendClose(WebSocket.NORMAL_CLOSURE, ...)`.

Vale notar o que não muda: continua sendo a mesma conexão TCP, na mesma porta, sem reconexão
nenhuma. É por isso que o WebSocket atravessa firewalls e proxies corporativos que só liberam
as portas 80 e 443, já que para a infraestrutura aquilo começou como tráfego HTTP legítimo.

### 2. Como o WebSocket e o multicast descobrem e alcançam os destinatários?

Os dois entregam uma mensagem a vários destinatários, mas em camadas diferentes, e isso muda
tudo.

No multicast o endereçamento é implícito. O servidor manda um datagrama para `230.0.0.1` e
pronto; ele nunca soube nem vai saber quem estava ouvindo. A descoberta acontece do lado
oposto: é o receptor que se inscreve com `joinGroup` ou `IP_ADD_MEMBERSHIP`, e é a rede que
passa a encaminhar o tráfego do grupo para ele. Remetente e destinatários ficam totalmente
desacoplados.

No WebSocket não existe mágica de rede nenhuma. O servidor mantém uma estrutura de dados na
memória com as conexões vivas e itera sobre ela, mandando uma cópia por conexão:

```java
for (WebSocket cliente : getConnections()) {
    cliente.send(avisoFormatado);
}
```

O `websockets.broadcast(clientes_conectados, aviso_formatado)` do Python faz o mesmo laço
internamente, sobre o `set` que o código alimenta no `tratar_conexao`. A descoberta é
simplesmente o cliente ter aberto uma conexão TCP e o servidor ter guardado ela na lista.

As consequências práticas são três. A escalabilidade é invertida: o multicast é imbatível em
banda no remetente, que é constante, mas depende da rede inteira cooperar, enquanto o
WebSocket custa N cópias e funciona em qualquer lugar que tenha TCP, que é a razão de o mural
ser viável na Internet e o multicast não. A confiabilidade também difere, porque no WebSocket
cada cópia vai por uma conexão TCP com as garantias da Parte A, e no multicast um aviso
perdido some. E o conhecimento do estado muda o que dá para fazer: como o servidor WebSocket
tem a lista, ele consegue contar os conectados (os logs imprimem "Total: 2"), mandar mensagem
para um aluno só ou guardar histórico para quem chegar atrasado, coisas que o multicast não
permite nem em princípio.

Resumindo, no multicast a rede resolve a distribuição e o remetente não conhece ninguém; no
WebSocket o remetente conhece todo mundo e resolve a distribuição sozinho.

### 3. Por que o WebSocket é melhor que TCP cru para o mural?

Os dois são conexões TCP contínuas mesmo. A diferença é tudo o que o WebSocket padroniza por
cima e que, com TCP puro, a gente teria que inventar por conta própria.

O ponto central é que o TCP é um fluxo de bytes e não de mensagens. Ele não preserva
fronteiras: se a aplicação envia "aviso1" e "aviso2", o outro lado pode receber
"aviso1aviso2" de uma vez, ou "avi" e depois "so1aviso2". Alguém precisa delimitar onde
termina cada mensagem. Na Parte A resolvi isso com `\n` como separador, usando `readLine()` no
Java e `readline()` no Python. Funciona, mas é um protocolo caseiro e frágil, que quebraria se
uma mensagem contivesse quebra de linha e que não trata dados binários. O WebSocket já traz
enquadramento definido, com o tamanho no cabeçalho, suporte a texto e binário e fragmentação
de mensagens grandes, e por isso o `onMessage(WebSocket conexao, String mensagem)` entrega a
mensagem inteira sem a aplicação precisar pensar nisso.

O segundo problema é que o nosso cliente TCP é lock-step, não full-duplex. No `ClienteTCP.java`
o `entrada.readLine()` vem logo depois do `saida.println(linha)`, então o cliente só consegue
ler depois de escrever. Se o servidor quisesse empurrar um aviso espontâneo, o cliente só o
veria quando ele mesmo resolvesse mandar alguma coisa, o que para um mural é fatal. Corrigir
exigiria uma thread separada só para leitura. Na Parte D isso já vem pronto pelo modelo de
eventos, com o `onText()` do Java e o `async for mensagem in websocket` do Python sendo
chamados quando a mensagem chega, e foi o que permitiu que os dois clientes recebessem o aviso
um do outro em tempo real.

Além disso, uma conexão TCP crua na porta 5000 é bloqueada por praticamente qualquer firewall
corporativo, enquanto o WebSocket começa como HTTP na 80 ou 443 e passa, ganhando criptografia
de graça com `wss://`. Um mural de verdade também seria uma página web, e navegadores não
deixam abrir sockets TCP arbitrários por JavaScript, mas oferecem a API `WebSocket`
nativamente. E ainda vem com gestão de conexão pronta: ping/pong para detectar clientes que
sumiram sem avisar, códigos de fechamento padronizados e os callbacks `onClose` e `onError`,
que no nosso código mantêm o contador de conectados coerente.

No fim, o TCP cru resolve o transporte e o WebSocket resolve a conversa. Dá para implementar
tudo isso sobre TCP puro, e a Parte A prova que dá, mas seria reinventar de forma
proprietária, e provavelmente com bugs, um protocolo que já existe, está na RFC 6455 e é
suportado por todo navegador e biblioteca de rede moderna.
