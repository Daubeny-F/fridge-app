'use strict';
const $ = (s, root = document) => root.querySelector(s);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const icon = (name, extra = '') => `<svg class="icon ${extra}" aria-hidden="true"><use href="#i-${name}"/></svg>`;
const categories = {vegetables:'Vegetables',fruit:'Fruit',dairy:'Dairy & eggs',protein:'Meat & protein',grains:'Grains & pasta',pantry:'Pantry'};
const names = {overview:'Overview',fridge:'My fridge',recipes:'Recipe ideas',favorites:'Saved recipes',shopping:'Shopping list',reminders:'Expiry reminders',settings:'Settings'};
const foodEmoji = name => {
  const n = name.toLowerCase();
  const foods = [['tomato','🍅'],['spinach','🥬'],['lettuce','🥬'],['egg','🥚'],['milk','🥛'],['yogurt','🥛'],['cheese','🧀'],['feta','🧀'],['chicken','🍗'],['salmon','🐟'],['tuna','🐟'],['rice','🍚'],['pasta','🍝'],['bread','🍞'],['avocado','🥑'],['carrot','🥕'],['broccoli','🥦'],['pepper','🫑'],['lemon','🍋'],['banana','🍌'],['apple','🍎'],['potato','🥔'],['onion','🧅'],['garlic','🧄'],['cucumber','🥒'],['mushroom','🍄'],['oat','🌾'],['lentil','🫘'],['chickpea','🫘'],['olive','🫒']];
  return foods.find(([key]) => n.includes(key))?.[1] || '🌿';
};
const food = name => `<span class="food-icon" aria-hidden="true">${foodEmoji(name)}</span>`;
let data, page = 'overview', filter = 'all', query = '', sort = 'expiry', toastTimer;
const main = $('#main');
const modal = $('#modal');
const csrf = () => document.cookie.split('; ').find(c => c.startsWith('csrftoken='))?.split('=')[1] || $('input[name=csrfmiddlewaretoken]').value;

async function api(url, method = 'GET', body) {
  const options = {method, credentials:'same-origin', headers:{'Accept':'application/json'}};
  if (method !== 'GET') {
    options.headers['X-CSRFToken'] = csrf();
    options.headers['Content-Type'] = 'application/json';
    options.body = JSON.stringify(body || {});
  }
  let response;
  try { response = await fetch(url, options); }
  catch { throw new Error('Could not reach your kitchen. Check that the server is running.'); }
  if (response.status === 401) { location.href = '/login/'; throw new Error('Your session ended. Please sign in.'); }
  const contentType = response.headers.get('content-type') || '';
  const result = contentType.includes('application/json') ? await response.json() : {};
  if (!response.ok) {
    if (response.status === 403) throw new Error('Your security token expired. Refresh the page and try again.');
    throw new Error(result.error || Object.entries(result.errors || {}).map(([k,v]) => `${k.replaceAll('_',' ')}: ${v.join(' ')}`).join('\n') || 'Something went wrong. Please try again.');
  }
  return result;
}
function toast(message, error = false) {
  const element = $('#toast');
  element.textContent = message;
  element.className = `toast show${error ? ' error' : ''}`;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => element.classList.remove('show'), 4500);
}
const alerts = () => data.ingredients.filter(i => i.days_left <= data.settings.reminder_days);
const soon = () => data.ingredients.filter(i => i.days_left >= 0 && i.days_left <= data.settings.reminder_days);
const dateLabel = date => new Date(`${date}T12:00:00`).toLocaleDateString('en-GB',{day:'numeric',month:'short'});
function expiry(item) {
  if (item.days_left < 0) return `<span class="status expired">Expired ${Math.abs(item.days_left)}d ago</span>`;
  if (item.days_left === 0) return '<span class="status soon">Expires today</span>';
  return `<span class="status ${item.days_left <= data.settings.reminder_days ? 'soon' : ''}">${item.days_left <= data.settings.reminder_days ? `${item.days_left} ${item.days_left===1?'day':'days'} left` : `Fresh · ${item.days_left}d`}</span>`;
}
function empty(title, text, symbol, button = '') { return `<div class="empty">${icon(symbol)}<h3>${esc(title)}</h3><p>${esc(text)}</p>${button}</div>`; }
const addButton = () => `<button class="btn primary" data-action="add">${icon('plus')}Add ingredient</button>`;
const heading = (title, text, action = '') => `<div class="page-heading"><div><h1>${esc(title)}</h1><p>${esc(text)}</p></div>${action}</div>`;

