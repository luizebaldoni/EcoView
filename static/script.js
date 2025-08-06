const ctx = document.getElementById('sensorChart').getContext('2d');
const chart = new Chart(ctx, {
    type: 'line',
    data: {
        labels: JSON.parse('{{ timestamps|safe }}'),
        datasets: [{
            label: 'Sensor 1',
            data: JSON.parse('{{ sensor_data.sensor1|safe }}'),
            borderColor: 'rgb(75, 192, 192)',
            tension: 0.1
        }]
    },
    options: {
        responsive: true,
        scales: {
            y: {
                beginAtZero: false
            }
        }
    }
});
