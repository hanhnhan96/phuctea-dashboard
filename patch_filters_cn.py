#!/usr/bin/env python3
"""Patch: month filter + auto date + THU CÔNG NỢ live data"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

orig = len(html)

# ═══════════════════════════════════════════════════════════════
# 1. FILTER HTML – thêm dropdown Tháng sau dropdown Năm
# ═══════════════════════════════════════════════════════════════
OLD_YEAR_DIV = '<option value="0" selected>Cả 2 năm</option></select></div><div class="fdiv"></div>\n  <div class="fg"><label>Xem theo</label>'
NEW_YEAR_DIV = '''<option value="0" selected>Cả 2 năm</option></select></div>
  <div class="fdiv"></div>
  <div class="fg"><label>Tháng</label>
    <select id="fMonth" onchange="onMonthChange()"><option value="">Tất cả tháng</option></select>
  </div>
  <div class="fdiv"></div>
  <div class="fg"><label>Xem theo</label>'''

if OLD_YEAR_DIV in html:
    html = html.replace(OLD_YEAR_DIV, NEW_YEAR_DIV, 1)
    print('✓ Thêm dropdown Tháng vào filters')
else:
    print('❌ Không tìm thấy anchor để thêm dropdown Tháng')

# ═══════════════════════════════════════════════════════════════
# 2. KPI TABLE HTML – thêm 2 hàng cnbh_tt + cnbh_pct vào bảng CN
# ═══════════════════════════════════════════════════════════════
MONTHS_CNBH_TT  = ''.join(f'<td id="cnbh_tt_{m}">–</td>' for m in range(1,13))
MONTHS_CNBH_PCT = ''.join(f'<td id="cnbh_pct_{m}" class="pct-na">–</td>' for m in range(1,13))

OLD_CN_ROWS = '<td id="cn_tt_total" style="font-weight:700">–</td></tr><tr><td class="left" style="font-weight:700;font-size:11px">% Đạt KH</td>'
NEW_CN_ROWS = (
    '<td id="cn_tt_total" style="font-weight:700">–</td></tr>\n'
    '<tr><td class="left" style="font-weight:700;color:#1a6b3c;font-size:11px">Thu CN BH (TT)</td>'
    + MONTHS_CNBH_TT +
    '<td id="cnbh_tt_total" style="font-weight:700">–</td></tr>\n'
    '<tr><td class="left" style="font-weight:700;font-size:11px">% CN BH / DT BH</td>'
    + MONTHS_CNBH_PCT +
    '<td id="cnbh_pct_total" class="pct-na">–</td></tr>\n'
    '<tr><td class="left" style="font-weight:700;font-size:11px">% Đạt KH</td>'
)

if OLD_CN_ROWS in html:
    html = html.replace(OLD_CN_ROWS, NEW_CN_ROWS, 1)
    print('✓ Thêm 2 hàng cnbh_tt + cnbh_pct vào bảng KPI CN')
else:
    print('❌ Không tìm thấy anchor bảng CN để thêm hàng')

# ═══════════════════════════════════════════════════════════════
# 3. KPI section title – cập nhật
# ═══════════════════════════════════════════════════════════════
html = html.replace(
    '2. Thu hồi Công nợ (VNĐ) — Nhập tay',
    '2. Thu hồi Công nợ (VNĐ) — từ Google Sheets',
    1
)
print('✓ Cập nhật title Section 2 KPI')

# ═══════════════════════════════════════════════════════════════
# 4. JS – Inject tất cả hàm mới trước function applyF()
# ═══════════════════════════════════════════════════════════════
SHEET_ID = '1DR4q16Whx7QFlw3KIPbtR-6RpbDpwQ1MeOyT3faHnu4'

NEW_JS = (
"""
// ===== MONTH FILTER =====
function updateMonthDropdown(){
  const y=parseInt((document.getElementById('fYear')||{}).value)||0;
  const data=y===0?D_ALL:D_ALL.filter(r=>r.nam===y);
  const months=[...new Set(data.map(r=>r.thang).filter(m=>m&&!isNaN(m)))].sort((a,b)=>a-b);
  const sel=document.getElementById('fMonth');
  if(!sel) return;
  const cur=sel.value;
  sel.innerHTML='<option value="">Tất cả tháng</option>';
  months.forEach(m=>{
    const o=document.createElement('option');
    o.value=m; o.textContent='Tháng '+m;
    if(String(m)===cur) o.selected=true;
    sel.appendChild(o);
  });
}

function onMonthChange(){
  const m=parseInt((document.getElementById('fMonth')||{}).value)||0;
  const y=parseInt((document.getElementById('fYear')||{}).value)||0;
  const fromEl=document.getElementById('fFrom');
  const toEl=document.getElementById('fTo');
  if(m && y && y!==0){
    const lastDay=new Date(y,m,0).getDate();
    if(fromEl) fromEl.value=`${y}-${String(m).padStart(2,'0')}-01`;
    if(toEl)   toEl.value  =`${y}-${String(m).padStart(2,'0')}-${String(lastDay).padStart(2,'0')}`;
  } else if(!m){
    if(fromEl) fromEl.value='';
    if(toEl)   toEl.value='';
  }
  applyF();
}

