package de.jojo.ai;

import java.io.IOException;
import java.util.UUID;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

import javafx.application.Application;
import javafx.concurrent.Task;
import javafx.geometry.Insets;
import javafx.geometry.Pos;
import javafx.scene.Scene;
import javafx.scene.control.Button;
import javafx.scene.control.Label;
import javafx.scene.control.ScrollPane;
import javafx.scene.control.TextArea;
import javafx.scene.input.KeyCode;
import javafx.scene.layout.BorderPane;
import javafx.scene.layout.HBox;
import javafx.scene.layout.Priority;
import javafx.scene.layout.Region;
import javafx.scene.layout.VBox;
import javafx.stage.Stage;

public class GuiChatClient extends Application {

    private final ExecutorService requests = Executors.newSingleThreadExecutor(runnable -> {
        Thread thread = new Thread(runnable, "ai-chat-request");
        thread.setDaemon(true);
        return thread;
    });

    private final VBox messages = new VBox(18);
    private final TextArea input = new TextArea();
    private final Button sendButton = new Button("Senden  ➤");
    private final Button newChatButton = new Button("+  Neuer Chat");
    private final Label connectionStatus = new Label("BEREIT");
    private ScrollPane chatScroll;
    private String sessionId = UUID.randomUUID().toString();
    private Label pendingMessage;

    @Override
    public void start(Stage stage) {
        BorderPane root = new BorderPane();
        root.getStyleClass().add("app-root");
        root.setLeft(createSidebar());
        root.setCenter(createChatArea());

        Scene scene = new Scene(root, 1100, 760);
        scene.getStylesheets().add(getClass().getResource("/de/jojo/ai/chat.css").toExternalForm());
        stage.setTitle("AI Studio - Lokaler Chat");
        stage.setMinWidth(820);
        stage.setMinHeight(620);
        stage.setScene(scene);
        stage.show();
        input.requestFocus();
    }

    private VBox createSidebar() {
        VBox sidebar = new VBox(24);
        sidebar.getStyleClass().add("sidebar");
        sidebar.setPrefWidth(250);
        sidebar.setPadding(new Insets(26, 18, 20, 18));

        HBox brand = new HBox(12);
        brand.setAlignment(Pos.CENTER_LEFT);
        Label mark = new Label("AI");
        mark.getStyleClass().add("brand-mark");
        VBox brandText = new VBox(2);
        Label name = new Label("AI STUDIO");
        name.getStyleClass().add("brand-name");
        Label caption = new Label("DEIN LOKALES MODELL");
        caption.getStyleClass().add("brand-caption");
        brandText.getChildren().addAll(name, caption);
        brand.getChildren().addAll(mark, brandText);

        newChatButton.getStyleClass().add("new-chat-button");
        newChatButton.setMaxWidth(Double.MAX_VALUE);
        newChatButton.setOnAction(event -> startNewChat());

        VBox navigation = new VBox(10);
        Label section = new Label("WORKSPACE");
        section.getStyleClass().add("section-label");
        Label selectedChat = new Label("◉   Lokaler Chat");
        selectedChat.getStyleClass().addAll("nav-item", "nav-item-selected");
        navigation.getChildren().addAll(section, selectedChat);

        Region spacer = new Region();
        VBox.setVgrow(spacer, Priority.ALWAYS);

        VBox serverCard = new VBox(7);
        serverCard.getStyleClass().add("server-card");
        HBox statusLine = new HBox(8);
        statusLine.setAlignment(Pos.CENTER_LEFT);
        Label statusDot = new Label("●");
        statusDot.getStyleClass().add("status-dot");
        connectionStatus.getStyleClass().add("server-status");
        statusLine.getChildren().addAll(statusDot, connectionStatus);
        Label serverAddress = new Label("localhost:8080");
        serverAddress.getStyleClass().add("server-address");
        Label serverHint = new Label("Lokaler Python-Server");
        serverHint.getStyleClass().add("server-hint");
        serverCard.getChildren().addAll(statusLine, serverAddress, serverHint);

        sidebar.getChildren().addAll(brand, newChatButton, navigation, spacer, serverCard);
        return sidebar;
    }

    private BorderPane createChatArea() {
        BorderPane chatArea = new BorderPane();
        chatArea.getStyleClass().add("chat-area");
        chatArea.setTop(createHeader());

        messages.getStyleClass().add("messages");
        messages.setPadding(new Insets(28, 34, 32, 34));
        addAssistantMessage("Hallo! Ich bin dein lokaler AI-Assistent. Stell mir eine Frage, "
                + "und ich antworte mit deinem eigenen Modell.");

        chatScroll = new ScrollPane(messages);
        chatScroll.setFitToWidth(true);
        chatScroll.getStyleClass().add("chat-scroll");
        chatArea.setCenter(chatScroll);
        chatArea.setBottom(createComposer());
        return chatArea;
    }

