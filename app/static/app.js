const sessionId = `web-${Math.random().toString(16).slice(2)}`;
const messages = document.querySelector("#messages");
const plan = document.querySelector("#plan");
const tools = document.querySelector("#tools");
const memory = document.querySelector("#memory");
const status = document.querySelector("#status");
const form = document.querySelector("#chat-form");
const input = document.querySelector("#message");

function addMessage(role, text) {
  const article = document.createElement("article");
  article.className = `message ${role}`;
  article.textContent = text;
  messages.append(article);
  messages.scrollTop = messages.scrollHeight;
}

function renderList(target, items, formatter) {
  target.replaceChildren();
  for (const item of items) {
    const li = document.createElement("li");
    li.textContent = formatter(item);
    target.append(li);
  }
}

async function send(message) {
  addMessage("user", message);
  input.value = "";
  const response = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id: sessionId }),
  });
  const data = await response.json();
  addMessage("agent", data.response);
  renderList(plan, data.plan || [], (item) => item.step);
  renderList(tools, data.tools_used || [], (item) => item);
  renderList(memory, data.short_term_memory || [], (item) => `${item.kind}: ${item.content}`);
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const message = input.value.trim();
  if (message) send(message);
});

document.querySelectorAll("[data-message]").forEach((button) => {
  button.addEventListener("click", () => send(button.dataset.message));
});

fetch("/health")
  .then((response) => response.json())
  .then((data) => {
    status.textContent = `Activo (${data.tools.length} herramientas)`;
    status.classList.add("ok");
  })
  .catch(() => {
    status.textContent = "Sin conexion";
  });

addMessage("agent", "Hola. Estoy listo para consultar stock, registrar salidas con OT, revisar alertas o redactar reportes operativos.");