// ===== THU CÔNG NỢ – LIVE DATA =====
let _cnBH={}, _cnKPI={};

async function fetchCNFromSheet(){
  const url=`https://docs.google.com/spreadsheets/d/""" + SHEET_ID + """/gviz/tq?tqx=out:csv&sheet=THU%20C%C3%94NG%20N%E1%BB%A2`;
  try{
    const resp=await fetch(url,{cache:'no-store'});
    if(!resp.ok) throw new Error('HTTP '+resp.status);
    const text=await resp.text();
    if(!text||text.trim().startsWith('<')) throw new Error('Sheet chua public');
    const rows=parseSalesCSV(text);
    if(rows.length<2) return;
    _cnBH={}; _cnKPI={};
    for(let i=1;i<rows.length;i++){
      const r=rows[i];
      if(r[5]){
        const d=parseSalesDate(r[5]);
        if(d){const yr=parseInt(d.slice(0,4)),mo=parseInt(d.slice(5,7));
          if(yr&&mo){const k=yr+'-'+mo;_cnBH[k]=(_cnBH[k]||0)+(parseSalesNum(r[6])||0);}}
      }
      if(r[9]){
        const d=parseSalesDate(r[9]);
        if(d){const yr=parseInt(d.slice(0,4)),mo=parseInt(d.slice(5,7));
          if(yr&&mo){const k=yr+'-'+mo;_cnKPI[k]=(_cnKPI[k]||0)+(parseSalesNum(r[10])||0);}}
      }
    }
    applyCNToKPI();
    console.info('fetchCNFromSheet OK – BH months:',Object.keys(_cnBH).length,'KPI months:',Object.keys(_cnKPI).length);
  }catch(e){console.warn('fetchCNFromSheet:',e.message);}
}

function applyCNToKPI(){
  const fmt=n=>new Intl.NumberFormat('vi-VN').format(Math.round(n));
  const dtByM={};
  D_ALL.filter(r=>r.nam===2026).forEach(r=>{
    if(r.thang) dtByM[r.thang]=(dtByM[r.thang]||0)+(r.tongThanhTien||0);
  });
  let totBH=0,totDT=0;
  for(let m=1;m<=12;m++){
    // J:L → cn_tt_m
    const kv=_cnKPI['2026-'+m]||0;
    const cnEl=document.getElementById('cn_tt_'+m);
    if(cnEl&&kv){cnEl.value=fmt(kv);cnEl.classList.add('kpi-sheet-field');cnEl.readOnly=true;}
    // F:G → cnbh_tt_m
    const bv=_cnBH['2026-'+m]||0;
    const dt=dtByM[m]||0;
    totBH+=bv; totDT+=dt;
    const bhEl=document.getElementById('cnbh_tt_'+m);
    if(bhEl) bhEl.textContent=bv?fmt(bv):'–';
    const pEl=document.getElementById('cnbh_pct_'+m);
    if(pEl){
      if(!bv||!dt){pEl.innerHTML='<span class="pct-na">–</span>';}
      else{const r=bv/dt,p=(r*100).toFixed(1)+'%';
        const c=r>=1?'pct-cell pct-over':r>=0.8?'pct-cell':'pct-cell pct-low';
        pEl.innerHTML=`<span class="${c}">${p}</span>`;}
    }
  }
  const bhTot=document.getElementById('cnbh_tt_total');
  if(bhTot) bhTot.textContent=totBH?fmt(totBH):'–';
  const pTot=document.getElementById('cnbh_pct_total');
  if(pTot){
    if(!totBH||!totDT){pTot.innerHTML='<span class="pct-na">–</span>';}
    else{const r=totBH/totDT,p=(r*100).toFixed(1)+'%';
      const c=r>=1?'pct-cell pct-over':r>=0.8?'pct-cell':'pct-cell pct-low';
      pTot.innerHTML=`<span class="${c}">${p}</span>`;}
  }
  if(typeof recalcKPI==='function') recalcKPI();
}

setInterval(fetchCNFromSheet, 5*60*1000);

