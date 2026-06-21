function abrirModalExportar() {
    document.getElementById('modalExportar').style.display = 'flex';
}

function fecharModalExportar() {
    document.getElementById('modalExportar').style.display = 'none';
}

function validarPeriodoExportacao() {
    const dataInicioInput = document.getElementById('export_data_inicio').value;
    const dataFimInput = document.getElementById('export_data_fim').value;
    
    if (!dataInicioInput || !dataFimInput) {
        alert("Por favor, preencha ambos os campos de data.");
        return false;
    }

    const inicio = new Date(dataInicioInput);
    const fim = new Date(dataFimInput);
    
    if (inicio > fim) {
        alert("Erro de consistência: A data inicial não pode ser maior do que a data final!");
        return false;
    }
    
    const diferencaTempo = Math.abs(fim - inicio);
    const diferencaDias = Math.ceil(diferencaTempo / (1000 * 60 * 60 * 24));
    
    if (diferencaDias > 365) {
        alert(`Período bloqueado! O intervalo selecionado compreende ${diferencaDias} dias. O limite máximo do sistema SaaS para relatórios é de 365 dias (1 ano).`);
        return false;
    }
    
    fecharModalExportar();
    return true;
}