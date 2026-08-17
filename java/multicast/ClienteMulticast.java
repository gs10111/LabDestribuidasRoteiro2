import java.net.*;
import java.io.IOException;
import java.util.Enumeration;

public class ClienteMulticast {
    static final int OFFSET = 16;

    public static void main(String[] args) throws IOException {
        String grupoMulticast = "230.0.0.1";
        int porta = 4446 + OFFSET;

        try (MulticastSocket socket = new MulticastSocket(porta)) {
            InetAddress grupo = InetAddress.getByName(grupoMulticast);
            InetSocketAddress endpointGrupo = new InetSocketAddress(grupo, porta);

            int inscricoes = 0;
            Enumeration<NetworkInterface> interfaces = NetworkInterface.getNetworkInterfaces();
            while (interfaces.hasMoreElements()) {
                NetworkInterface interfaceRede = interfaces.nextElement();
                if (!interfaceRede.isUp() || !interfaceRede.supportsMulticast()) {
                    continue;
                }
                try {
                    socket.joinGroup(endpointGrupo, interfaceRede);
                    inscricoes++;
                } catch (IOException e) {
                    continue;
                }
            }

            if (inscricoes == 0) {
                System.out.println("[Multicast] Nenhuma interface aceitou a inscricao no grupo.");
                return;
            }

            System.out.println("[Multicast] Inscrito no grupo " + grupoMulticast + ":" + porta
                    + " em " + inscricoes + " interface(s). Aguardando avisos...");

            byte[] buffer = new byte[1024];
            while (true) {
                DatagramPacket pacote = new DatagramPacket(buffer, buffer.length);
                socket.receive(pacote);
                String mensagem = new String(pacote.getData(), 0, pacote.getLength());
                System.out.println("[Multicast] Recebido: " + mensagem);
            }
        }
    }
}
