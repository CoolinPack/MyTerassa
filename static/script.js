let tg = window.Telegram.WebApp;
tg.expand();

let user = tg.initDataUnsafe?.user || { id: 12345678, first_name: "Арсен", username: "arsen_user" };
let cart = {};
let dishes = [];
let currentCategory = "Все";
let appliedDiscount = 0.05; // Скидка по умолчанию

document.addEventListener("DOMContentLoaded", () => {
    loadMenu();
    loadProfile();
});

function switchTab(tabId) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    
    if (tabId === 'home') {
        document.getElementById('page-home').classList.add('active');
        document.querySelectorAll('.nav-item')[0].classList.add('active');
    } else if (tabId === 'menu') {
        document.getElementById('page-menu').classList.add('active');
        document.querySelectorAll('.nav-item')[1].classList.add('active');
    } else if (tabId === 'cart') {
        document.getElementById('page-cart').classList.add('active');
        document.querySelectorAll('.nav-item')[2].classList.add('active');
        renderCart();
    } else if (tabId === 'profile') {
        document.getElementById('page-profile').classList.add('active');
        document.querySelectorAll('.nav-item')[3].classList.add('active');
        loadOrdersHistory();
    }
}

async function loadMenu() {
    // В реальной развертке запросы идут к бэкенду, здесь имитируем загрузку из БД
    dishes = [
        { id: 1, name: "Тартар из тунца с авокадо", category: "Салаты", price: 160000, composition: "Тунец, авокадо, соус унаги", is_stop: 0, is_popular: 1 },
        { id: 2, name: "Цезарь с креветками", category: "Салаты", price: 150000, composition: "Креветки, айсберг, пармезан", is_stop: 0, is_popular: 1 },
        { id: 3, name: "Лосось на гриле", category: "Горячее", price: 150000, composition: "Филе лосося, травы", is_stop: 0, is_popular: 1 },
        { id: 4, name: "Цезарь с курицей", category: "Салаты", price: 130000, composition: "Куриное филе, соус цезарь", is_stop: 0, is_popular: 0 },
    ];
    renderDishes();
    renderPopular();
}

function renderPopular() {
    const container = document.getElementById('popular-dishes');
    container.innerHTML = dishes.filter(d => d.is_popular).map(d => `
        <div class="dish-card">
            <div class="dish-info">
                <h4>${d.name}</h4>
                <div class="dish-price">${d.price.toLocaleString()} VND</div>
            </div>
            <div>→</div>
        </div>
    `).join('');
}

function renderDishes() {
    const container = document.getElementById('menu-dishes');
    const searchQuery = document.getElementById('search-input').value.toLowerCase();
    
    let filtered = dishes.filter(d => {
        let matchesCategory = (currentCategory === "Все" || d.category === currentCategory);
        let matchesSearch = d.name.toLowerCase().includes(searchQuery);
        return matchesCategory && matchesSearch;
    });

    container.innerHTML = filtered.map(d => {
        let qty = cart[d.id] || 0;
        if (d.is_stop) {
            return `
                <div class="dish-card" style="opacity: 0.6;">
                    <div class="dish-info">
                        <div class="dish-category">${d.category}</div>
                        <h4>${d.name}</h4>
                        <div style="color: red; font-weight: bold; font-size: 13px;">В стоп-листе</div>
                    </div>
                    <div class="dish-price">${d.price.toLocaleString()} VND</div>
                </div>`;
        }
        return `
            <div class="dish-card">
                <div class="dish-info">
                    <div class="dish-category">${d.category}</div>
                    <h4>${d.name}</h4>
                    <div class="dish-price">${d.price.toLocaleString()} VND</div>
                </div>
                <div class="dish-controls">
                    <button onclick="changeQty(${d.id}, -1)">-</button>
                    <span>${qty}</span>
                    <button onclick="changeQty(${d.id}, 1)">+</button>
                </div>
            </div>`;
    }).join('');
}

function changeQty(dishId, delta) {
    if (!cart[dishId]) cart[dishId] = 0;
    cart[dishId] += delta;
    if (cart[dishId] < 0) cart[dishId] = 0;
    if (cart[dishId] === 0) delete cart[dishId];
    renderDishes();
}

function filterMenu() {
    renderDishes();
}

