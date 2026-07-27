const $=s=>document.querySelector(s); let vehicleId=null;
function csrf(){return decodeURIComponent((document.cookie.split('; ').find(x=>x.startsWith('autopassport_csrf='))||'=').split('=')[1])}
async function api(url,o={}){const m=(o.method||'GET').toUpperCase(),h={...(o.headers||{})};if(!['GET','HEAD'].includes(m))h['X-CSRF-Token']=csrf();const r=await fetch(url,{credentials:'same-origin',...o,headers:h});if(!r.ok){const b=await r.json().catch(()=>({}));throw Error(b.detail||`HTTP ${r.status}`)}return r.status===204?null:r.json()}
async function garage(){const rows=await api('/api/vehicles');$('#app').hidden=false;$('#auth').hidden=true;$('#garage').innerHTML=rows.map(v=>`<button class="vehicle" data-id="${v.id}"><b>${v.make} ${v.model}</b><span>${v.current_mileage.toLocaleString('ru-RU')} км</span></button>`).join('')||'<p>Добавьте первый автомобиль.</p>';document.querySelectorAll('.vehicle').forEach(b=>b.onclick=()=>openVehicle(b.dataset.id))}
function money(v){return v===null||v===undefined?'':`${Number(v).toLocaleString('ru-RU')} ₽`}
async function openVehicle(id){vehicleId=id;const d=await api(`/api/vehicles/${id}`);$('#detail').hidden=false;$('#share').hidden=false;$('#vehicle').innerHTML=`<h2>${d.vehicle.make} ${d.vehicle.model} ${d.vehicle.year}</h2><p>${d.vehicle.vin} · ${d.vehicle.registration_number||''} · ${d.vehicle.current_mileage.toLocaleString('ru-RU')} км</p>`;$('#visits').innerHTML=(d.visits||[]).map(v=>`<article class="card"><small>${v.visit_date} · ${v.trust_level} · rev.${v.revision}</small><h3>${v.title}</h3><p>${v.location||''}</p><p>${v.mileage?v.mileage.toLocaleString('ru-RU')+' км':''} ${money(v.total_cost_rubles)}</p><ul>${v.items.map(i=>`<li>${i.title} — ${i.cost_status}${i.cost_rubles?` · ${money(i.cost_rubles)}`:''}</li>`).join('')}</ul><button class="delete-visit" data-id="${v.id}">Скрыть визит</button></article>`).join('')||'<p>Визитов пока нет.</p>';$('#timeline').innerHTML=d.events.map(e=>`<article class="card"><small>${e.event_date} · ${e.trust_level} · rev.${e.revision}</small><h3>${e.title}</h3><p>${e.description}</p><p>${e.mileage?e.mileage.toLocaleString('ru-RU')+' км':''}</p><button class="delete" data-id="${e.id}">Скрыть событие</button></article>`).join('')||'<p>Событий пока нет.</p>';document.querySelectorAll('.delete').forEach(b=>b.onclick=async()=>{await api(`/api/events/${b.dataset.id}`,{method:'DELETE'});openVehicle(id)});document.querySelectorAll('.delete-visit').forEach(b=>b.onclick=async()=>{await api(`/api/visits/${b.dataset.id}`,{method:'DELETE'});openVehicle(id)})}
$('#authForm').onsubmit=async e=>{e.preventDefault();const body=new FormData(e.target);try{await api('/api/auth/login',{method:'POST',body})}catch(_){await api('/api/auth/register',{method:'POST',body})}garage()}
$('#vehicleForm').onsubmit=async e=>{e.preventDefault();const v=await api('/api/vehicles',{method:'POST',body:new FormData(e.target)});e.target.reset();garage();openVehicle(v.id)}
$('#eventForm').onsubmit=async e=>{e.preventDefault();await api(`/api/vehicles/${vehicleId}/events`,{method:'POST',body:new FormData(e.target)});e.target.reset();openVehicle(vehicleId)}
$('#visitForm').onsubmit=async e=>{e.preventDefault();const f=new FormData(e.target);const body={kind:f.get('kind'),visit_date:f.get('visit_date'),mileage:f.get('mileage')||null,title:f.get('title'),location:f.get('location'),total_cost_rubles:f.get('total_cost_rubles')||null,total_cost_status:f.get('total_cost_status'),total_cost_visible_to_public:f.get('total_cost_visible_to_public')==='on',items:[{item_type:f.get('item_type'),title:f.get('item_title'),brand:f.get('item_brand'),quantity:f.get('item_quantity'),unit:f.get('item_unit'),cost_rubles:f.get('item_cost_rubles')||null,cost_status:f.get('item_cost_status')}]} ; await api(`/api/vehicles/${vehicleId}/visits`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});e.target.reset();openVehicle(vehicleId)}
$('#share').onclick=async()=>{const s=await api(`/api/vehicles/${vehicleId}/share`,{method:'POST'});await navigator.clipboard.writeText(s.url).catch(()=>{});alert(`Ссылка действует 1 час:\n${s.url}`)}
api('/api/me').then(garage).catch(()=>{});

// PWA: cache only the app shell. API, PDF and private data stay network-only.
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/service-worker.js').catch(() => {});
  });
}

let deferredInstallPrompt = null;
const installButton = document.querySelector('#installApp');
window.addEventListener('beforeinstallprompt', event => {
  event.preventDefault();
  deferredInstallPrompt = event;
  if (installButton) installButton.hidden = false;
});
if (installButton) {
  installButton.onclick = async () => {
    if (!deferredInstallPrompt) return;
    deferredInstallPrompt.prompt();
    await deferredInstallPrompt.userChoice.catch(() => null);
    deferredInstallPrompt = null;
    installButton.hidden = true;
  };
}

const ownerPdfButton = document.querySelector('#downloadPdf');
if (ownerPdfButton) {
  ownerPdfButton.onclick = () => {
    if (!vehicleId) return;
    window.open(`/api/vehicles/${vehicleId}/pdf`, '_blank');
  };
}

