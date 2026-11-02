function alternarCampos(tipo) {
    const secao = document.getElementById('secao-veiculo');
    const titulo = document.getElementById('titulo-secao-veiculo');
    const descricao = document.getElementById('descricao-secao-veiculo');
    if (!secao) return;

    secao.style.display = 'block';
    const visitante = tipo === 'visitante';
    if (titulo) titulo.textContent = visitante ? 'Veículo do visitante (opcional)' : 'Dados do veículo';
    if (descricao) descricao.hidden = !visitante;
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