function toggleCategoryDropdown() {
    const dropdown = document.getElementById('category-dropdown');
    dropdown.style.display = dropdown.style.display === 'block' ? 'none' : 'block';
}

function selectCategory(cat) {
    currentCategory = cat;
    document.getElementById('selected-category-name').innerText = cat === 'Все' ? 'Все категории' : cat;
    document.getElementById('category-dropdown').style.display = 'none';
    renderDishes();
}

function renderCart() {
    const container = document.getElementById('cart-content');
    const checkoutSec = document.getElementById('cart-checkout-section');
    
    const itemIds = Object.keys(cart);
    if (itemIds.length === 0) {
        container.innerHTML = '<p class="empty-cart">Ваша корзина пуста</p>';
        checkoutSec.style.display = 'none';
        return;
    }
    
    checkoutSec.style.display = 'block';
    let subtotal = 0;
    
    container.innerHTML = itemIds.map(id => {
        let dish = dishes.find(d => d.id == id);
        let qty = cart[id];
        subtotal += dish.price * qty;
        return `
            <div class="dish-card">
                <div class="dish-info">
                    <h4>${dish.name} × ${qty}</h4>
                    <div class="dish-price">${(dish.price * qty).toLocaleString()} VND</div>
                </div>
            </div>`;
    }).join('');
    
    let discount = subtotal * appliedDiscount;
    let final = subtotal - discount;
    
    document.getElementById('subtotal-price').innerText = subtotal.toLocaleString();
    document.getElementById('discount-price').innerText = discount.toLocaleString();
    document.getElementById('final-price').innerText = final.toLocaleString();
}

function applyPromo() {
    let promo = document.getElementById('promo-input').value.trim();
    if (promo === 'TERASSA5') {
        appliedDiscount = 0.05;
        alert('Промокод успешно применен! Скидка 5%');
        renderCart();
    } else {
        alert('Неверный промокод');
    }
}

function makeOrder(type) {
    let itemsDesc = Object.keys(cart).map(id => {
        let dish = dishes.find(d => d.id == id);
        return `${dish.name} x ${cart[id]}`;
    }).join(', ');
    
    let subtotal = 0;
    Object.keys(cart).forEach(id => {
        let dish = dishes.find(d => d.id == id);
        subtotal += dish.price * cart[id];
    });
    let final = subtotal - (subtotal * appliedDiscount);
    
    if (type === 'Доставка') {
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(position => {
                let lat = position.coords.latitude;
                let lon = position.coords.longitude;
                sendOrderToServer(itemsDesc, final, `Доставка (Широта: ${lat}, Долгота: ${lon} (GPS))`);
            }, () => {
                alert('Не удалось получить геопозицию. Заказ оформлен как самовывоз.');
                sendOrderToServer(itemsDesc, final, 'Самовывоз');
            });
        } else {
            sendOrderToServer(itemsDesc, final, 'Самовывоз');
        }
    } else {
        sendOrderToServer(itemsDesc, final, 'Самовывоз');
    }
}

function sendOrderToServer(items, total, type) {
    alert(`Заказ успешно оформлен!\nСумма: ${total.toLocaleString()} VND\nТип: ${type}`);
    cart = {};
    switchTab('home');
}

function loadProfile() {
    document.getElementById('p-name').innerText = user.first_name || "Арсен";
    document.getElementById('profile-name').innerText = user.first_name || "Арсен";
    document.getElementById('p-birth').innerText = "30.09.2002";
    document.getElementById('p-gender').innerText = "Мужской";
}

function loadOrdersHistory() {
    const container = document.getElementById('orders-history');
    // Отображаем историю заказов без плашки «Новый»
    container.innerHTML = `
        <div class="history-card">
            <div class="history-top">
                <span>Заказ #4</span>
                <span>1 790 000 VND</span>
            </div>
            <div style="font-size: 13px; color: #8c7355; margin-bottom: 6px;">19.08.2026, 06:07:36</div>
            <div style="font-size: 14px;"><b>Состав:</b> Цезарь с курицей × 3, Тартар из тунца с авокадо × 5, Цезарь с креветками × 4</div>
            <div style="font-size: 13px; color: #666; margin-top: 4px;">Тип: Доставка (Широта: 12.280430, Долгота: 109.201220 (GPS))</div>
        </div>`;
}
