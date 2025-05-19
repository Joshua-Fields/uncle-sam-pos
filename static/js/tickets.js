function fetchTickets() {
  fetch('/get_tickets')
    .then(res => res.json())
    .then(tickets => {
      const container = document.getElementById('ticket-container');
      container.innerHTML = '';
      tickets.forEach(ticket => {
        const div = document.createElement('div');
        div.className = 'ticket';
        const timeCreated = new Date(ticket.timestamp);
        const elapsed = Math.floor((Date.now() - timeCreated.getTime()) / 1000);

        div.style.background = getColor(elapsed);

        let shortOrderNumber = ticket.display_order_number
          ? ticket.display_order_number.split('-')[1]
          : ticket.id;

        div.innerHTML = `
          <h3>Order #${shortOrderNumber}</h3>
          <ul>${ticket.items.map(i => `<li>${i.item} - £${i.price.toFixed(2)}</li>`).join('')}</ul>
          <p><strong>Elapsed:</strong> <span class="timer" data-start="${ticket.timestamp}">${elapsed}s</span></p>
          <button onclick="clearTicket(${ticket.id})">Clear</button>
        `;

        container.appendChild(div);
      });
    });
}

function renderTickets(tickets) {
  const container = document.getElementById('ticket-container');
  container.innerHTML = '';

  tickets.forEach(ticket => {
    const el = document.createElement('div');
    el.className = 'ticket';

  let shortOrderNumber = ticket.display_order_number
    ? ticket.display_order_number.split('-')[1]
    : ticket.id;

  el.innerHTML = `
    <h3>Order #${shortOrderNumber}</h3>
    <ul>${ticket.items.map(i => `<li>${i.item} – £${i.price.toFixed(2)}</li>`).join('')}</ul>
    <p>🕒 ${new Date(ticket.timestamp).toLocaleTimeString()}</p>
    <button onclick="clearTicket(${ticket.id})">Mark as Done</button>
  `;


    container.appendChild(el);
  });
}


function getColor(seconds) {
  if (seconds < 120) return '#d4fcd4';      // Green < 2 min
  if (seconds < 300) return '#fffac8';      // Yellow < 5 min
  return '#ffd1d1';                         // Red > 5 min
}

function clearTicket(id) {
  fetch(`/clear_ticket/${id}`, { method: 'DELETE' })
    .then(() => fetchTickets());
}

setInterval(fetchTickets, 5000);  // Refresh every 5s
fetchTickets();
