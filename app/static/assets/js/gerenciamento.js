document.addEventListener("DOMContentLoaded", function () {
    const dataContainer = document.getElementById('charts-data');
    if (!dataContainer) return;

    const labelStatus = JSON.parse(dataContainer.getAttribute('data-status-labels'));
    const valoresStatus = JSON.parse(dataContainer.getAttribute('data-status-valores'));
    const labelsDocas = JSON.parse(dataContainer.getAttribute('data-docas-labels'));
    const mediaTempoDoca = JSON.parse(dataContainer.getAttribute('data-docas-tempos'));

    // Função para mapear dinamicamente a cor certa para o status correspondente
    const coresMapeadas = labelStatus.map(status => {
        const s = status.toLowerCase().trim();
        if (s.includes('concluido') || s.includes('concluído')) return '#28a745'; // Verde
        if (s.includes('patio') || s.includes('pátio')) return '#fd7e14';       // Laranja
        if (s.includes('doca')) return '#17a2b8';                                // Azul Claro
        return '#6c757d'; // Cor padrão caso surja outro status (Cinza)
    });

    // --- Gráfico de Status (Doughnut/Pizza) ---
    const ctxStatus = document.getElementById('chartStatus');
    if (ctxStatus) {
        new Chart(ctxStatus.getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: labelStatus,
                datasets: [{
                    data: valoresStatus,
                    backgroundColor: coresMapeadas // Aplica as cores dinâmicas e corretas
                }]
            },
            options: { 
                responsive: true,
                maintainAspectRatio: true
            }
        });
    }

    // --- Gráfico de Tempo de Doca (Barras) ---
    const ctxTempo = document.getElementById('chartTempoDoca');
    if (ctxTempo) {
        new Chart(ctxTempo.getContext('2d'), {
            type: 'bar',
            data: {
                labels: labelsDocas,
                datasets: [{
                    label: 'Média em Minutos',
                    data: mediaTempoDoca,
                    backgroundColor: '#1e242b',
                    borderRadius: 5
                }]
            },
            options: {
                responsive: true,
                scales: { y: { beginAtZero: true } }
            }
        });
    }
});