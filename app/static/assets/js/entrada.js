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