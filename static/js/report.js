function loadReport() {
  const filter = document.getElementById('filter').value;

  fetch(`/api/report_data?filter=${filter}`)
    .then(res => res.json())
    .then(data => {
      const container = document.getElementById('report-container');
      container.innerHTML = `
        <h2>📦 Total Orders: ${data.total_orders}</h2>
        <h2>💷 Total Revenue: £${data.total_revenue}</h2>
        <h2>📊 Avg Order Value: £${data.avg_order}</h2>
        <h2>🥢 Combos Sold: ${data.combo_count}</h2>
        <h2>🍋 Lemonade Upgrades: ${data.lemonade_upgrades}</h2>
        <div>

        </div>
      `;

      const orderList = document.getElementById('order-list');
      orderList.innerHTML = (data.orders || []).map(o => {
        const amount = parseFloat(o.total_price);  // Ensure it's numeric

        let colorClass = '';
        if (amount === 13.5) colorClass = 'order-green';
        else if (amount <= 9.5) colorClass = 'order-yellow';
        else colorClass = 'order-orange';

        const details = (o.items || []).map(i =>
          `<div>${i.item} – £${i.price.toFixed(2)}</div>`
        ).join('');

        return `
          <li class="${colorClass}" onclick="this.classList.toggle('order-expanded')">
            Order #${o.display_order_number} – £${amount.toFixed(2)}
            <div class="order-details">
              ${details || '<em>No breakdown available</em>'}
            </div>
          </li>
        `;
      }).join('');





      renderOrdersByHourChart(data.orders_by_hour);
      renderComboChart(data.total_orders, data.combo_count);
      renderLemonadeChart(data.combo_count, data.lemonade_upgrades);
      renderTopItemsChart(data.most_popular);
    });


}

function renderOrdersByHourChart(hourData) {
  const ctx = document.getElementById('ordersByHourChart').getContext('2d');
  if (window.ordersChart instanceof Chart) {
  window.ordersChart.destroy();
}


  const labels = Object.keys(hourData).sort();
  const values = labels.map(hour => hourData[hour]);

  window.ordersChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: 'Orders per Hour',
        data: values,
        backgroundColor: 'rgba(54, 162, 235, 0.6)'
      }]
    },
    options: {
      scales: {
        y: { beginAtZero: true }
      }
    }
  });
}

function renderComboChart(totalOrders, comboCount) {
  const ctx = document.getElementById('comboBreakdownChart').getContext('2d');
  if (window.comboChart instanceof Chart) {
  window.comboChart.destroy();
}


  window.comboChart = new Chart(ctx, {
    type: 'pie',
    data: {
      labels: ['Standard Orders', 'Combo Orders'],
      datasets: [{
        data: [totalOrders - comboCount, comboCount],
        backgroundColor: ['#FFCD56', '#36A2EB']
      }]
    }
  });
}

function renderLemonadeChart(comboCount, lemonadeUpgrades) {
  const ctx = document.getElementById('lemonadeChart').getContext('2d');
  if (window.lemonadeChart instanceof Chart) {
    window.lemonadeChart.destroy();
  }

  window.lemonadeChart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['Regular Combos', 'Lemonade Upgrades'],
      datasets: [{
        data: [
          comboCount - lemonadeUpgrades,  // combos without lemonade
          lemonadeUpgrades                // combos with lemonade
        ],
        backgroundColor: ['#FF6384', '#4BC0C0']
      }]
    }
  });
}

function renderTopItemsChart(items) {
  const ctx = document.getElementById('topItemsChart').getContext('2d');
  if (window.itemsChart instanceof Chart) {
  window.itemsChart.destroy();
}


  const labels = items.map(i => i[0]);
  const counts = items.map(i => i[1]);

  window.itemsChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: 'Top Items Sold',
        data: counts,
        backgroundColor: 'rgba(255, 99, 132, 0.6)'
      }]
    },
    options: {
      indexAxis: 'y',
      scales: {
        x: { beginAtZero: true }
      }
    }
  });
}

function toggleOrders() {
  const section = document.getElementById('order-history');
  const btn = document.querySelector('button[onclick=\"toggleOrders()\"]');
  const isVisible = section.style.display === 'block';

  section.style.display = isVisible ? 'none' : 'block';
  btn.textContent = isVisible ? '📋 Show Past Orders' : '📋 Hide Past Orders';
}


loadReport();

function exportReport() {
  const filter = document.getElementById('filter').value;
  window.open(`/export_report?filter=${filter}`, '_blank');
}

function exportPDF() {
  const filter = document.getElementById('filter').value;
  window.open(`/export_pdf?filter=${filter}`, '_blank');
}
