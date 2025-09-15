function toggleShabbatTimes() {
  const content = document.getElementById('shabbat-content');
  const toggle = document.getElementById('shabbat-toggle');
  
  if (content.style.display === 'none' || !content.style.display) {
    content.style.display = 'block';
    toggle.textContent = '▼';
  } else {
    content.style.display = 'none';
    toggle.textContent = '▶';
  }
}

function toggleZmanim() {
  const content = document.getElementById('zmanim-content');
  const toggle = document.getElementById('zmanim-toggle');
  
  if (content.style.display === 'none' || !content.style.display) {
    content.style.display = 'block';
    toggle.textContent = '▼';
  } else {
    content.style.display = 'none';
    toggle.textContent = '▶';
  }
}

function toggleShabbatInfo() {
  const content = document.getElementById('shabbat-info-content');
  const toggle = document.getElementById('shabbat-info-toggle');
  
  if (content.style.display === 'none' || !content.style.display) {
    content.style.display = 'block';
    toggle.textContent = '▼';
  } else {
    content.style.display = 'none';
    toggle.textContent = '▶';
  }
}

function showCalendar() {
  const calendarView = document.getElementById('calendar-view');
  const zmanimView = document.getElementById('zmanim-view');
  const calendarToggle = document.getElementById('calendar-toggle');
  const zmanimToggle = document.getElementById('zmanim-toggle-btn');
  
  calendarView.style.display = 'flex';
  zmanimView.style.display = 'none';
  calendarToggle.classList.add('active');
  zmanimToggle.classList.remove('active');
}

function showZmanim() {
  const calendarView = document.getElementById('calendar-view');
  const zmanimView = document.getElementById('zmanim-view');
  const calendarToggle = document.getElementById('calendar-toggle');
  const zmanimToggle = document.getElementById('zmanim-toggle-btn');
  
  calendarView.style.display = 'none';
  zmanimView.style.display = 'flex';
  calendarToggle.classList.remove('active');
  zmanimToggle.classList.add('active');
}

function initDashboardToggle() {
  const toggleBtns = document.querySelectorAll('.dash-toggle-btn');
  const body = document.body;
  
  function switchDashboard(dashNumber) {
    body.className = body.className.replace(/dash-\d+/g, '');
    body.classList.add(`dash-${dashNumber}`);
    
    toggleBtns.forEach(btn => {
      btn.classList.toggle('active', btn.dataset.dash === dashNumber.toString());
    });
    
    localStorage.setItem('selectedDash', dashNumber);
  }
  
  toggleBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const dashNumber = parseInt(btn.dataset.dash);
      switchDashboard(dashNumber);
    });
  });
  
  const savedDash = localStorage.getItem('selectedDash') || '1';
  switchDashboard(parseInt(savedDash));
}

async function fetchJSON(url) {
  try {
    const r = await fetch(url);
    if (!r.ok) throw new Error(r.statusText);
    return await r.json();
  } catch (e) {
    return null;
  }
}

// OAuth credential management functions
async function updateCredentials(clientId, clientSecret, projectId = '', saveToConfig = true) {
  try {
    const response = await fetch('/api/credentials', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        client_id: clientId,
        client_secret: clientSecret,
        project_id: projectId,
        save_to_config: saveToConfig
      })
    });
    
    const result = await response.json();
    if (response.ok) {
      console.log('Credentials updated:', result.message);
      return true;
    } else {
      console.error('Error updating credentials:', result.error);
      return false;
    }
  } catch (e) {
    console.error('Network error updating credentials:', e);
    return false;
  }
}

async function clearCredentials() {
  try {
    const response = await fetch('/api/credentials', {
      method: 'DELETE'
    });
    
    const result = await response.json();
    if (response.ok) {
      console.log('Credentials cleared:', result.message);
      return true;
    } else {
      console.error('Error clearing credentials:', result.error);
      return false;
    }
  } catch (e) {
    console.error('Network error clearing credentials:', e);
    return false;
  }
}

async function getCredentialStatus() {
  const data = await fetchJSON('/api/credentials');
  return data;
}