"""
)

TARGET = 'function applyF(){'
if TARGET in html:
    html = html.replace(TARGET, NEW_JS + TARGET, 1)
    print('✓ Inject updateMonthDropdown / onMonthChange / fetchCNFromSheet / applyCNToKPI')
else:
    print('❌ Không tìm thấy function applyF()')

# ═══════════════════════════════════════════════════════════════
# 5. getF() – thêm month
# ═══════════════════════════════════════════════════════════════
OLD_GETF = "function getF(){return{brand:fBrand.value,gran:fGran.value,from:fFrom.value,to:fTo.value,store:fStore.value,cat:fCat.value};}"
NEW_GETF = "function getF(){const _mEl=document.getElementById('fMonth');return{brand:fBrand.value,gran:fGran.value,from:fFrom.value,to:fTo.value,store:fStore.value,cat:fCat.value,month:_mEl?parseInt(_mEl.value)||0:0};}"
if OLD_GETF in html:
    html = html.replace(OLD_GETF, NEW_GETF, 1)
    print('✓ getF() thêm month')
else:
    print('❌ Không match getF()')

# ═══════════════════════════════════════════════════════════════
# 6. applyF() – thêm filter tháng
# ═══════════════════════════════════════════════════════════════
OLD_FILTER = "    if(f.cat&&r.loaiHang!==f.cat)return false;\n    if(f.from&&r.ngay"
NEW_FILTER = "    if(f.cat&&r.loaiHang!==f.cat)return false;\n    if(f.month&&r.thang!==f.month)return false;\n    if(f.from&&r.ngay"
if OLD_FILTER in html:
    html = html.replace(OLD_FILTER, NEW_FILTER, 1)
    print('✓ applyF() thêm f.month filter')
else:
    print('❌ Không match applyF filter chain')

# ═══════════════════════════════════════════════════════════════
# 7. onYearChange() – reset month + gọi updateMonthDropdown
# ═══════════════════════════════════════════════════════════════
OLD_OYC = (
    "function onYearChange(){\n"
    "  const y=parseInt(document.getElementById('fYear').value);\n"
    "  D_CY = (!y||y===0) ? D_ALL : D_ALL.filter(r=>r.nam===y);\n"
    "  // Clear date filter when switching year\n"
    "  document.getElementById('fFrom').value='';\n"
    "  document.getElementById('fTo').value='';\n"
    "  applyF();\n"
    "  updateMissMonths();\n"
    "  if(document.getElementById('page-miss').style.display!=='none') renderMissPage();\n"
    "}"
)
NEW_OYC = (
    "function onYearChange(){\n"
    "  const y=parseInt(document.getElementById('fYear').value);\n"
    "  D_CY = (!y||y===0) ? D_ALL : D_ALL.filter(r=>r.nam===y);\n"
    "  document.getElementById('fFrom').value='';\n"
    "  document.getElementById('fTo').value='';\n"
    "  const _mEl=document.getElementById('fMonth');if(_mEl)_mEl.value='';\n"
    "  updateMonthDropdown();\n"
    "  applyF();\n"
    "  updateMissMonths();\n"
    "  if(document.getElementById('page-miss').style.display!=='none') renderMissPage();\n"
    "}"
)
if OLD_OYC in html:
    html = html.replace(OLD_OYC, NEW_OYC, 1)
    print('✓ onYearChange() reset month + updateMonthDropdown')
else:
    print('❌ Không match onYearChange()')

# ═══════════════════════════════════════════════════════════════
# 8. resetF() – reset fMonth
# ═══════════════════════════════════════════════════════════════
OLD_RESET = (
    "function resetF(){\n"
    "  fBrand.value='';fGran.value='month';fFrom.value='';fTo.value='';fStore.value='';fCat.value='';\n"
    "  filt=[...D_CY];renderAll();\n"
    "}"
)
NEW_RESET = (
    "function resetF(){\n"
    "  fBrand.value='';fGran.value='month';fFrom.value='';fTo.value='';fStore.value='';fCat.value='';\n"
    "  const _mEl=document.getElementById('fMonth');if(_mEl)_mEl.value='';\n"
    "  filt=[...D_CY];renderAll();\n"
    "}"
)
if OLD_RESET in html:
    html = html.replace(OLD_RESET, NEW_RESET, 1)
    print('✓ resetF() thêm reset fMonth')
else:
    print('❌ Không match resetF()')

# ═══════════════════════════════════════════════════════════════
# 9. fetchSalesFromSheet – gọi updateMonthDropdown sau khi load
# ═══════════════════════════════════════════════════════════════
OLD_AFT = "    if(typeof buildFilters==='function') buildFilters();"
NEW_AFT = "    if(typeof buildFilters==='function') buildFilters();\n    updateMonthDropdown();"
if OLD_AFT in html:
    html = html.replace(OLD_AFT, NEW_AFT, 1)
    print('✓ fetchSalesFromSheet gọi updateMonthDropdown sau khi load')
else:
    print('❌ Không match buildFilters() trong fetchSalesFromSheet')

# ═══════════════════════════════════════════════════════════════
# 10. Startup – thêm fetchCNFromSheet
# ═══════════════════════════════════════════════════════════════
OLD_ST = 'fetchSalesFromSheet().then(()=>fetchKPIFromSheet());'
NEW_ST = 'fetchSalesFromSheet().then(()=>{fetchKPIFromSheet();fetchCNFromSheet();});'
if OLD_ST in html:
    html = html.replace(OLD_ST, NEW_ST, 1)
    print('✓ Startup thêm fetchCNFromSheet')
else:
    print('❌ Không match startup')

# ═══════════════════════════════════════════════════════════════
# Save
# ═══════════════════════════════════════════════════════════════
with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f'\n{"="*50}')
print(f'✅ Xong! {orig//1024} KB → {len(html)//1024} KB')