    private HBox createHeader() {
        HBox header = new HBox();
        header.getStyleClass().add("chat-header");
        header.setAlignment(Pos.CENTER_LEFT);
        header.setPadding(new Insets(22, 34, 20, 34));

        VBox title = new VBox(4);
        Label heading = new Label("AI Assistant");
        heading.getStyleClass().add("header-title");
        Label subtitle = new Label("Ein privater Chat, direkt auf deinem Rechner");
        subtitle.getStyleClass().add("header-subtitle");
        title.getChildren().addAll(heading, subtitle);

        Region spacer = new Region();
        HBox.setHgrow(spacer, Priority.ALWAYS);
        Label modelBadge = new Label("●  EIGENES MODELL");
        modelBadge.getStyleClass().add("model-badge");
        header.getChildren().addAll(title, spacer, modelBadge);
        return header;
    }

    private VBox createComposer() {
        VBox wrapper = new VBox();
        wrapper.getStyleClass().add("composer-wrap");
        wrapper.setPadding(new Insets(14, 34, 22, 34));

        HBox composer = new HBox(12);
        composer.getStyleClass().add("composer");
        composer.setAlignment(Pos.BOTTOM_RIGHT);
        composer.setPadding(new Insets(12, 12, 12, 18));

        input.setPromptText("Schreib eine Nachricht ...");
        input.setWrapText(true);
        input.setPrefRowCount(2);
        input.setMaxHeight(100);
        input.getStyleClass().add("message-input");
        HBox.setHgrow(input, Priority.ALWAYS);
        input.setOnKeyPressed(event -> {
            if (event.getCode() == KeyCode.ENTER && !event.isShiftDown()) {
                event.consume();
                sendMessage();
            }
        });

        sendButton.getStyleClass().add("send-button");
        sendButton.setOnAction(event -> sendMessage());
        composer.getChildren().addAll(input, sendButton);

        Label hint = new Label("Enter zum Senden  ·  Shift + Enter für eine neue Zeile");
        hint.getStyleClass().add("composer-hint");
        wrapper.getChildren().addAll(composer, hint);
        VBox.setMargin(hint, new Insets(8, 0, 0, 4));
        return wrapper;
    }

    private void startNewChat() {
        sessionId = UUID.randomUUID().toString();
        messages.getChildren().clear();
        addAssistantMessage("Neuer Chat gestartet. Was möchtest du wissen?");
        connectionStatus.setText("BEREIT");
    }

    private void sendMessage() {
        String message = input.getText().trim();
        if (message.isEmpty() || sendButton.isDisabled()) {
            return;
        }

        input.clear();
        addUserMessage(message);
        pendingMessage = addAssistantMessage("Denke nach ...");
        setBusy(true);
        String requestSession = sessionId;

        Task<String> request = new Task<String>() {
            @Override
            protected String call() throws IOException {
                return ChatClient.send(message, requestSession);
            }
        };
        request.setOnSucceeded(event -> {
            removePendingMessage();
            addAssistantMessage(request.getValue());
            connectionStatus.setText("VERBUNDEN");
            setBusy(false);
        });
        request.setOnFailed(event -> {
            removePendingMessage();
            Throwable error = request.getException();
            String details = error == null ? "Unbekannter Fehler" : error.getMessage();
            addErrorMessage("Der Server ist nicht erreichbar. Starte zuerst start-server.bat."
                    + (details == null || details.trim().isEmpty() ? "" : "\n" + details));
            connectionStatus.setText("OFFLINE");
            setBusy(false);
        });
        requests.execute(request);
    }

    private void setBusy(boolean busy) {
        sendButton.setDisable(busy);
        input.setDisable(busy);
        newChatButton.setDisable(busy);
        sendButton.setText(busy ? "..." : "Senden  ➤");
    }

    private Label addAssistantMessage(String text) {
        return addMessage(text, false, false);
    }

    private void addUserMessage(String text) {
        addMessage(text, true, false);
    }

    private void addErrorMessage(String text) {
        addMessage(text, false, true);
    }

    private Label addMessage(String text, boolean fromUser, boolean isError) {
        Label bubble = new Label(text);
        bubble.setWrapText(true);
        bubble.setMaxWidth(620);
        bubble.getStyleClass().add("message-bubble");
        bubble.getStyleClass().add(fromUser ? "user-bubble" : "assistant-bubble");
        if (isError) {
            bubble.getStyleClass().add("error-bubble");
        }

        HBox row = new HBox(bubble);
        row.setAlignment(fromUser ? Pos.CENTER_RIGHT : Pos.CENTER_LEFT);
        row.getStyleClass().add("message-row");
        messages.getChildren().add(row);
        scrollToBottom();
        return bubble;
    }

    private void removePendingMessage() {
        if (pendingMessage != null && pendingMessage.getParent() != null) {
            messages.getChildren().remove(pendingMessage.getParent());
        }
        pendingMessage = null;
    }

    private void scrollToBottom() {
        javafx.application.Platform.runLater(() -> chatScroll.setVvalue(1.0));
    }

    @Override
    public void stop() {
        requests.shutdownNow();
    }

    public static void main(String[] args) {
        launch(args);
    }
}
