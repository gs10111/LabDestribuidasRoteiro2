import java.io.*;
import java.net.*;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

public class ServidorTCP {
    static final int OFFSET = 0;

    public static void main(String[] args) throws IOException {
        int porta = 5000 + OFFSET;
        DateTimeFormatter formato = DateTimeFormatter.ofPattern("dd/MM/yyyy HH:mm:ss");

        try (ServerSocket servidor = new ServerSocket(porta)) {
            System.out.println("[TCP] Servidor aguardando conexoes na porta " + porta + "...");
            try (Socket cliente = servidor.accept();
                 BufferedReader entrada = new BufferedReader(
                         new InputStreamReader(cliente.getInputStream()));
                 PrintWriter saida = new PrintWriter(cliente.getOutputStream(), true)) {

                System.out.println("[TCP] Cliente conectado: " + cliente.getRemoteSocketAddress());
                String mensagem;
                while ((mensagem = entrada.readLine()) != null) {
                    System.out.println("[TCP] Recebido: " + mensagem);
                    if (mensagem.equalsIgnoreCase("sair")) {
                        saida.println("Encerrando conexao. Ate mais!");
                        break;
                    }
                    if (mensagem.equalsIgnoreCase("hora")) {
                        saida.println("Monitor responde: agora sao " + LocalDateTime.now().format(formato));
                        continue;
                    }
                    saida.println("Monitor responde: recebi sua mensagem -> \"" + mensagem + "\"");
                }
            }
        }
        System.out.println("[TCP] Servidor encerrado.");
    }
}
