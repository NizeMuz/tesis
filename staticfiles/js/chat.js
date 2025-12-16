class ServiuChat {
    constructor() {
        this.isOpen = false;
        this.messages = [];
        this.init();
    }

    init() {
        this.createChatWidget();
        this.bindEvents();
        this.addWelcomeMessage();
    }

    createChatWidget() {
        const chatHTML = `
            <div class="chat-widget" id="chatWidget">
                <button class="chat-toggle" id="chatToggle">
                    💬
                </button>
                <div class="chat-container" id="chatContainer">
                    <div class="chat-header">
                        <h4>Asistente Serviu</h4>
                        <button class="chat-close" id="chatClose">×</button>
                    </div>
                    <div class="chat-messages" id="chatMessages">
                        <!-- Los mensajes se cargarán aquí -->
                    </div>
                    <div class="typing-indicator" id="typingIndicator">
                        <div class="typing-dots">
                            <div class="typing-dot"></div>
                            <div class="typing-dot"></div>
                            <div class="typing-dot"></div>
                        </div>
                    </div>
                    <div class="chat-input-container">
                        <form class="chat-input-form" id="chatForm">
                            <textarea 
                                class="chat-input" 
                                id="chatInput" 
                                placeholder="Escribe tu pregunta sobre Serviu..."
                                rows="1"
                            ></textarea>
                            <button type="submit" class="chat-send" id="chatSend">
                                ➤
                            </button>
                        </form>
                    </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', chatHTML);
    }

    bindEvents() {
        const chatToggle = document.getElementById('chatToggle');
        const chatClose = document.getElementById('chatClose');
        const chatForm = document.getElementById('chatForm');
        const chatInput = document.getElementById('chatInput');

        chatToggle.addEventListener('click', () => this.toggleChat());
        chatClose.addEventListener('click', () => this.closeChat());
        chatForm.addEventListener('submit', (e) => this.handleSubmit(e));
        
        // Auto-resize textarea
        chatInput.addEventListener('input', () => {
            chatInput.style.height = 'auto';
            chatInput.style.height = Math.min(chatInput.scrollHeight, 80) + 'px';
        });

        // Enter para enviar, Shift+Enter para nueva línea
        chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.handleSubmit(e);
            }
        });
    }

    toggleChat() {
        const container = document.getElementById('chatContainer');
        const toggle = document.getElementById('chatToggle');
        
        if (this.isOpen) {
            this.closeChat();
        } else {
            container.style.display = 'flex';
            toggle.innerHTML = '×';
            this.isOpen = true;
            
            // Focus en el input
            setTimeout(() => {
                document.getElementById('chatInput').focus();
            }, 100);
        }
    }

    closeChat() {
        const container = document.getElementById('chatContainer');
        const toggle = document.getElementById('chatToggle');
        
        container.style.display = 'none';
        toggle.innerHTML = '💬';
        this.isOpen = false;
    }

    async handleSubmit(e) {
        e.preventDefault();
        
        const input = document.getElementById('chatInput');
        const message = input.value.trim();
        
        if (!message) return;
        
        // Limpiar input
        input.value = '';
        input.style.height = 'auto';
        
        // Agregar mensaje del usuario
        this.addMessage(message, 'user');
        
        // Mostrar indicador de escritura
        this.showTyping();
        
        try {
            // Enviar mensaje al backend
            const response = await this.sendMessage(message);
            
            // Ocultar indicador de escritura
            this.hideTyping();
            
            // Agregar respuesta del bot - CORREGIDO: usar response.response en lugar de response.message
            if (response.status === 'success') {
                this.addMessage(response.response, 'bot');
            } else {
                this.addMessage(response.error || 'Error desconocido', 'bot');
            }
            
        } catch (error) {
            console.error('Error al enviar mensaje:', error);
            this.hideTyping();
            this.addMessage('Lo siento, ha ocurrido un error. Por favor, intenta nuevamente.', 'bot');
        }
    }

    async sendMessage(message) {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
                         document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
        
        const response = await fetch('/chat/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken,
            },
            body: JSON.stringify({ message: message })
        });
        
        if (!response.ok) {
            throw new Error('Error en la respuesta del servidor');
        }
        
        return await response.json();
    }

    addMessage(content, sender) {
        const messagesContainer = document.getElementById('chatMessages');
        const messageElement = document.createElement('div');
        messageElement.className = `message ${sender}`;
        
        if (sender === 'bot') {
            messageElement.innerHTML = `
                <div class="message-avatar">S</div>
                <div class="message-content">${this.formatMessage(content)}</div>
            `;
        } else {
            messageElement.innerHTML = `
                <div class="message-content">${this.formatMessage(content)}</div>
            `;
        }
        
        messagesContainer.appendChild(messageElement);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        
        this.messages.push({ content, sender, timestamp: new Date() });
    }

    formatMessage(message) {
        // Convertir URLs en enlaces
        const urlRegex = /(https?:\/\/[^\s]+)/g;
        message = message.replace(urlRegex, '<a href="$1" target="_blank" rel="noopener">$1</a>');
        
        // Convertir saltos de línea
        message = message.replace(/\n/g, '<br>');
        
        return message;
    }

    showTyping() {
        const typingIndicator = document.getElementById('typingIndicator');
        const messagesContainer = document.getElementById('chatMessages');
        
        typingIndicator.style.display = 'block';
        messagesContainer.appendChild(typingIndicator);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    hideTyping() {
        const typingIndicator = document.getElementById('typingIndicator');
        typingIndicator.style.display = 'none';
    }

    addWelcomeMessage() {
        setTimeout(() => {
            this.addMessage(
                '¡Hola! Soy el asistente virtual de Serviu Región de Ñuble. Puedo ayudarte con información sobre beneficiarios, programas habitacionales, requisitos y más. ¿En qué puedo ayudarte?',
                'bot'
            );
        }, 1000);
    }
}

// Inicializar el chat cuando se carga la página
document.addEventListener('DOMContentLoaded', () => {
    new ServiuChat();
});


// Agregar función para consulta por RUT
function consultarPorRUT() {
    const rut = document.getElementById('rut-input').value;
    const mensaje = document.getElementById('chat-input').value;
    
    if (!rut) {
        alert('Por favor ingresa un RUT');
        return;
    }
    
    fetch('/chat/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({
            message: mensaje,
            rut: rut
        })
    })
    .then(response => response.json())
    .then(data => {
        // Mostrar respuesta con datos del beneficiario
        displayResponse(data.response, data.beneficiario_data);
    })
    .catch(error => {
        console.error('Error:', error);
    });
}