function relativeTime(isoOrRfc) {
  try {
    const d = new Date(isoOrRfc);
    const now = new Date();
    const diff = Math.max(0, (now - d) / 1000);
    const mins = Math.floor(diff / 60);
    if (mins < 1) return 'now';
    if (mins < 60) return `${mins}m`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h`;
    const days = Math.floor(hrs / 24);
    return `${days}d`;
  } catch (_) {
    return '';
  }
}

async function refreshTime() {
  const data = await fetchJSON('/api/time');
  if (!data) return;
  document.getElementById('time-local').textContent = data.local;
  document.getElementById('time-utc').textContent = data.utc;
  
  // Format combined date: MON, 15, SEP | 22, ELUL, 5785
  const combinedDateEl = document.getElementById('combined-date');
  if (combinedDateEl && data.date && data.hebrew) {
    // Parse English date (e.g., "Mon, 15 Sep")
    const englishParts = data.date.split(', ');
    const dayOfWeek = englishParts[0]?.toUpperCase() || '';
    const dayMonth = englishParts[1] || '';
    const [day, month] = dayMonth.split(' ');
    const monthUpper = month?.toUpperCase() || '';
    
    // Parse Hebrew date (e.g., "22 Elul 5785")
    const hebrewParts = data.hebrew.split(' ');
    const hebrewDay = hebrewParts[0] || '';
    const hebrewMonth = hebrewParts[1]?.toUpperCase() || '';
    const hebrewYear = hebrewParts[2] || '';
    
    const combinedDate = `${dayOfWeek}, ${day}, ${monthUpper} | ${hebrewDay}, ${hebrewMonth}, ${hebrewYear}`;
    combinedDateEl.textContent = combinedDate;
  }
  
  // Update day-of-week indicator
  updateWeekIndicator();
}

function updateWeekIndicator() {
  const now = new Date();
  const currentDay = now.getDay(); // Sunday = 0, Monday = 1, etc.
  const dayItems = document.querySelectorAll('.day-item');
  
  dayItems.forEach((item, index) => {
    if (index === currentDay) {
      item.classList.add('current');
    } else {
      item.classList.remove('current');
    }
  });
}

let emailTabs = { active: 'combined', accounts: [] };
let calTabs = { active: 'combined', accounts: [] };
let newsTab = 'israel';

function simplifyEvent(ev) {
  const start = ev.start || {};
  const raw = start.dateTime || start.date;
  let label = raw;
  try {
    const dt = new Date(raw);
    if (raw && raw.length > 10) {
      label = dt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false });
    } else {
      label = 'All day';
    }
  } catch (_) {}
  return `${label} — ${ev.title || '(no title)'}`;
}

async function refreshAgenda() {
  // Always use combined view for homepage
  const data = await fetchJSON('/api/calendar');
  if (!data) return;
  const today = document.getElementById('agenda-today');
  const tomorrow = document.getElementById('agenda-tomorrow');
  today.innerHTML = '';
  tomorrow.innerHTML = '';
  for (const e of data.today || []) {
    const li = document.createElement('li');
    li.textContent = simplifyEvent(e);
    today.appendChild(li);
  }
  for (const e of data.tomorrow || []) {
    const li = document.createElement('li');
    li.textContent = simplifyEvent(e);
    tomorrow.appendChild(li);
  }
}

function setAqiBadge(el, value) {
  el.className = 'badge';
  if (value == null || isNaN(value)) return;
  let cls = 'aqi-good', txt = 'Good';
  const v = Number(value);
  if (v <= 50) { cls='aqi-good'; txt='Good'; }
  else if (v <= 100) { cls='aqi-moderate'; txt='Moderate'; }
  else if (v <= 150) { cls='aqi-usg'; txt='USG'; }
  else if (v <= 200) { cls='aqi-unhealthy'; txt='Unhealthy'; }
  else if (v <= 300) { cls='aqi-very-unhealthy'; txt='Very Unhealthy'; }
  else { cls='aqi-hazardous'; txt='Hazardous'; }
  el.classList.add(cls);
  el.textContent = txt;
}

function setPm25Badge(el, value) {
  el.className = 'badge';
  if (value == null || isNaN(value)) return;
  const v = Number(value);
  // EPA breakpoints for PM2.5 (µg/m3)
  if (v <= 12) { el.classList.add('aqi-good'); el.textContent='Good'; }
  else if (v <= 35.4) { el.classList.add('aqi-moderate'); el.textContent='Moderate'; }
  else if (v <= 55.4) { el.classList.add('aqi-usg'); el.textContent='USG'; }
  else if (v <= 150.4) { el.classList.add('aqi-unhealthy'); el.textContent='Unhealthy'; }
  else if (v <= 250.4) { el.classList.add('aqi-very-unhealthy'); el.textContent='Very Unhealthy'; }
  else { el.classList.add('aqi-hazardous'); el.textContent='Hazardous'; }
}

async function refreshNextMeetingAndWeather() {
  // Always use combined view for homepage
  const next = await fetchJSON('/api/next-meeting');
  if (next) {
    document.getElementById('meeting-title').textContent = next.title || 'No upcoming';
    const meetingInEl = document.getElementById('meeting-in');
    if (next.start_time && next.title) {
      meetingInEl.textContent = `${next.start_time} (${next.in})`;
    } else {
      meetingInEl.textContent = next.in || '';
    }
  }
  const wx = await fetchJSON('/api/weather');
  if (wx && wx.current) {
    document.getElementById('wx-temp').textContent = Math.round(wx.current.temp);
    if (wx.today && wx.today.max != null) document.getElementById('wx-today-max').textContent = Math.round(wx.today.max);
    if (wx.tomorrow) {
      document.getElementById('wx-tmw-min').textContent = Math.round(wx.tomorrow.min);
      document.getElementById('wx-tmw-max').textContent = Math.round(wx.tomorrow.max);
    }
  }
  const today = new Date();
  const shDiv = document.getElementById('shabbat-clock');
  if (today.getDay() === 5) {
    const sab = await fetchJSON('/api/shabbat');
    if (sab) {
      const f = (x) => x ? new Date(x).toLocaleString([], { weekday: 'short', hour: '2-digit', minute: '2-digit', hour12: false }) : '—';
      const set = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v; };
      set('sh-in', f(sab.candle?.time));
      set('sh-out', f(sab.havdalah?.time));
      set('sh-parsha', sab.parsha || '—');
      const holidayText = sab.next_holiday || '—';
      const holidayDate = sab.next_holiday_date ? ` (${sab.next_holiday_date})` : '';
      set('sh-holiday', holidayText + holidayDate);
    }
    shDiv.style.display = '';
  } else {
    shDiv.style.display = 'none';
  }
  const aq = await fetchJSON('/api/aqi');
  if (aq) {
    if (aq.pm25 != null) {
      document.getElementById('pm25').textContent = Math.round(aq.pm25);
      setPm25Badge(document.getElementById('pm25-desc'), aq.pm25);
    }
    if (aq.aqi != null) {
      document.getElementById('aqi').textContent = Math.round(aq.aqi);
      setAqiBadge(document.getElementById('aqi-desc'), aq.aqi);
    }
  }
}

async function refreshNews() {
  // Fetch combined news from both Israel and Jerusalem feeds
  const israelItems = await fetchJSON('/api/news');
  const jerusalemItems = await fetchJSON('/api/news?q=Jerusalem');
  const list = document.getElementById('news-list');
  
  if (!list) return;
  
  // Combine and sort news items by date
  const allItems = [];
  if (israelItems) allItems.push(...israelItems);
  if (jerusalemItems) allItems.push(...jerusalemItems);
  
  // Remove duplicates based on title and sort by recency
  const uniqueItems = allItems.filter((item, index, self) => 
    index === self.findIndex(t => t.title === item.title)
  );
  
  // Take the latest 10 items
  const latestItems = uniqueItems.slice(0, 10);
  
  list.innerHTML = '';
  for (const it of latestItems) {
    const li = document.createElement('li');
    li.innerHTML = `<a href="${it.link}" target="_blank">${it.title}</a> <span class="meta">${it.source} • ${it.ago}</span>`;
    list.appendChild(li);
  }
}

async function refreshAlerts() {
  const el = document.getElementById('alert-latest');
  const overlay = document.getElementById('red-alert-overlay');
  const latest = await fetchJSON('/api/alerts');
  
  if (!latest || Object.keys(latest).length === 0) {
    el.textContent = 'No recent alerts';
    overlay.classList.remove('active');
    return;
  }
  
  const t = latest.when ? new Date(latest.when) : null;
  let timeLabel = '';
  if (t) {
    const now = new Date();
    const alertDate = new Date(t.getFullYear(), t.getMonth(), t.getDate());
    const todayDate = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const dayDiff = Math.floor((todayDate - alertDate) / (1000 * 60 * 60 * 24));
    
    timeLabel = t.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false });
    if (dayDiff > 0) {
      timeLabel += ` (-${dayDiff}D)`;
    }
  }
  
  const text = latest.text || latest.title || latest.location || '';
  const alertText = `${text}${timeLabel ? ' — ' + timeLabel : ''}`;
  el.textContent = alertText;
  
  // Show overlay when there are alerts
  overlay.classList.add('active');
}

async function refreshEmailsPills() {
  const ul = document.getElementById('email-list');
  ul.innerHTML = '';
  const qs = emailTabs.active !== 'combined' ? `?account=${encodeURIComponent(emailTabs.active)}` : '';
  const items = await fetchJSON('/api/emails' + qs);
  if (!items) return;
  for (const it of items) {
    const li = document.createElement('li');
    li.dataset.id = it.id;
    li.dataset.account = it.account || (emailTabs.active !== 'combined' ? emailTabs.active : '');
    const title = document.createElement('div'); title.className = 'item-title'; title.textContent = (it.subject || '(no subject)').slice(0, 120);
    const sub = document.createElement('div'); sub.className = 'item-sub'; sub.textContent = `${(it.from || '').replace(/<.*?>/, '')} • ${relativeTime(it.received)}`;
    const expand = document.createElement('div'); expand.className = 'item-sub'; expand.style.display = 'none';
    li.appendChild(title); li.appendChild(sub); li.appendChild(expand);
    li.addEventListener('click', async () => {
      if (expand.style.display === 'none') {
        expand.style.display = '';
        expand.textContent = 'Loading…';
        const acc = li.dataset.account || it.account || '';
        const det = await fetchJSON(`/api/email/${encodeURIComponent(li.dataset.id)}?account=${encodeURIComponent(acc)}`);
        expand.textContent = det && det.snippet ? det.snippet : '(no preview)';
      } else {
        expand.style.display = 'none';
      }
    });
    ul.appendChild(li);
  }
}

async function refreshStatus() {
  const s = await fetchJSON('/api/status');
  if (!s) return;
  if (!s.google_accounts || s.google_accounts < 1) {
    const emails = document.getElementById('email-list');
    const agendaToday = document.getElementById('agenda-today');
    const agendaTomorrow = document.getElementById('agenda-tomorrow');
    const prompt = document.createElement('li');
    const link = document.createElement('a');
    link.href = '/auth/google';
    link.textContent = 'Connect Google to show emails and calendar';
    prompt.appendChild(link);
    emails.innerHTML = '';
    emails.appendChild(prompt.cloneNode(true));
    agendaToday.innerHTML = '';
    agendaTomorrow.innerHTML = '';
    agendaToday.appendChild(prompt.cloneNode(true));
  }
}

function schedule() {
  refreshTime();
  refreshAgenda();
  refreshNextMeetingAndWeather();
  refreshEmailsPills();
  refreshNews();
  refreshStatus();
  refreshAlerts();

  setInterval(refreshTime, 15 * 1000);
  setInterval(refreshAgenda, 60 * 1000);
  setInterval(refreshNextMeetingAndWeather, 5 * 60 * 1000);
  setInterval(refreshEmailsPills, 60 * 1000);
  setInterval(refreshNews, 10 * 60 * 1000);
  setInterval(refreshAlerts, 30 * 1000);
}

document.addEventListener('DOMContentLoaded', schedule);

document.addEventListener('DOMContentLoaded', async () => {
  const status = await fetchJSON('/api/status');
  const emails = Array.isArray(status?.accounts) ? status.accounts : [];
  const labels = status?.labels || {};
  emailTabs.accounts = emails; calTabs.accounts = emails;
  function buildTabs(el, items, active, onChange) {
    el.innerHTML = '';
    const all = [{ key: 'combined', label: 'Combined' }].concat(items.map(e => {
      let label = e;
      if (labels && (labels.personal === e)) label = 'Personal';
      if (labels && (labels.business === e)) label = 'Business';
      return { key: e, label };
    }));
    for (const it of all) {
      const span = document.createElement('span');
      span.className = 'tab' + (active === it.key ? ' active' : '');
      span.textContent = it.label;
      span.addEventListener('click', () => onChange(it.key));
      el.appendChild(span);
    }
  }
  // Hide email and calendar tabs on homepage by not building them
  // Email tabs - hidden on homepage
  const et = document.getElementById('email-tabs');
  if (et) et.style.display = 'none';
  
  // Calendar tabs - hidden on homepage  
  const ct = document.getElementById('cal-tabs');
  if (ct) ct.style.display = 'none';
  
  // News tabs removed - now showing combined news
});

// Video feed logic
document.addEventListener('DOMContentLoaded', async () => {
  const st = await fetchJSON('/api/status');
  const cfg = st?.video || {};
  const wrap = document.getElementById('video-wrap');
  const tabs = document.getElementById('video-tabs');
  const btnT = document.getElementById('vid-toggle');
  const btnM = document.getElementById('vid-mute');
  const btnZ = document.getElementById('vid-zoom');
  const btnF = document.getElementById('vid-full');
  const btnO = document.getElementById('vid-open');
  const store = (k,v) => localStorage.setItem(k, String(v));
  const read = (k, d) => { const v=localStorage.getItem(k); if (v==null) return d; return v==='true'; };
  let on = read('video_on', !!cfg.enabled);
  let zoom = read('video_zoom', false);
  let muted = read('video_muted', true);
  const rooms = cfg.rooms || {};
  const roomKeys = Object.keys(rooms).filter(k => rooms[k]);
  let activeRoom = localStorage.getItem('video_room') || cfg.default || (roomKeys[0] || '');

  function buildTabs() {
    if (!tabs) return;
    tabs.innerHTML = '';
    if (roomKeys.length === 0) return;
    const all = roomKeys.map(k => ({ key: k, label: k.replace('-', ' ').replace(/\b\w/g, c => c.toUpperCase()) }));
    for (const it of all) {
      const span = document.createElement('span');
      span.className = 'tab' + (activeRoom === it.key ? ' active' : '');
      span.textContent = it.label;
      span.addEventListener('click', () => { activeRoom = it.key; localStorage.setItem('video_room', activeRoom); render(); buildTabs(); });
      tabs.appendChild(span);
    }
  }

  function currentUrl(useWebRTC = false) {
    if (rooms && rooms[activeRoom]) {
      const baseUrl = rooms[activeRoom];
      if (useWebRTC && baseUrl.includes('1984/stream.html')) {
        return baseUrl.replace('stream.html', 'api/ws').replace('&mode=webrtc', '') + '&mode=webrtc';
      }
      return baseUrl;
    }
    return cfg.url || '';
  }

  function render() {
    wrap.innerHTML = '';
    btnT.textContent = on ? 'Turn Off' : 'Turn On';
    btnT.classList.toggle('active', on);
    btnZ.classList.toggle('active', zoom);
    btnM.classList.toggle('active', muted);
    const url = currentUrl();
    if (!on || !url) return;
    const holder = document.createElement('div');
    holder.style.width = '100%'; holder.style.height = '100%';
    holder.className = zoom ? 'zoomed' : '';
    
    // Try WebRTC first for Go2RTC streams
    if (url.includes('1984/stream.html')) {
      const webrtcUrl = url + '&mode=webrtc';
      const f = document.createElement('iframe');
      f.src = webrtcUrl;
      f.className = 'video-frame';
      f.allowFullscreen = true;
      holder.appendChild(f);
      btnM.disabled = true; btnM.title = 'Mute not available for WebRTC iframe';
    } else if (cfg.embed === 'video' && (url.endsWith('.mp4') || url.endsWith('.m3u8') || url.includes('.mp4') || url.includes('.m3u8'))) {
      const v = document.createElement('video');
      v.src = url;
      v.autoplay = true; v.playsInline = true; v.muted = muted; v.controls = false;
      v.preload = 'none';
      v.setAttribute('playsinline', 'true');
      v.style.objectFit = 'cover';
      v.className = 'video-el';
      holder.appendChild(v);
    } else {
      const f = document.createElement('iframe');
      f.src = url;
      f.className = 'video-frame';
      f.allowFullscreen = true;
      holder.appendChild(f);
      btnM.disabled = true; btnM.title = 'Mute not available for page embeds';
    }
    wrap.appendChild(holder);
  }

  btnT?.addEventListener('click', () => { on = !on; store('video_on', on); render(); });
  btnZ?.addEventListener('click', () => { zoom = !zoom; store('video_zoom', zoom); render(); });
  btnM?.addEventListener('click', () => {
    muted = !muted; store('video_muted', muted);
    const vid = wrap.querySelector('video'); if (vid) { vid.muted = muted; }
    render();
  });
  btnF?.addEventListener('click', () => {
    const el = wrap;
    if (el.requestFullscreen) el.requestFullscreen();
    else if (el.webkitRequestFullscreen) el.webkitRequestFullscreen();
    else if (el.msRequestFullscreen) el.msRequestFullscreen();
  });
  btnO?.addEventListener('click', () => {
    const url = currentUrl(); if (url) window.open(url, '_blank');
  });

  buildTabs();
  render();
});

// --- Bottom nav: highlight active link ---
document.addEventListener('DOMContentLoaded', () => {
  const path = window.location.pathname || '/';
  document.querySelectorAll('.bottom-nav a').forEach(a => {
    const href = a.getAttribute('href');
    if (href === path) a.classList.add('active');
    // mark Home active for root
    if (path === '/' && a.dataset.nav === 'home') a.classList.add('active');
  });
});

// --- Email Page: mixed personal/business grid ---
async function renderEmailColumn(selector, accountEmail) {
  const ul = document.querySelector(selector);
  if (!ul || !accountEmail) return;
  ul.innerHTML = '';
  const items = await fetchJSON('/api/emails?account=' + encodeURIComponent(accountEmail));
  if (!items) return;
  for (const it of items) {
    const li = document.createElement('li');
    const title = document.createElement('div'); title.className = 'item-title'; title.textContent = (it.subject || '(no subject)').slice(0, 120);
    const sub = document.createElement('div'); sub.className = 'item-sub'; sub.textContent = `${(it.from || '').replace(/<.*?>/, '')} • ${relativeTime(it.received)}`;
    li.appendChild(title); li.appendChild(sub);
    ul.appendChild(li);
  }
}

// --- Email Page: two-column layout with personal/business separation ---
document.addEventListener('DOMContentLoaded', async () => {
  const emailPersonal = document.getElementById('email-personal');
  const emailBusiness = document.getElementById('email-business');
  if (!emailPersonal && !emailBusiness) return;
  
  async function loadEmailPage() {
    const personalUl = document.getElementById('email-list-personal');
    const businessUl = document.getElementById('email-list-business');
    if (!personalUl || !businessUl) return;
    
    personalUl.innerHTML = '';
    businessUl.innerHTML = '';
    
    const items = await fetchJSON('/api/emails');
    if (!items) return;
    
    for (const it of items) {
      const li = document.createElement('li');
      li.dataset.id = it.id;
      li.dataset.account = it.account || '';
      
      const title = document.createElement('div');
      title.className = 'item-title';
      title.textContent = (it.subject || '(no subject)').slice(0, 120);
      
      const sub = document.createElement('div');
      sub.className = 'item-sub';
      const sourceTag = it.account_type || 'Personal';
      sub.textContent = `${(it.from || '').replace(/<.*?>/, '')} • ${relativeTime(it.received)}`;
      
      const expand = document.createElement('div');
      expand.className = 'item-sub';
      expand.style.display = 'none';
      
      li.appendChild(title);
      li.appendChild(sub);
      li.appendChild(expand);
      
      li.addEventListener('click', async () => {
        if (expand.style.display === 'none') {
          expand.style.display = '';
          expand.textContent = 'Loading…';
          const acc = li.dataset.account || it.account || '';
          const det = await fetchJSON(`/api/email/${encodeURIComponent(li.dataset.id)}?account=${encodeURIComponent(acc)}`);
          expand.textContent = det && det.snippet ? det.snippet : '(no preview)';
        } else {
          expand.style.display = 'none';
        }
      });
      
      // Add to appropriate column based on account type
      if (sourceTag === 'Business') {
        businessUl.appendChild(li);
      } else {
        personalUl.appendChild(li);
      }
    }
  }
  
  await loadEmailPage();
  setInterval(loadEmailPage, 60 * 1000);
});

// --- Calendar Week Page (Sun-Sat agenda with today highlighted) ---
document.addEventListener('DOMContentLoaded', async () => {
  const page = document.getElementById('calendar-week-page');
  if (!page) return;
  async function loadWeek() {
    const data = await fetchJSON('/api/calendar/week');
    if (!data) return;
    const rangeEl = document.getElementById('week-range');
    if (rangeEl && data.range) {
      rangeEl.textContent = `${data.range.start} — ${data.range.end}`;
    }
    const cont = document.getElementById('week-grid');
    cont.innerHTML = '';
    const todayKey = data.today;
    for (const day of (data.days || [])) {
      const wrap = document.createElement('div');
      wrap.className = 'week-day' + (day.date === todayKey ? ' today' : '');
      const head = document.createElement('div'); head.className = 'day-head'; head.textContent = day.label;
      const ul = document.createElement('ul'); ul.className = 'list';
      for (const e of (day.events || [])) {
        const li = document.createElement('li');
        li.textContent = simplifyEvent(e);
        ul.appendChild(li);
      }
      wrap.appendChild(head); wrap.appendChild(ul);
      cont.appendChild(wrap);
    }
  }
  await loadWeek();
  setInterval(loadWeek, 60 * 1000);
});

// --- Next Meeting on Calendar Page ---
document.addEventListener('DOMContentLoaded', async () => {
  const nextMeetingCard = document.getElementById('next-meeting-card');
  if (!nextMeetingCard) return;
  
  async function loadNextMeetingCalendar() {
    const next = await fetchJSON('/api/next-meeting');
    if (next) {
      document.getElementById('meeting-title-calendar').textContent = next.title || 'No upcoming meetings';
      const meetingInEl = document.getElementById('meeting-in-calendar');
      if (next.start_time && next.title) {
        meetingInEl.textContent = `${next.start_time} (${next.in})`;
      } else {
        meetingInEl.textContent = next.in || '';
      }
    }
  }
  
  loadNextMeetingCalendar();
  setInterval(loadNextMeetingCalendar, 5 * 60 * 1000);
});

// --- Calendar Three-Day Page (Today, Tomorrow, Day After agenda) ---
document.addEventListener('DOMContentLoaded', async () => {
  const page = document.getElementById('calendar-three-day-page');
  if (!page) return;
  
  async function loadThreeDay() {
    const data = await fetchJSON('/api/calendar/three-day');
    if (!data) return;
    
    const cont = document.getElementById('three-day-grid');
    cont.innerHTML = '';
    const todayKey = data.today;
    
    for (const day of (data.days || [])) {
      const wrap = document.createElement('div');
      wrap.className = 'three-day-item' + (day.date === todayKey ? ' today' : '');
      
      const head = document.createElement('div');
      head.className = 'day-head';
      head.textContent = day.label;
      
      const date = document.createElement('div');
      date.className = 'day-date';
      date.textContent = day.full_date;
      
      const ul = document.createElement('ul');
      ul.className = 'list';
      
      for (const e of (day.events || [])) {
        const li = document.createElement('li');
        li.textContent = simplifyEvent(e);
        ul.appendChild(li);
      }
      
      if (day.events.length === 0) {
        const li = document.createElement('li');
        li.textContent = 'No events';
        li.style.color = 'var(--muted)';
        li.style.fontStyle = 'italic';
        ul.appendChild(li);
      }
      
      wrap.appendChild(head);
      wrap.appendChild(date);
      wrap.appendChild(ul);
      cont.appendChild(wrap);
    }
  }
  
  await loadThreeDay();
  setInterval(loadThreeDay, 60 * 1000);
});

// --- Israel Holidays Page ---
document.addEventListener('DOMContentLoaded', async () => {
  const page = document.getElementById('israel-holidays-page');
  if (!page) return;
  
  async function loadIsraelHolidays() {
    const data = await fetchJSON('/api/holidays/israel');
    if (!data) return;
    
    const cont = document.getElementById('holidays-grid');
    cont.innerHTML = '';
    
    const holidays = data.holidays || [];
    
    if (holidays.length === 0) {
      const noHolidays = document.createElement('div');
      noHolidays.textContent = 'No upcoming holidays found';
      noHolidays.style.color = 'var(--muted)';
      noHolidays.style.fontStyle = 'italic';
      noHolidays.style.textAlign = 'center';
      noHolidays.style.padding = '20px';
      cont.appendChild(noHolidays);
      return;
    }
    
    // Create a grid layout for holidays
    cont.style.display = 'grid';
    cont.style.gridTemplateColumns = 'repeat(auto-fit, minmax(280px, 1fr))';
    cont.style.gap = '12px';
    cont.style.padding = '12px';
    
    for (const holiday of holidays) {
      const holidayCard = document.createElement('div');
      holidayCard.className = 'holiday-card';
      holidayCard.style.padding = '12px';
      holidayCard.style.border = '1px solid var(--border)';
      holidayCard.style.borderRadius = '8px';
      holidayCard.style.backgroundColor = 'var(--card-bg)';
      
      const name = document.createElement('div');
      name.className = 'holiday-name';
      name.textContent = holiday.name;
      name.style.fontWeight = 'bold';
      name.style.fontSize = '14px';
      name.style.marginBottom = '6px';
      
      const date = document.createElement('div');
      date.className = 'holiday-date';
      date.textContent = holiday.formatted_date;
      date.style.fontSize = '12px';
      date.style.color = 'var(--muted)';
      date.style.marginBottom = '6px';
      
      const meta = document.createElement('div');
      meta.style.display = 'flex';
      meta.style.alignItems = 'center';
      meta.style.gap = '8px';
      meta.style.fontSize = '11px';
      
      // Type badge
      const typeBadge = document.createElement('span');
      typeBadge.textContent = holiday.type;
      typeBadge.style.padding = '2px 6px';
      typeBadge.style.borderRadius = '10px';
      typeBadge.style.fontSize = '10px';
      typeBadge.style.fontWeight = 'bold';
      
      // Color code by type
      switch (holiday.type) {
        case 'Religious':
          typeBadge.style.backgroundColor = '#e3f2fd';
          typeBadge.style.color = '#1976d2';
          break;
        case 'National':
          typeBadge.style.backgroundColor = '#f3e5f5';
          typeBadge.style.color = '#7b1fa2';
          break;
        case 'Memorial':
          typeBadge.style.backgroundColor = '#fff3e0';
          typeBadge.style.color = '#f57c00';
          break;
        default:
          typeBadge.style.backgroundColor = '#f5f5f5';
          typeBadge.style.color = '#666';
      }
      
      // Days until
      const daysUntil = document.createElement('span');
      if (holiday.days_until === 0) {
        daysUntil.textContent = 'Today';
        daysUntil.style.color = 'var(--accent)';
        daysUntil.style.fontWeight = 'bold';
      } else if (holiday.days_until === 1) {
        daysUntil.textContent = 'Tomorrow';
        daysUntil.style.color = 'var(--accent)';
      } else {
        daysUntil.textContent = `in ${holiday.days_until} days`;
        daysUntil.style.color = 'var(--muted)';
      }
      
      meta.appendChild(typeBadge);
      meta.appendChild(daysUntil);
      
      holidayCard.appendChild(name);
      holidayCard.appendChild(date);
      holidayCard.appendChild(meta);
      cont.appendChild(holidayCard);
    }
  }
  
  await loadIsraelHolidays();
  // Refresh every 6 hours since holidays don't change frequently
  setInterval(loadIsraelHolidays, 6 * 60 * 60 * 1000);
});

// --- News Page: two-column grid of story cards ---
document.addEventListener('DOMContentLoaded', async () => {
  const newsGrid = document.getElementById('news-grid');
  if (!newsGrid) return;
  
  function getSourceName(story) {
    let sourceName = story.source || 'NEWS';
    if (!story.source && story.link) {
      try {
        const url = new URL(story.link);
        const hostname = url.hostname.toLowerCase();
        if (hostname.includes('haaretz')) sourceName = 'Haaretz';
        else if (hostname.includes('jpost')) sourceName = 'Jerusalem Post';
        else if (hostname.includes('timesofisrael')) sourceName = 'Times of Israel';
        else if (hostname.includes('ynet')) sourceName = 'Ynet';
        else if (hostname.includes('i24news')) sourceName = 'i24NEWS';
        else if (hostname.includes('reuters')) sourceName = 'Reuters';
        else if (hostname.includes('bbc')) sourceName = 'BBC';
        else if (hostname.includes('cnn')) sourceName = 'CNN';
        else if (hostname.includes('ap.org')) sourceName = 'AP News';
        else sourceName = hostname.replace('www.', '').split('.')[0];
        sourceName = sourceName.charAt(0).toUpperCase() + sourceName.slice(1);
      } catch (_) {}
    }
    return sourceName;
  }
  
  function formatTimeAgo(publishedDate) {
    if (!publishedDate) return 'Recently';
    
    const publishedTime = new Date(publishedDate);
    const now = new Date();
    const diffMs = now - publishedTime;
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffHours / 24);
    
    if (diffDays > 0) {
      return `${diffDays}d ago`;
    } else if (diffHours > 0) {
      return `${diffHours}h ago`;
    } else {
      const diffMins = Math.floor(diffMs / (1000 * 60));
      return `${Math.max(1, diffMins)}m ago`;
    }
  }
  
  async function loadNewsPage() {
    const items = await fetchJSON('/api/news');
    if (!items) {
      newsGrid.innerHTML = '<div class="loading">Failed to load news</div>';
      return;
    }
    
    newsGrid.innerHTML = '';
    
    for (const story of items) {
      const newsItem = document.createElement('a');
      newsItem.className = 'news-item';
      newsItem.href = story.link;
      newsItem.target = '_blank';
      
      const title = document.createElement('div');
      title.className = 'news-title';
      title.textContent = story.title || '(no title)';
      
      const meta = document.createElement('div');
      meta.className = 'news-meta';
      
      const sourceBubble = document.createElement('span');
      sourceBubble.className = 'news-source';
      sourceBubble.textContent = getSourceName(story);
      
      const timeSpan = document.createElement('span');
      timeSpan.className = 'news-time';
      timeSpan.textContent = formatTimeAgo(story.published);
      
      meta.appendChild(sourceBubble);
      meta.appendChild(timeSpan);
      
      newsItem.appendChild(title);
      newsItem.appendChild(meta);
      
      // Add summary if available
      if (story.summary && story.summary.trim()) {
        const summary = document.createElement('div');
        summary.className = 'news-summary';
        summary.textContent = story.summary;
        newsItem.appendChild(summary);
      }
      
      newsGrid.appendChild(newsItem);
    }
  }
  
  await loadNewsPage();
  setInterval(loadNewsPage, 15 * 60 * 1000); // Refresh every 15 minutes
});

// --- Zmanim Widget ---
document.addEventListener('DOMContentLoaded', async () => {
  const zmanimView = document.getElementById('zmanim-view');
  const zmanimFullCard = document.getElementById('zmanim-full-card');
  if (!zmanimView && !zmanimFullCard) return;

  function formatTime(isoString) {
    if (!isoString) return '—';
    try {
      const date = new Date(isoString);
      return date.toLocaleTimeString('en-US', { 
        hour: '2-digit', 
        minute: '2-digit',
        hour12: false 
      });
    } catch (e) {
      return '—';
    }
  }

  function formatDate(dateString) {
    if (!dateString) return '—';
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString('en-US', { 
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric'
      });
    } catch (e) {
      return '—';
    }
  }

  async function loadZmanim() {
    const data = await fetchJSON('/api/zmanim');
    if (!data) return;

    // Update Shabbat information (homepage toggle view)
    const shabbat = data.shabbat || {};
    
    // Homepage Parsha
    const parshaEl = document.getElementById('zmanim-parsha');
    if (parshaEl) {
      parshaEl.textContent = shabbat.parsha || '—';
    }

    // Full page Parsha
    const parshaFullEl = document.getElementById('zmanim-parsha-full');
    if (parshaFullEl) {
      parshaFullEl.textContent = shabbat.parsha || '—';
    }

    // Candle lighting (both views)
    const candleEl = document.getElementById('zmanim-candle');
    const candleFullEl = document.getElementById('zmanim-candle-full');
    const candleTime = shabbat.candle_lighting ? formatTime(shabbat.candle_lighting.time) : '—';
    if (candleEl) candleEl.textContent = candleTime;
    if (candleFullEl) candleFullEl.textContent = candleTime;

    // Havdalah (both views)
    const havdalahEl = document.getElementById('zmanim-havdalah');
    const havdalahFullEl = document.getElementById('zmanim-havdalah-full');
    const havdalahTime = shabbat.havdalah ? formatTime(shabbat.havdalah.time) : '—';
    if (havdalahEl) havdalahEl.textContent = havdalahTime;
    if (havdalahFullEl) havdalahFullEl.textContent = havdalahTime;

    // Date display for full page
    const dateEl = document.getElementById('zmanim-date-display');
    if (dateEl) {
      dateEl.textContent = formatDate(data.date);
    }

    // Hebrew date display for full page
    const hebrewDateEl = document.getElementById('zmanim-hebrew-date');
    if (hebrewDateEl) {
      // Fetch Hebrew date from the time API
      fetchJSON('/api/time').then(timeData => {
        if (timeData && timeData.hebrew) {
          hebrewDateEl.textContent = timeData.hebrew;
        }
      }).catch(() => {
        hebrewDateEl.textContent = '—';
      });
    }

    // Update daily Zmanim
    const zmanim = data.zmanim || {};
    
    // Homepage elements
    const zmanimElements = {
      'zmanim-alot': zmanim.alot_hashachar,
      'zmanim-sunrise': zmanim.sunrise,
      'zmanim-shema': zmanim.sof_zman_shma_gra,
      'zmanim-tefillah': zmanim.sof_zman_tfilla_gra,
      'zmanim-chatzot': zmanim.chatzot,
      'zmanim-mincha-gedola': zmanim.mincha_gedola,
      'zmanim-mincha-ketana': zmanim.mincha_ketana,
      'zmanim-sunset': zmanim.sunset,
      'zmanim-tzeit': zmanim.tzeit_hakochavim
    };

    // Full page elements
    const zmanimFullElements = {
      'zmanim-alot-full': zmanim.alot_hashachar,
      'zmanim-misheyakir-full': zmanim.misheyakir,
      'zmanim-sunrise-full': zmanim.sunrise,
      'zmanim-shema-full': zmanim.sof_zman_shma_gra,
      'zmanim-tefillah-full': zmanim.sof_zman_tfilla_gra,
      'zmanim-chatzot-full': zmanim.chatzot,
      'zmanim-mincha-gedola-full': zmanim.mincha_gedola,
      'zmanim-mincha-ketana-full': zmanim.mincha_ketana,
      'zmanim-plag-full': zmanim.plag_hamincha,
      'zmanim-sunset-full': zmanim.sunset,
      'zmanim-tzeit-full': zmanim.tzeit_hakochavim
    };

    // Update homepage elements
    Object.entries(zmanimElements).forEach(([elementId, time]) => {
      const el = document.getElementById(elementId);
      if (el) {
        el.textContent = formatTime(time);
      }
    });

    // Update full page elements
    Object.entries(zmanimFullElements).forEach(([elementId, time]) => {
      const el = document.getElementById(elementId);
      if (el) {
        el.textContent = formatTime(time);
      }
    });
  }

  await loadZmanim();
  // Refresh every hour
  setInterval(loadZmanim, 60 * 60 * 1000);

  // Initialize tab switching functionality for Zmanim page
  const tabButtons = document.querySelectorAll('.tab-button');
  const tabContents = document.querySelectorAll('.tab-content');

  if (tabButtons.length > 0 && tabContents.length > 0) {
    tabButtons.forEach(button => {
      button.addEventListener('click', () => {
        const targetTab = button.getAttribute('data-tab');
        
        // Remove active class from all buttons and contents
        tabButtons.forEach(btn => btn.classList.remove('active'));
        tabContents.forEach(content => content.classList.remove('active'));
        
        // Add active class to clicked button and corresponding content
        button.classList.add('active');
        const targetContent = document.getElementById(targetTab);
        if (targetContent) {
          targetContent.classList.add('active');
        }
      });
    });
  }
});

// --- Red Alert Widget ---
document.addEventListener('DOMContentLoaded', async () => {
  const alertCard = document.getElementById('red-alert');
  if (!alertCard) return;

  function formatLastUpdated(isoString) {
    if (!isoString) return '—';
    try {
      const date = new Date(isoString);
      const now = new Date();
      const diffMs = now - date;
      const diffMins = Math.floor(diffMs / 60000);
      
      if (diffMins < 1) return 'Just now';
      if (diffMins < 60) return `${diffMins}m ago`;
      
      const diffHours = Math.floor(diffMins / 60);
      if (diffHours < 24) return `${diffHours}h ago`;
      
      return date.toLocaleDateString();
    } catch (e) {
      return '—';
    }
  }

  async function loadRedAlert() {
    const data = await fetchJSON('/api/red-alert');
    if (!data) return;

    const statusDot = document.getElementById('status-dot');
    const statusText = document.getElementById('status-text');
    const lastUpdated = document.getElementById('last-updated');
    const alertLocations = document.getElementById('alert-locations');
    const alertCount = document.getElementById('alert-count');

    // Update status indicator
    if (statusDot && statusText) {
      statusDot.className = `status-dot ${data.status}`;
      
      // Show last alert time instead of just status
      if (data.last_alert_display) {
        statusText.textContent = `Last: ${data.last_alert_display}`;
      } else {
        switch (data.status) {
          case 'clear':
            statusText.textContent = 'No recent alerts';
            break;
          case 'active':
            statusText.textContent = 'Active Alert';
            break;
          case 'unknown':
            statusText.textContent = 'Status Unknown';
            break;
          case 'error':
            statusText.textContent = 'Connection Error';
            break;
          default:
            statusText.textContent = 'Checking...';
        }
      }
    }

    // Update last updated time
    if (lastUpdated) {
      lastUpdated.textContent = formatLastUpdated(data.last_updated);
    }

    // Update alert details
    if (alertLocations && alertCount) {
      if (data.alerts && data.alerts.length > 0) {
        // Display alert locations
        alertLocations.innerHTML = data.alerts.map(location => 
          `<div class="alert-location-item">${location}</div>`
        ).join('');
        
        // Display count
        alertCount.textContent = `${data.location_count} location${data.location_count !== 1 ? 's' : ''} affected`;
      } else {
        alertLocations.innerHTML = '<div style="text-align: center; color: var(--muted); padding: 8px;">No active alerts</div>';
        alertCount.textContent = 'No alerts';
      }
    }
  }

  await loadRedAlert();
  // Refresh every 30 seconds for Red Alerts
  setInterval(loadRedAlert, 30 * 1000);
});

document.addEventListener('DOMContentLoaded', initDashboardToggle);