function updateChrome() {
  const initials = data.user.name.trim().split(/\s+/).map(n => n[0]).slice(0,2).join('').toUpperCase();
  $('#avatar').textContent = initials;
  $('#top-avatar').textContent = initials;
  $('#sidebar-name').textContent = data.user.name;
  $('#fridge-count').textContent = data.ingredients.length;
  $('#alert-count').textContent = alerts().length;
  $('#alert-count').hidden = alerts().length === 0;
  $('#notification-dot').hidden = alerts().length === 0;
  $('#today').textContent = new Date(`${data.today}T12:00:00`).toLocaleDateString('en-GB',{weekday:'short',day:'numeric',month:'long'});
}
async function refresh(redraw = true) {
  data = await api('/api/state/');
  updateChrome();
  if (redraw) render();
}
function navigate(next) {
  if (!names[next]) return;
  page = next; filter = 'all'; query = ''; sort = 'expiry';
  history.replaceState(null, '', `#${page}`);
  $('#sidebar').classList.remove('open');
  render();
  window.scrollTo({top:0, behavior:'instant'});
}
function render() {
  $('#breadcrumb').textContent = names[page];
  document.title = `${names[page]} · Fridgewise`;
  document.querySelectorAll('.nav-item[data-page]').forEach(el => { el.classList.toggle('active', el.dataset.page === page); if(el.dataset.page === page) el.setAttribute('aria-current','page'); else el.removeAttribute('aria-current'); });
  const renderers = {overview:overviewPage,fridge:fridgePage,recipes:recipesPage,favorites:recipesPage,shopping:shoppingPage,reminders:remindersPage,settings:settingsPage};
  main.innerHTML = renderers[page]();
  if (['recipes','favorites'].includes(page)) updateRecipes();
  if (page === 'fridge') updateInventory();
}
function stats() {
  const items = [
    ['fridge','In your fridge',data.ingredients.length,'ingredients on hand'],
    ['clock','Use soon',soon().length,`within ${data.settings.reminder_days} days`],
    ['chef','Ready to cook',data.recipes.filter(r=>r.ready).length,'ideas from your fridge'],
    ['heart','Saved for later',data.recipes.filter(r=>r.favorite).length,'favorite recipes'],
  ];
  return `<div class="stats">${items.map(([symbol,label,value,note])=>`<div class="stat"><span class="stat-icon">${icon(symbol)}</span><div><label>${label}</label><strong>${value}</strong><small>${note}</small></div></div>`).join('')}</div>`;
}
function miniInventory() {
  if (!data.ingredients.length) return empty('A fresh canvas','Add your first ingredient and let’s see what’s cooking.','fridge',addButton());
  return `<table class="mini-inventory"><thead><tr><th>INGREDIENT</th><th>QUANTITY</th><th>FRESHNESS</th></tr></thead><tbody>${data.ingredients.slice(0,4).map(i=>`<tr><td><div class="mini-name">${food(i.name)}${esc(i.name)}</div></td><td>${esc(i.quantity)} ${esc(i.unit)}</td><td>${expiry(i)}</td></tr>`).join('')}</tbody></table>`;
}
function overviewPage() {
  const firstName = data.user.name.split(' ')[0];
  return heading(`A fresh day, ${firstName}.`, 'A little inspiration for what’s already in your fridge.', addButton()) +
    `<section class="hero"><div class="hero-copy"><span class="eyebrow">YOUR INGREDIENTS. ENDLESS POSSIBILITIES.</span><h2>Good food starts<br>with <em>what you have.</em></h2><p>A handful of ingredients. A dash of inspiration.<br>Let’s turn your fridge into something delicious.</p><button class="btn primary" data-page="recipes">Find my next meal ${icon('arrow')}</button></div><img src="/static/art/hero.svg" alt="Fresh vegetables arranged around a handmade ceramic plate"><span class="hero-stamp">FRESH THINKING, EVERY DAY</span></section>` + stats() +
    `<div class="overview-split"><section class="panel"><div class="section-heading"><h2>A peek inside your fridge <span class="tiny-count">${data.ingredients.length}</span></h2><button class="text-btn" data-page="fridge">View all ${icon('arrow')}</button></div>${miniInventory()}</section><section class="panel expiry-panel"><h3>${icon('clock')}A little heads-up</h3><p>Good ingredients deserve to be used.</p>${alerts().slice(0,3).map(i=>`<div class="expiry-item">${food(i.name)}<div><strong>${esc(i.name)}</strong><small>${i.days_left < 0 ? 'Expired · remove from fridge' : i.days_left === 0 ? 'Best used today' : `Use in the next ${i.days_left} ${i.days_left===1?'day':'days'}`}</small></div><button class="icon-btn" data-action="edit" data-id="${i.id}" aria-label="Edit ${esc(i.name)}">${icon('arrow')}</button></div>`).join('') || `<p class="hint">Everything is looking fresh. We’ll keep an eye on your dates.</p>`}<button class="text-btn" data-page="reminders">See all reminders ${icon('arrow')}</button></section></div>
    <section><div class="section-heading"><div><h2>A little fridge-to-table inspiration</h2><p class="section-kicker">Picked for what you have. Made for what you’re craving.</p></div><button class="text-btn" data-page="recipes">Explore recipes ${icon('arrow')}</button></div><div class="recipe-grid">${data.recipes.slice(0,3).map(recipeCard).join('') || empty('Recipes are on their way','An administrator can add recipes to the collection.','chef')}</div></section>`;
}
function recipeCard(r) {
  return `<article class="recipe-card"><div class="recipe-art"><button class="recipe-art-link" data-action="recipe" data-id="${r.id}" aria-label="View ${esc(r.title)}"><img src="/static/art/${esc(r.art)}.svg" alt="Illustration of ${esc(r.title)}" loading="lazy"></button><span class="recipe-tag">${icon(r.use_soon.length ? 'leaf' : 'chef')}${r.use_soon.length ? 'USES YOUR USE-SOON INGREDIENTS' : r.category === 'protein' ? 'HIGH PROTEIN' : r.category.toUpperCase()}</span><button class="save-btn ${r.favorite?'saved':''}" data-action="favorite" data-id="${r.id}" aria-label="${r.favorite?'Unsave':'Save'} ${esc(r.title)}" aria-pressed="${r.favorite}">${icon('heart')}</button></div><div class="recipe-body"><div class="recipe-meta"><span>${icon('clock')}${r.minutes} min</span><span>${icon('users')}${r.servings} servings</span><span>${r.category==='protein'?'High protein':r.category[0].toUpperCase()+r.category.slice(1)}</span></div><button class="recipe-title" data-action="recipe" data-id="${r.id}">${esc(r.title)}</button><p class="recipe-description">${esc(r.description)}</p><div class="recipe-match"><span>${icon(r.ready?'check':'fridge')}${r.ready?'You have everything!':`${r.matched} of ${r.total} ingredients`}</span><button class="text-btn" data-action="recipe" data-id="${r.id}">Let’s cook ${icon('arrow')}</button></div></div></article>`;
}
function fridgePage() {
  return heading('Your fridge, at a glance.','Keep track of the good things you have on hand.',`<div>${addButton()}</div>`) +
    `<div class="toolbar"><label class="search-box">${icon('search')}<input type="search" id="inventory-search" placeholder="Find an ingredient…" value="${esc(query)}" aria-label="Search ingredients"></label><div class="recipe-filter-row">${['all','vegetables','fruit','dairy','protein','grains','pantry'].map(c=>`<button class="chip ${filter===c?'active':''}" data-filter="${c}" aria-pressed="${filter===c}">${c==='all'?'Everything':categories[c]}</button>`).join('')}</div><select id="inventory-sort" aria-label="Sort inventory"><option value="expiry">Expiry date</option><option value="name" ${sort==='name'?'selected':''}>Name A–Z</option><option value="category" ${sort==='category'?'selected':''}>Category</option></select></div><div id="inventory-results"></div><div class="section-heading" style="margin-top:18px"><span class="hint">Dates are reminders. Always check food condition before cooking.</span><a class="text-btn" href="/api/export/">${icon('download')}Export CSV</a></div>`;
}
function updateInventory() {
  let items = data.ingredients.filter(i=>(filter==='all'||i.category===filter)&&i.name.toLowerCase().includes(query.toLowerCase()));
  items = [...items].sort((a,b)=>sort==='name'?a.name.localeCompare(b.name):sort==='category'?a.category.localeCompare(b.category):a.days_left-b.days_left);
  const root = $('#inventory-results'); if (!root) return;
  root.innerHTML = items.length ? `<div class="table-wrap"><table class="inventory-table"><thead><tr><th>Ingredient</th><th>Category</th><th>Amount</th><th>Expires</th><th>Freshness</th><th><span class="sr-only">Actions</span></th></tr></thead><tbody>${items.map(i=>`<tr><td><div class="mini-name">${food(i.name)}${esc(i.name)}</div></td><td><span class="badge-neutral">${categories[i.category]}</span></td><td>${esc(i.quantity)} ${esc(i.unit)}</td><td>${dateLabel(i.expires_on)}</td><td>${expiry(i)}</td><td><div class="table-actions"><button class="icon-btn" data-action="edit" data-id="${i.id}" aria-label="Edit ${esc(i.name)}">${icon('edit')}</button><button class="icon-btn" data-action="delete" data-id="${i.id}" aria-label="Remove ${esc(i.name)}">${icon('trash')}</button></div></td></tr>`).join('')}</tbody></table></div>` : empty(data.ingredients.length?'Nothing matches just yet.':'Let’s stock your fridge.',data.ingredients.length?'Try another search or category.':'Add ingredients and their expiry dates to find your next meal.','fridge',data.ingredients.length?'':addButton());
}
function recipesPage() {
  const saved = page==='favorites';
  return heading(saved?'Good ideas, saved.':'What’s cooking? ',saved?'Your favorite recipes, ready when you are.':'Recipe ideas inspired by the ingredients you already have.',`<span class="badge-neutral">${data.recipes.filter(r=>r.ready).length} ready to cook</span>`) +
  `<div class="toolbar"><div class="recipe-filter-row">${[['all','All ideas'],['ready','Ready to cook'],['soon','Use soon'],['vegetarian','Vegetarian'],['vegan','Vegan'],['quick','Under 20 min']].map(([key,label])=>`<button class="chip ${filter===key?'active':''}" data-filter="${key}" aria-pressed="${filter===key}">${label}</button>`).join('')}</div><label class="search-box">${icon('search')}<input type="search" id="recipe-search" placeholder="Find a recipe or ingredient…" aria-label="Search recipes" value="${esc(query)}"></label></div><p class="hint">Matched by ingredient names; check the recipe for amounts. Keep salt, pepper, water, and cooking oil on hand.</p><div class="recipe-grid" id="recipe-results"></div>`;
}
function updateRecipes() {
  const root = $('#recipe-results'); if (!root) return;
  const recipes = data.recipes.filter(r=>
    (page!=='favorites'||r.favorite) && (filter!=='ready'||r.ready) && (filter!=='soon'||r.use_soon.length) &&
    (filter!=='vegetarian'||['vegetarian','vegan'].includes(r.category)) && (filter!=='vegan'||r.category==='vegan') &&
    (filter!=='quick'||r.minutes<20) && `${r.title} ${r.ingredients.map(i=>i.name).join(' ')}`.toLowerCase().includes(query.toLowerCase()));
  root.innerHTML = recipes.length ? recipes.map(recipeCard).join('') : empty(page==='favorites'?'Your favorites start here.':'No recipes match this combination.',page==='favorites'?'Tap the heart on a recipe to keep it for later.':'Try another filter or add more ingredients to your fridge.','chef',`<button class="btn" data-page="${page==='favorites'?'recipes':'fridge'}">${page==='favorites'?'Explore recipe ideas':'Open my fridge'} ${icon('arrow')}</button>`);
}
function remindersPage() {
  return heading('A little nudge, less waste.',`Your ingredients expiring within ${data.settings.reminder_days} days, plus anything past its date.`,`<button class="btn" data-page="settings">${icon('settings')}Reminder settings</button>`) +
    `<div class="info-banner">${icon('bell')}<p>${data.settings.email_reminders?'Email reminders are allowed. An administrator can send a reminder manually when ingredients are due.':'Your in-app reminders are on. Allow email reminders in Settings if you also want an administrator to email you.'}</p></div>` +
    (alerts().length ? `<div class="alert-list">${alerts().map(i=>`<article class="alert-card">${food(i.name)}<div><h3>${esc(i.name)}</h3><p>${esc(i.quantity)} ${esc(i.unit)} · ${dateLabel(i.expires_on)}</p></div>${expiry(i)}<button class="btn" data-action="${i.days_left<0?'delete':'use-recipes'}" data-id="${i.id}">${i.days_left<0?'Remove ingredient':'Find a recipe'} ${icon(i.days_left<0?'trash':'arrow')}</button></article>`).join('')}</div>` : empty('Everything’s looking fresh.','We’ll give you a heads-up when something needs a little attention.','leaf',`<button class="btn" data-page="fridge">Take a look inside ${icon('arrow')}</button>`));
}
function shoppingPage() {
  const unchecked = data.shopping.filter(i=>!i.checked).length;
  return heading('Just the missing pieces.','A little list for your next trip to the store.',`<span class="badge-neutral">${unchecked} to pick up</span>`) +
    `<section class="panel shopping-panel"><form class="inline-form" id="shopping-form"><label class="sr-only" for="shopping-name">Ingredient name</label><input id="shopping-name" name="name" placeholder="Add something to your list…" required maxlength="80"><button type="submit" class="btn primary">${icon('plus')}Add</button></form>${data.shopping.length ? data.shopping.map(i=>`<div class="shopping-row ${i.checked?'done':''}"><input type="checkbox" id="shop-${i.id}" data-shop-id="${i.id}" ${i.checked?'checked':''}><label for="shop-${i.id}">${esc(i.name)}</label><button class="icon-btn" data-action="remove-shopping" data-id="${i.id}" aria-label="Remove ${esc(i.name)}">${icon('trash')}</button></div>`).join('') : empty('Your list is lovely and clear.','Add ingredients here, or open a recipe and add its missing ingredients.','basket')}<p class="hint" style="margin:20px 0 0">Picked something up? Add it to My fridge with its expiry date.</p></section>`;
}
function settingsPage() {
  return heading('Make yourself at home.','A few preferences for your everyday kitchen.') +
    `<div class="settings-grid"><section class="panel"><h3>Stay one step ahead</h3><p>Choose when your ingredients should get your attention.</p><form id="settings-form"><div class="field"><label for="reminder-days">Remind me before ingredients expire</label><select id="reminder-days" name="reminder_days">${Array.from({length:14},(_,i)=>i+1).map(n=>`<option value="${n}" ${n===data.settings.reminder_days?'selected':''}>${n} ${n===1?'day':'days'} before</option>`).join('')}</select></div><div class="check-row"><input type="checkbox" id="email-reminders" name="email_reminders" ${data.settings.email_reminders?'checked':''}><label for="email-reminders">Allow expiry reminder emails<small>Sent manually by an administrator, at most once per day, to ${esc(data.user.email||'your account email')}.</small></label></div><p class="hint">Email reminders are manual. An administrator reviews your due ingredients and clicks Send; nothing is sent automatically. Local preview mode saves a file instead of sending an email.</p><div class="form-errors" id="settings-errors" role="alert"></div><button class="btn primary" type="submit">Save preferences ${icon('check')}</button></form></section><section class="panel"><h3>Your corner of the kitchen</h3><p>Account details and your ingredient data.</p><div class="account-row"><span>Name</span><strong>${esc(data.user.name)}</strong></div><div class="account-row"><span>Username</span><strong>${esc(data.user.username)}</strong></div><div class="account-row"><span>Email</span><strong>${esc(data.user.email||'Not set')}</strong></div><div class="account-row"><span>Access</span><strong>${data.user.is_staff?'Administrator':'Home cook'}</strong></div><a class="btn" style="margin-top:24px" href="/api/export/">${icon('download')}Export my fridge</a><p class="hint" style="margin-top:16px">Your fridge and shopping list belong to your account. An administrator can manage all records.</p></section></div>`;
}
function openModal(content) {
  $('#modal-content').innerHTML = content;
  modal.showModal();
  modal.scrollTop = 0;
}
const modalHeader = title => `<div class="modal-head"><h2 id="modal-title">${esc(title)}</h2><button class="icon-btn" data-action="close-modal" aria-label="Close dialog">${icon('x')}</button></div>`;
function ingredientModal(id) {
  const item = id ? data.ingredients.find(i=>i.id===Number(id)) : null;
  const defaultExpiry = new Date(`${data.today}T12:00:00`); defaultExpiry.setDate(defaultExpiry.getDate()+7);
  const dateString = [defaultExpiry.getFullYear(),String(defaultExpiry.getMonth()+1).padStart(2,'0'),String(defaultExpiry.getDate()).padStart(2,'0')].join('-');
  openModal(modalHeader(item?'A little fridge update.':'Something fresh?') + `<div class="modal-body"><p class="modal-description">${item?'Update the details for this ingredient.':'Add an ingredient and we’ll help you make the most of it.'}</p><form id="ingredient-form" data-id="${item?.id||''}"><div class="field"><label for="ingredient-name">Ingredient name</label><input id="ingredient-name" name="name" placeholder="e.g. tomatoes, spinach, eggs" required maxlength="80" value="${esc(item?.name||'')}" autofocus></div><div class="field"><label for="ingredient-category">Category</label><select id="ingredient-category" name="category">${Object.entries(categories).map(([key,label])=>`<option value="${key}" ${item?.category===key?'selected':''}>${label}</option>`).join('')}</select></div><div class="field-row"><div class="field"><label for="ingredient-quantity">Amount</label><input id="ingredient-quantity" type="number" name="quantity" min="0.01" max="9999999.99" step="0.01" required value="${esc(item?.quantity||'1')}"></div><div class="field"><label for="ingredient-unit">Unit</label><select id="ingredient-unit" name="unit">${['g','kg','ml','l','pcs','pack'].map(u=>`<option value="${u}" ${item?.unit===u||!item&&u==='pcs'?'selected':''}>${u}</option>`).join('')}</select></div></div><div class="field"><label for="ingredient-expiry">Expiry date</label><input id="ingredient-expiry" type="date" name="expires_on" required value="${esc(item?.expires_on||dateString)}"><small>We’ll remind you ${data.settings.reminder_days} days before this date.</small></div><div class="form-errors" id="ingredient-errors" role="alert"></div><div class="modal-actions"><button class="btn" type="button" data-action="close-modal">Cancel</button><button class="btn primary" type="submit">${icon('check')}${item?'Save changes':'Add to my fridge'}</button></div></form></div>`);
}
function recipeModal(id) {
  const r = data.recipes.find(r=>r.id===Number(id)); if (!r) return;
  openModal(`<img class="recipe-dialog-art" src="/static/art/${esc(r.art)}.svg" alt="Illustration of ${esc(r.title)}">` + modalHeader(r.title) + `<div class="modal-body"><p class="modal-description">${esc(r.description)}</p><div class="detail-badges"><span>${icon('clock','small')} ${r.minutes} minutes</span><span>${r.servings} servings</span><span>${r.matched}/${r.total} ingredients on hand</span></div>${r.use_soon.length?`<div class="info-banner">${icon('leaf')}Uses your ${r.use_soon.map(esc).join(', ')} before ${r.use_soon.length>1?'they expire':'it expires'}.</div>`:''}<section class="detail-section"><h3>What you’ll need</h3>${r.ingredients.map(i=>`<div class="detail-ingredient ${i.available?'':'missing'}">${icon(i.available?'check':'plus')}<span>${esc(i.name)}</span><span>${esc(i.amount)} ${i.available?'· in your fridge':'· to pick up'}</span></div>`).join('')}<p class="hint" style="margin-top:12px">Salt, pepper, water, and cooking oil as needed. Check your quantities before starting.</p>${r.missing.length?`<button class="btn" data-action="missing" data-id="${r.id}">${icon('basket')}Add ${r.missing.length} missing ingredients to my list</button>`:''}</section><section class="detail-section"><h3>Let’s make it</h3><ol>${r.instructions.map(s=>`<li>${esc(s)}</li>`).join('')}</ol></section><div class="modal-actions"><button class="btn ${r.favorite?'':'primary'}" data-action="favorite-modal" data-id="${r.id}">${icon('heart')}${r.favorite?'Saved to your recipes':'Save this recipe'}</button></div></div>`);
}
function deleteModal(id) {
  const i = data.ingredients.find(i=>i.id===Number(id)); if (!i) return;
  openModal(modalHeader('Make a little room?') + `<div class="modal-body"><p class="modal-description">Remove <strong>${esc(i.name)}</strong> from your fridge? Your recipe suggestions will update too.</p><div class="modal-actions"><button class="btn" data-action="close-modal">Keep it</button><button class="btn danger" data-action="confirm-delete" data-id="${i.id}">${icon('trash')}Remove ingredient</button></div></div>`);
}
document.addEventListener('click', async event => {
  const nav = event.target.closest('[data-page]');
  if (nav && data) { navigate(nav.dataset.page); return; }
  const chip = event.target.closest('[data-filter]');
  if (chip) {
    filter = chip.dataset.filter;
    document.querySelectorAll('[data-filter]').forEach(el=>{el.classList.toggle('active',el.dataset.filter===filter);el.setAttribute('aria-pressed',String(el.dataset.filter===filter));});
    if(page==='fridge') updateInventory(); else updateRecipes(); return;
  }
  const button = event.target.closest('[data-action]'); if (!button || !data) return;
  const id = Number(button.dataset.id), action = button.dataset.action;
  if (button.disabled) return;
  try {
    switch(action) {
      case 'add': ingredientModal(); break;
      case 'edit': ingredientModal(id); break;
      case 'delete': deleteModal(id); break;
      case 'close-modal': modal.close(); break;
      case 'recipe': recipeModal(id); break;
      case 'favorite':
      case 'favorite-modal': {
        button.disabled = true;
        const result = await api(`/api/recipes/${id}/favorite/`,'POST');
        await refresh();
        if(action==='favorite-modal') { modal.close(); recipeModal(id); }
        toast(result.favorite?'Saved. A good idea for later.':'Recipe removed from saved.'); break;
      }
      case 'confirm-delete':
        button.disabled = true;
        await api(`/api/ingredients/${id}/`,'DELETE'); modal.close(); await refresh(); toast('Ingredient removed. Your fridge is up to date.'); break;
      case 'missing': {
        button.disabled = true;
        const recipe = data.recipes.find(r=>r.id===id);
        await api('/api/shopping/','POST',{names:recipe.missing});
        await refresh(); toast('Missing ingredients added to your shopping list.'); button.textContent='Added to your list ✓'; break;
      }
      case 'remove-shopping':
        button.disabled=true;
        await api(`/api/shopping/${id}/`,'DELETE'); await refresh(); toast('Removed from your list.'); break;
      case 'use-recipes': {
        navigate('recipes'); filter='soon'; render(); break;
      }
    }
  } catch(error) {button.disabled=false; toast(error.message,true);}
});
document.addEventListener('input', event => {
  if (event.target.id==='inventory-search') {query=event.target.value;updateInventory();}
  if (event.target.id==='recipe-search') {query=event.target.value;updateRecipes();}
});
document.addEventListener('change', async event => {
  if (event.target.id==='inventory-sort') {sort=event.target.value;updateInventory();}
  if (event.target.dataset.shopId) {
    const el = event.target; el.disabled=true;
    try {await api(`/api/shopping/${el.dataset.shopId}/`,'PUT',{checked:el.checked}); await refresh();}
    catch(error) {el.checked=!el.checked;el.disabled=false;toast(error.message,true);}
  }
});
document.addEventListener('submit', async event => {
  const form = event.target;
  if (!['ingredient-form','settings-form','shopping-form'].includes(form.id)) return;
  event.preventDefault();
  const button = $('button[type=submit]',form); button.disabled = true;
  try {
    if (form.id==='ingredient-form') {
      const payload=Object.fromEntries(new FormData(form));
      const id=form.dataset.id;
      await api(id?`/api/ingredients/${id}/`:'/api/ingredients/',id?'PUT':'POST',payload);
      modal.close(); await refresh(); toast(id?'Fresh details, saved.':'Added. Your next meal is getting closer.');
    } else if(form.id==='settings-form') {
      await api('/api/settings/','PUT',{reminder_days:$('#reminder-days').value,email_reminders:$('#email-reminders').checked});
      await refresh(); toast('Your preferences are saved.');
    } else {
      await api('/api/shopping/','POST',{names:[new FormData(form).get('name')]});
      await refresh(); $('#shopping-name')?.focus(); toast('Added to your list.');
    }
  } catch(error) {
    const errors=$('.form-errors',form);
    if(errors) errors.textContent=error.message; else toast(error.message,true);
  } finally {button.disabled=false;}
});
$('#mobile-toggle').addEventListener('click',()=>$('#sidebar').classList.toggle('open'));
document.addEventListener('click',e=>{if(!e.target.closest('#sidebar')&&!e.target.closest('#mobile-toggle')) $('#sidebar').classList.remove('open');});
modal.addEventListener('click', event=>{if(event.target===modal){const r=modal.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)modal.close();}});
page = names[location.hash.slice(1)] ? location.hash.slice(1) : 'overview';
refresh().catch(error=>{main.innerHTML=empty('Your kitchen is taking a moment.',error.message,'alert','<button class="btn primary" id="retry-load">Try again</button>');$('#retry-load').addEventListener('click',()=>location.reload());});
setInterval(async()=>{
  if(!data || document.hidden) return;
  const previous = alerts().length;
  try {
    await refresh(false);
    if(alerts().length>previous) toast('A little heads-up: check your expiry reminders.');
    if(['overview','reminders'].includes(page) && !modal.open) render();
  } catch { /* Keep the current view on temporary connection loss. */ }
},60000);
