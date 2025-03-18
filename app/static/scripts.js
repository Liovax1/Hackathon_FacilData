const chatWindow = document.getElementById("chat-window");
const chatForm = document.getElementById("chat-form");
const userInput = document.getElementById("user-input");

function addMessage(content, sender) {
    const messageEl = document.createElement("div");
    messageEl.classList.add("message", sender);
    
    const contentEl = document.createElement("div");
    contentEl.classList.add("content");
    contentEl.textContent = content;
    
    messageEl.appendChild(contentEl);
    chatWindow.appendChild(messageEl);
    chatWindow.scrollTop = chatWindow.scrollHeight;
}

chatForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const userText = userInput.value.trim();
    if (!userText) return;

    addMessage(userText, "user");
    userInput.value = "";

    try {
        const response = await axios.post("/ask", { question: userText });
        addMessage(response.data.response, "bot");
    } catch (error) {
        addMessage("Une erreur est survenue. Réessayez.", "bot");
        console.error(error);
    }
});
