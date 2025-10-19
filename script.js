// script.js - Integração Frontend com Backend Python

document.addEventListener('DOMContentLoaded', function() {
    const perguntaInput = document.getElementById('pergunta-usuario');
    const botaoPerguntar = document.querySelector('button[type="submit"]');
    const respostaDiv = document.getElementById('resposta');
    
    // URL do seu backend Python
    const BACKEND_URL = 'http://127.0.0.1:5000/perguntar';
    
    // Função para fazer a pergunta ao backend
    async function fazerPergunta(pergunta) {
        try {
            // Mostrar que está carregando
            respostaDiv.innerHTML = `
                <div class="loading">
                    <p>🤖 Processando sua pergunta...</p>
                </div>
            `;
            
            // Fazer requisição para o backend
            const response = await fetch(BACKEND_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    pergunta: pergunta
                })
            });
            
            // Verificar se a resposta foi bem-sucedida
            if (!response.ok) {
                throw new Error(`Erro HTTP: ${response.status}`);
            }
            
            // Converter resposta para JSON
            const dados = await response.json();
            
            // Exibir a resposta
            exibirResposta(dados);
            
        } catch (error) {
            console.error('Erro ao fazer pergunta:', error);
            respostaDiv.innerHTML = `
                <div class="error">
                    <p>❌ <strong>Erro:</strong> Não foi possível processar sua pergunta.</p>
                    <p><small>Verifique se o backend Python está rodando em http://127.0.0.1:5000/</small></p>
                    <p><small>Erro técnico: ${error.message}</small></p>
                </div>
            `;
        }
    }
    
    // Função para exibir a resposta formatada
     function exibirResposta(dados) {
        let html = '';

        if (dados.resposta) {
            // *** A MÁGICA ACONTECE AQUI ***
            // Pega a resposta do backend e substitui todas as quebras de linha (\n)
            // pela tag de quebra de linha do HTML (<br>).
            const respostaFormatada = dados.resposta.replace(/\n/g, '<br>');

            html = `<p class="resposta-p">${respostaFormatada}</p>`;
        }
        
        respostaDiv.innerHTML = html;
    }
    
    // Event listener para o botão
    botaoPerguntar.addEventListener('click', function(e) {
        e.preventDefault();
        
        const pergunta = perguntaInput.value.trim();
        
        if (!pergunta) {
            respostaDiv.innerHTML = `
                <div class="error">
                    <p>⚠️ Por favor, digite uma pergunta antes de enviar.</p>
                </div>
            `;
            return;
        }
        
        fazerPergunta(pergunta);
    });
    
    // Event listener para Enter no textarea
    perguntaInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            botaoPerguntar.click();
        }
    });
    
    // Limpar resposta quando começar a digitar nova pergunta
    perguntaInput.addEventListener('input', function() {
        if (respostaDiv.innerHTML && perguntaInput.value.trim() === '') {
            respostaDiv.innerHTML = '';
        }
    });
});

// Função para testar se o backend está funcionando
async function testarBackend() {
    try {
        const response = await fetch('http://127.0.0.1:5000/perguntar', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                pergunta: 'teste'
            })
        });
        
        if (response.ok) {
            console.log('✅ Backend está funcionando!');
            return true;
        } else {
            console.log('❌ Backend não está respondendo corretamente');
            return false;
        }
    } catch (error) {
        console.log('❌ Erro ao conectar com backend:', error.message);
        return false;
    }
}

// Testar backend quando a página carregar
window.addEventListener('load', () => {
    testarBackend();
})