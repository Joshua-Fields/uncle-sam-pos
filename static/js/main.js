let order = [];
let total = 0;

let currentBase = null;
let currentStyle = null;
let currentStylePrice = 0;

function setBase(base) {
  currentBase = base;
  document.getElementById('status').textContent = `Base selected: ${base}`;

  if (navigator.vibrate) {
    navigator.vibrate(30); // 30ms light vibration
  }

}

function setStyle(style, price) {
  if (!currentBase) {
    alert("Please select a base first.");
    return;
  }
  currentStyle = style;
  currentStylePrice = price;
  const fullName = `${currentBase} Corndog - ${style} Style`;
  order.push({ item: fullName, price: price });
  total += price;
  currentBase = null;
  currentStyle = null;
  updateOrderList();

  if (navigator.vibrate) {
    navigator.vibrate(30); // 30ms light vibration
  }

}

function addExtra(name, price) {
  order.push({ item: name, price: price });
  total += price;
  updateOrderList();

  if (navigator.vibrate) {
    navigator.vibrate(30); // 30ms light vibration
  }

}

function addCombo(withLemonade) {
  const comboPrice = withLemonade ? 13.5 : 11.5;
  const comboName = withLemonade
    ? "Combo: Corndog + Fries + Lemonade"
    : "Combo: Corndog + Fries + Drink";
  order.push({ item: comboName, price: comboPrice });
  total += comboPrice;
  updateOrderList();

  if (navigator.vibrate) {
    navigator.vibrate(30); // 30ms light vibration
  }
}

function updateOrderList() {
  const list = document.getElementById('order-list');
  list.innerHTML = '';
  order.forEach(({ item, price }, index) => {
    const li = document.createElement('li');
    li.innerHTML = `${item} - £${price.toFixed(2)} <button onclick="removeItem(${index})">✖️</button>`;
    list.appendChild(li);
  });
  document.getElementById('total').textContent = total.toFixed(2);
  if (navigator.vibrate) {
    navigator.vibrate(30); // 30ms light vibration
  }

}

function removeItem(index) {
  total -= order[index].price;
  order.splice(index, 1);
  updateOrderList();

  if (navigator.vibrate) {
    navigator.vibrate(30); // 30ms light vibration
  }
}

function clearOrder() {
  order = [];
  total = 0;
  updateOrderList();
  document.getElementById('status').textContent = 'Order cleared.';

  if (navigator.vibrate) {
    navigator.vibrate(30); // 30ms light vibration
  }
}

function finishOrder() {
  if (order.length === 0) return;

  const hasCombo = order.some(i => i.item.includes("Combo"));
  const hasLemonadeUpgrade = order.some(i => i.item.includes("Lemonade")) && hasCombo;
  const orderType = hasCombo ? (hasLemonadeUpgrade ? "combo+lemonade" : "combo") : "standard";
  const location = document.getElementById('locationSelect').value;

  fetch('/save_full_order', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      location,
      items: order,
      total_price: total,
      combo: hasCombo,
      lemonade_upgrade: hasLemonadeUpgrade,
      order_type: orderType
    })
  }).then(res => res.json())
    .then(() => {
      document.getElementById('status').textContent = 'Order saved!';
      clearOrder();
    });
  if (navigator.vibrate) {
    navigator.vibrate(30); // 30ms light vibration
  }

}
