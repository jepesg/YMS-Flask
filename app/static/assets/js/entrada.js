/**
 * Alterna dinamicamente as validações e campos visíveis na portaria
 * dependendo da escolha entre Veículo Logístico ou Pedestre/Visitante.
 * @param {string} tipo - 'caminhao' ou 'visitante'
 */
function alternarCamposEntrada(tipo) {
    const secaoCaminhao = document.getElementById('campos-caminhao');
    const labelNome = document.getElementById('label-nome');
    
    const placa = document.getElementById('placa');
    const modelo = document.getElementById('modelo');
    const transportadora = document.getElementById('transportadora');
    
    if (!secaoCaminhao || !labelNome) return;

    if (tipo === 'visitante') {
        // Esconde campos pesados e limpa obrigatoriedades
        secaoCaminhao.style.display = 'none';
        labelNome.innerText = "Nome do Visitante:";
        
        if (placa) placa.removeAttribute('required');
        if (modelo) modelo.removeAttribute('required');
        if (transportadora) transportadora.removeAttribute('required');
    } else {
        // Exibe campos e força o preenchimento regulatório de frotas
        secaoCaminhao.style.display = 'block';
        labelNome.innerText = "Nome do Motorista:";
        
        if (placa) placa.setAttribute('required', '');
        if (modelo) modelo.setAttribute('required', '');
        if (transportadora) transportadora.setAttribute('required', '');
    }
}

function alternarCampos(tipo) {
    const secao = document.getElementById('secao-veiculo');
    const inputs = secao.querySelectorAll('input');
    if (tipo === 'visitante') {
        secao.style.display = 'none';
        inputs.forEach(input => input.removeAttribute('required'));
    } else {
        secao.style.display = 'block';
    }
}

document.addEventListener("DOMContentLoaded", function () {
    const video = document.getElementById('webcam');
    const photoPreview = document.getElementById('photo-preview');
    const canvas = document.getElementById('canvas');
    const btnCapture = document.getElementById('btn-capture');
    const btnRetry = document.getElementById('btn-retry');
    const inputBase64 = document.getElementById('foto_base64');

    let stream = null;

    // 1. Liga a Webcam automaticamente ao abrir a página
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 } })
            .then(function (mediaStream) {
                stream = mediaStream;
                video.srcObject = mediaStream;
                video.play();
            })
            .catch(function (error) {
                console.error("Erro ao acessar a webcam: ", error);
                alert("Não foi possível acessar a câmera do dispositivo.");
            });
    }

    // 2. Evento de Capturar a Foto (Bater o Print)
    btnCapture.addEventListener('click', function () {
        const context = canvas.getContext('2d');
        canvas.width = video.videoWidth || 640;
        canvas.height = video.videoHeight || 480;
        
        // Desenha a imagem atual do vídeo dentro do canvas oculto
        context.drawImage(video, 0, 0, canvas.width, canvas.height);
        
        // Transforma o desenho do canvas em uma String Base64 do tipo PNG
        const dataUrl = canvas.toDataURL('image/png');
        
        // Salva essa string no input hidden para ir pro backend
        inputBase64.value = dataUrl;

        // Troca o vídeo ao vivo pelo preview estático da imagem
        video.style.display = 'none';
        photoPreview.src = dataUrl;
        photoPreview.style.display = 'block';

        // Ajusta a visibilidade dos botões
        btnCapture.style.display = 'none';
        btnRetry.style.display = 'inline-block';
    });

    // 3. Evento de Descartar a Foto e tentar novamente
    btnRetry.addEventListener('click', function () {
        // Limpa o input do formulário
        inputBase64.value = '';

        // Mostra o vídeo de volta e oculta o preview
        photoPreview.style.display = 'none';
        video.style.display = 'block';

        // Ajusta os botões
        btnRetry.style.display = 'none';
        btnCapture.style.display = 'inline-block';
    });
});