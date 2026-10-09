package de.jojo.ai;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.Scanner;
import java.util.UUID;

/**
 * Konsolen-Client für deine eigene AI (Java 8 kompatibel, keine Bibliotheken).
 * Spricht mit python/server.py.
 */
public class ChatClient {

    private static final String SERVER_URL = "http://localhost:8080/chat";

    public static void main(String[] args) {
        String sessionId = UUID.randomUUID().toString();
        Scanner scanner = new Scanner(System.in, "UTF-8");

        System.out.println("Chat gestartet. Tippe 'exit' zum Beenden.\n");

        while (true) {
            System.out.print("Du: ");
            if (!scanner.hasNextLine()) break;
            String input = scanner.nextLine().trim();
            if (input.equalsIgnoreCase("exit")) break;
            if (input.isEmpty()) continue;

            try {
                System.out.println("AI: " + send(input, sessionId) + "\n");
            } catch (IOException e) {
                System.out.println("Server nicht erreichbar. Läuft python/server.py? (" + e.getMessage() + ")\n");
            }
        }
        System.out.println("Tschüss!");
    }

    private static String send(String message, String sessionId) throws IOException {
        HttpURLConnection con = (HttpURLConnection) new URL(SERVER_URL).openConnection();
        con.setRequestMethod("POST");
        con.setConnectTimeout(10_000);
        con.setReadTimeout(300_000);
        con.setDoOutput(true);
        con.setRequestProperty("X-Session", sessionId);
        con.setRequestProperty("Content-Type", "text/plain; charset=utf-8");

        try (OutputStream out = con.getOutputStream()) {
            out.write(message.getBytes(StandardCharsets.UTF_8));
        }

        int code = con.getResponseCode();
        InputStream in = code >= 400 ? con.getErrorStream() : con.getInputStream();
        return readAll(in);
    }

    private static String readAll(InputStream in) throws IOException {
        if (in == null) return "";
        ByteArrayOutputStream buffer = new ByteArrayOutputStream();
        byte[] chunk = new byte[4096];
        int n;
        while ((n = in.read(chunk)) != -1) {
            buffer.write(chunk, 0, n);
        }
        return new String(buffer.toByteArray(), StandardCharsets.UTF_8);
    }
}
