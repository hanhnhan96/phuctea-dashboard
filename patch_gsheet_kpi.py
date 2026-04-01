#!/usr/bin/env python3
"""
Patch dashboard: connect KPI tab to Google Sheet "MỤC TIÊU NĂM 2026"
Sheet: https://docs.google.com/spreadsheets/d/1Cj3XaLVCvvUKwFqv2fUippXhP2zfX_8rFhlOClIADc4
GID: 1945783557

Sheet structure:
  Col A = labels, B = TỔNG, C..N = months 1..12
  Row 3 (idx 2): DT HT Mục tiêu → ht_kh
  Row 4 (idx 3): Tỷ lệ DT BH/HT % → tl_kh
  Row 6 (idx 5): DT HT KQ nhập tay → ht_tt
  Row 11 (idx 10): CN Kế hoạch → cn_kh
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# ─── 1. Add Sheet status bar to KPI tab ──────────────────────────────────────
OLD_SAVE_BTN = '''      <div style="display:flex;align-items:center;gap:8px">
        <button class="save-btn" onclick="saveKPI()">💾 Lưu dữ liệu</button>
        <span style="font-size:11px;color:var(--muted)" id="saveHint"></span>
      </div>'''

NEW_SAVE_BTN = '''      <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
        <button class="save-btn" onclick="saveKPI()">💾 Lưu dữ liệu</button>
        <button class="save-btn" style="background:#3182ce" onclick="fetchKPIFromSheet()">🔄 Đồng bộ từ Sheet</button>
        <span id="kpiSheetStatus" style="font-size:11px;color:#3182ce;font-weight:600">⏳ Đang kết nối Google Sheet...</span>
        <span style="font-size:11px;color:var(--muted)" id="saveHint"></span>
      </div>'''

if OLD_SAVE_BTN in html:
    html = html.replace(OLD_SAVE_BTN, NEW_SAVE_BTN)
    print('✓ Sheet status bar added')
else:
    print('✗ Could not find save button area')

# ─── 2. Add CSS for sheet-synced fields ──────────────────────────────────────
OLD_CSS_MARK = ':root{--g:#1a6b3c;'
NEW_CSS = '''.kpi-sheet-field{background:#e6f0ff!important;color:#1a4a8a!important;border:1px solid #3182ce!important;cursor:default!important;font-style:italic}
.kpi-sheet-field::placeholder{color:#3182ce}
'''
html = html.replace(OLD_CSS_MARK, NEW_CSS + OLD_CSS_MARK, 1)
print('✓ CSS for sheet fields added')

# ─── 3. Add saveKPI / loadKPI / recalcLNHT / fetchKPIFromSheet before recalcKPI ──
NEW_FUNCTIONS = '''
// ===== KPI SAVE / LOAD (localStorage cho các trường nhập tay) =====
function saveKPI(){
  const ids=['tsln_kh','cn_tt'];
  const data={};
  for(let m=1;m<=12;m++){
    ids.forEach(id=>{
      const el=document.getElementById(id+'_'+m);
      if(el&&el.value) data[id+'_'+m]=el.value;
    });
  }
  localStorage.setItem(KPI_KEY,JSON.stringify(data));
  const h=document.getElementById('saveHint');
  if(h){h.textContent='✅ Đã lưu lúc '+new Date().toLocaleTimeString('vi-VN');setTimeout(()=>{h.textContent='';},3000);}
}

function loadKPI(){
  try{
    const data=JSON.parse(localStorage.getItem(KPI_KEY)||'{}');
    Object.keys(data).forEach(k=>{
      const el=document.getElementById(k);
      if(el&&!el.readOnly) el.value=data[k];
    });
  }catch(e){}
}

function recalcLNHT(){
  // Tính tổng LN/DT tổng quan — dùng trong renderKPI overview
}

// ===== GOOGLE SHEET KPI =====
const GSHEET_ID='1Cj3XaLVCvvUKwFqv2fUippXhP2zfX_8rFhlOClIADc4';
const GSHEET_GID='1945783557';
let _sheetLoaded=false;

function parseViNum(s){
  if(!s||typeof s!=='string') return null;
  // Loại bỏ dấu % và khoảng trắng, xử lý số VN (. = hàng nghìn)
  const clean=s.replace(/%/g,'').replace(/\\s/g,'').replace(/\./g,'').replace(/,/g,'.');
  const n=parseFloat(clean);
  return isNaN(n)?null:n;
}

function parseSheetCSV(text){
  // Parse CSV có thể có dấu ngoặc kép
  const rows=text.split('\\n').map(row=>{
    const cols=[];let cur='',inQ=false;
    for(let i=0;i<row.length;i++){
      if(row[i]==='"'){inQ=!inQ;}
      else if(row[i]===','&&!inQ){cols.push(cur.trim());cur='';}
      else{cur+=row[i];}
    }
    cols.push(cur.trim());
    return cols;
  });
  return rows;
}

async function fetchKPIFromSheet(){
  const statusEl=document.getElementById('kpiSheetStatus');
  if(statusEl) statusEl.textContent='⏳ Đang tải từ Google Sheet...';

  // Thử gviz endpoint (yêu cầu "Anyone with link")
  const url=`https://docs.google.com/spreadsheets/d/${GSHEET_ID}/gviz/tq?tqx=out:csv&gid=${GSHEET_GID}`;

  try{
    const resp=await fetch(url,{cache:'no-store'});
    if(!resp.ok) throw new Error('HTTP '+resp.status+' — Sheet chưa được chia sẻ public');
    const text=await resp.text();
    applySheetKPI(parseSheetCSV(text));
    _sheetLoaded=true;
    const now=new Date().toLocaleString('vi-VN');
    if(statusEl) statusEl.textContent='🔗 Đồng bộ từ Google Sheet lúc '+now;
    if(document.getElementById('page-kpi')&&document.getElementById('page-kpi').classList.contains('on')){
      recalcKPI();
    }
  }catch(e){
    if(statusEl) statusEl.innerHTML='⚠️ <b>Chưa kết nối được Sheet.</b> Vui lòng: <b>Tệp → Chia sẻ → Xuất bản lên web</b> rồi bấm 🔄. ('+e.message+')';
    console.warn('fetchKPIFromSheet:',e);
  }
}

function applySheetKPI(rows){
  // rows[2] = Row 3: DT HT Mục tiêu → ht_kh
  // rows[3] = Row 4: Tỷ lệ DT BH/HT % → tl_kh
  // rows[5] = Row 6: DT HT KQ nhập tay → ht_tt
  // rows[10] = Row 11: CN Kế hoạch → cn_kh
  // Col index: B=1(TỔNG), C=2(T1), D=3(T2), ..., N=13(T12)

  const R_HT_KH=rows[2]||[];
  const R_TL_KH=rows[3]||[];
  const R_HT_TT=rows[5]||[];
  const R_CN_KH=rows[10]||[];

  for(let m=1;m<=12;m++){
    const ci=m+1; // column index (B=1, C=2=T1, ...)
    setSheetField('ht_kh_'+m, R_HT_KH[ci]);
    setSheetField('tl_kh_'+m, R_TL_KH[ci]);
    setSheetField('ht_tt_'+m, R_HT_TT[ci]);
    setSheetField('cn_kh_'+m, R_CN_KH[ci]);
  }
}

function setSheetField(id, rawVal){
  const el=document.getElementById(id);
  if(!el) return;
  const n=parseViNum(rawVal);
  if(n!==null){
    el.value=n;
    el.readOnly=true;
    el.classList.add('kpi-sheet-field');
    el.title='🔗 Lấy từ Google Sheet';
  } else {
    el.value='';
    el.readOnly=false;
    el.classList.remove('kpi-sheet-field');
  }
}

// Auto-refresh mỗi 5 phút
setInterval(fetchKPIFromSheet, 5*60*1000);

'''

# Insert before recalcKPI function
OLD_RECALC = 'function recalcKPI(){'
if OLD_RECALC in html:
    html = html.replace(OLD_RECALC, NEW_FUNCTIONS + OLD_RECALC, 1)
    print('✓ saveKPI / loadKPI / fetchKPIFromSheet inserted')
else:
    print('✗ Could not find recalcKPI to insert before')

# ─── 4. Call fetchKPIFromSheet in showTab kpi ─────────────────────────────────
html = html.replace(
    "if(name==='kpi'){loadKPI();recalcKPI();}",
    "if(name==='kpi'){loadKPI();fetchKPIFromSheet().then(()=>recalcKPI());}",
)
print('✓ showTab kpi → fetchKPIFromSheet first')

# ─── 5. Call fetchKPIFromSheet on startup (after applyF) ─────────────────────
html = html.replace(
    '// ===== KHỞI TẠO RENDER =====\napplyF();',
    '// ===== KHỞI TẠO RENDER =====\napplyF();\nfetchKPIFromSheet();'
)
print('✓ fetchKPIFromSheet called on startup')

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f'\nDone! {len(html)//1024} KB')
print('\n👉 BƯỚC TIẾP THEO — Bạn cần làm:')
print('   1. Mở Google Sheet')
print('   2. Tệp → Chia sẻ → Xuất bản lên web')
print('   3. Chọn sheet "MỤC TIÊU NĂM 2026" → Xuất bản')
print('   Hoặc: Nút Chia sẻ → Đổi thành "Bất kỳ ai có đường liên kết" → Người xem')
