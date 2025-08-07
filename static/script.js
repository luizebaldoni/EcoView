// Removido o código do gráfico, pois deve ser inicializado no dashboard.html

function updateDashboard() {
    fetch('/api/latest/')
        .then(response => response.json())
        .then(data => {
            document.getElementById('temp-value').innerText = data.sensor1 + ' °C';
            document.getElementById('temp-time').innerText = 'Última atualização: ' + data.timestamp;
            document.getElementById('hum-value').innerText = data.sensor2 + ' %';
            document.getElementById('hum-time').innerText = 'Última atualização: ' + data.timestamp;
            document.getElementById('bat-value').innerText = data.battery + ' %';
            document.getElementById('bat-time').innerText = 'Última atualização: ' + data.timestamp;
        })
        .catch(error => {
            // Em caso de erro, não atualiza os valores
        });
}
setInterval(updateDashboard, 5000);
window.onload = updateDashboard;
