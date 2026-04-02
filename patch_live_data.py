#!/usr/bin/env python3
"""
Patch dashboard: tải dữ liệu bán hàng live từ Google Sheets thay vì JSON nhúng 4MB.
Sheet ID: 1DR4q16Whx7QFlw3KIPbtR-6RpbDpwQ1MeOyT3faHnu4
Tab: "2025" (8869 dòng) + "2026" (2250 dòng) = 11119 dòng tổng

Cột thực tế trong Sheet:
  PHÂN LOẠI HÀNG HOÁ | PHÂN LOẠI CN | PL BÁO CÁO | THÁNG | NGÀY | CHI NHÁNH |
  MÃ HÀNG | SẢN PHẨM | ĐƠN VỊ | SL | ĐƠN GIÁ | THÀNH TIỀN | TỔNG GIẢM GIÁ |
  TỔNG THÀNH TIỀN | TỔNG GIÁ VỐN | TỔNG GIÁ TRỊ LỢI NHUẬN | TSLN TRÊN DT | TSLN TRÊN GIÁ VỐN

Định dạng số VN: 1.600.000 (dấu . = nghìn), 13,75% (dấu , = thập phân, % ÷ 100)
Định dạng ngày: 02/01/2026 (dd/MM/yyyy → yyyy-MM-dd)
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

SHEET_ID = '1DR4q16Whx7QFlw3KIPbtR-6RpbDpwQ1MeOyT3faHnu4'

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

orig_size = len(html)
print(f'File gốc: {orig_size//1024} KB')

# ─── 1. Xoá const D=[...huge JSON...] → const D=[] ───────────────────────────
d_start = html.find('const D=[')
if d_start < 0:
    print('❌ Không tìm thấy const D=[ (có thể đã patch rồi)')
    sys.exit(1)
d_end = html.find('];', d_start) + 2
old_kb = (d_end - d_start) // 1024
html = html[:d_start] + 'const D=[]' + html[d_end:]
print(f'✓ Đã xoá {old_kb} KB JSON nhúng')

# ─── 2. CSS cho thanh trạng thái ─────────────────────────────────────────────
OLD_CSS = ':root{--g:#1a6b3c;'
NEW_CSS = '''.data-status-bar{background:#f0f7f2;border-bottom:1px solid #b7dfc8;padding:5px 24px;font-size:11px;display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.ds-btn{background:#3182ce;color:#fff;border:none;border-radius:4px;padding:2px 10px;font-size:10px;font-weight:700;cursor:pointer;transition:opacity .2s}
.ds-btn:hover{opacity:.82}
'''
if OLD_CSS in html:
    html = html.replace(OLD_CSS, NEW_CSS + OLD_CSS, 1)
    print('✓ CSS thanh trạng thái đã thêm')
else:
    print('⚠ Không thêm được CSS (không tìm thấy :root)')

# ─── 3. Thanh trạng thái dữ liệu trước .tabs ────────────────────────────────
OLD_TABS = '<div class="tabs">'
STATUS_BAR_HTML = '''<div class="data-status-bar">
  <span style="color:#1a6b3c;font-weight:700">📊 Dữ liệu live:</span>
  <span id="salesSheetStatus" style="color:#3182ce;font-weight:600">⏳ Đang kết nối Google Sheets...</span>
  <button class="ds-btn" onclick="fetchSalesFromSheet()">🔄 Tải lại ngay</button>
</div>
<div class="tabs">'''
if html.count(OLD_TABS) >= 1:
    html = html.replace(OLD_TABS, STATUS_BAR_HTML, 1)
    print('✓ Thanh trạng thái đã thêm trước .tabs')
else:
    print('⚠ Không tìm thấy <div class="tabs">')

# ─── 4. Inject toàn bộ JS trước function applyF() ────────────────────────────
SALES_JS = r"""
// ===== LIVE SALES DATA – GOOGLE SHEETS =====
const SALES_SHEET_ID = '""" + SHEET_ID + r"""';
const SALES_YEARS = [2025, 2026];

// Mapping cột thực tế trong Sheet → field JS
const SALES_COL_MAP = {
  'PHÂN LOẠI HÀNG HOÁ':      'loaiHang',   // VL ĐỘC QUYỀN, NL ĐỘC QUYỀN...
  'PL BÁO CÁO':              'brand',       // PHÚC TEA / THE HOA
  'THÁNG':                   'thang',       // 1–12 (số)
  'NGÀY':                    'ngay',        // dd/MM/yyyy → yyyy-MM-dd
  'CHI NHÁNH':               'chiNhanh',
  'MÃ HÀNG':                 'maHang',
  'SẢN PHẨM':                'sanPham',
  'SL':                      'sl',
  'THÀNH TIỀN':              'thanhTien',
  'TỔNG GIẢM GIÁ':           'tongGiamGia',
  'TỔNG THÀNH TIỀN':         'tongThanhTien',
  'TỔNG GIÁ VỐN':            'tongGiaVon',
  'TỔNG GIÁ TRỊ LỢI NHUẬN': 'tongLoiNhuan',
  'TSLN TRÊN DT':            'tsln'          // "13,75%" → 0.1375
};
const _SALES_NUM = new Set(['thang','sl','thanhTien','tongGiamGia','tongThanhTien','tongGiaVon','tongLoiNhuan','tsln']);

/** Chuyển số định dạng VN: "1.600.000" → 1600000, "13,75%" → 0.1375 */
function parseSalesNum(s){
  if(!s||typeof s!=='string') return NaN;
  const t=s.trim();
  if(!t||t==='-'||t==='NaN'||t==='#N/A'||t==='#VALUE!') return NaN;
  const isPct=t.includes('%');
  // Xoá %, khoảng trắng; dấu . (nghìn) xoá đi; dấu , (thập phân) → .
  const clean=t.replace(/%/g,'').replace(/\s/g,'').replace(/\./g,'').replace(/,/g,'.');
  const n=parseFloat(clean);
  if(isNaN(n)) return NaN;
  return isPct ? n/100 : n;
}

/** Chuyển dd/MM/yyyy → yyyy-MM-dd (cho filter ngày) */
function parseSalesDate(s){
  if(!s) return '';
  const m=s.trim().match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})/);
  if(m) return `${m[3]}-${m[2].padStart(2,'0')}-${m[1].padStart(2,'0')}`;
  return s; // fallback: trả nguyên bản
}

/** CSV parser hỗ trợ ngoặc kép */
function parseSalesCSV(text){
  const allRows=[];
  const lines=text.split('\n');
  for(let li=0;li<lines.length;li++){
    const cols=[];let cell='';let q=false;
    const line=lines[li];
    for(let i=0;i<line.length;i++){
      const ch=line[i];
      if(ch==='"'){q=!q;}
      else if(ch===','&&!q){cols.push(cell.trim().replace(/^"|"$/g,''));cell='';}
      else{cell+=ch;}
    }
    cols.push(cell.trim().replace(/^"|"$/g,''));
    allRows.push(cols);
  }
  return allRows;
}

async function fetchSalesFromSheet(){
  const statusEl=document.getElementById('salesSheetStatus');
  if(statusEl){statusEl.textContent='⏳ Đang tải từ Google Sheets...';statusEl.style.color='#3182ce';}

  try{
    const allData=[];
    for(const year of SALES_YEARS){
      const url=`https://docs.google.com/spreadsheets/d/${SALES_SHEET_ID}/gviz/tq?tqx=out:csv&sheet=${year}`;
      let resp;
      try{ resp=await fetch(url,{cache:'no-store'}); }
      catch(fe){ console.warn(`fetchSales ${year}:`,fe); continue; }

      if(!resp.ok){
        if(resp.status===400){console.info(`Tab ${year} không tồn tại, bỏ qua`);continue;}
        throw new Error(`HTTP ${resp.status} (năm ${year})`);
      }
      const text=await resp.text();
      if(!text||text.trim().startsWith('<'))
        throw new Error(`Sheet chưa chia sẻ public (tab ${year})`);

      const rows=parseSalesCSV(text);
      if(rows.length<2){console.info(`Tab ${year}: rỗng`);continue;}

      // Map header
      const headers=rows[0].map(h=>SALES_COL_MAP[h.trim()]||null);
      if(!headers.some(Boolean)){console.warn(`Tab ${year}: không nhận ra cột`,rows[0]);continue;}

      let cnt=0;
      for(let i=1;i<rows.length;i++){
        const r=rows[i];
        if(!r||r.every(c=>!c)) continue;
        const obj={nam:year};
        headers.forEach((field,j)=>{
          if(!field) return;
          const raw=(r[j]||'').trim();
          if(field==='ngay'){
            obj.ngay=parseSalesDate(raw);
          } else if(_SALES_NUM.has(field)){
            obj[field]=parseSalesNum(raw);
          } else {
            obj[field]=raw||null;
          }
        });
        if(obj.maHang){allData.push(obj);cnt++;}
      }
      console.info(`Tab ${year}: ${cnt} dòng`);
    }

    if(allData.length===0) throw new Error('Không có dữ liệu');

    // Cập nhật D_ALL in-place (const D_ALL=D nên cùng tham chiếu)
    D_ALL.length=0;
    allData.forEach(r=>D_ALL.push(r));

    // Re-apply bộ lọc năm
    const y=parseInt((document.getElementById('fYear')||{}).value||'0');
    D_CY=(!y||y===0)?D_ALL:D_ALL.filter(r=>r.nam===y);

    // Cập nhật dropdown Cửa hàng + Danh mục nếu có
    if(typeof buildFilters==='function') buildFilters();

    // Re-render toàn bộ dashboard
    applyF();
    if(typeof updateMissMonths==='function') updateMissMonths();
    const ap=document.querySelector('.page.on');
    if(ap){
      if(ap.id==='page-miss'&&typeof renderMissPage==='function') renderMissPage();
      if(ap.id==='page-bod'&&typeof renderBOD==='function') renderBOD();
    }

    const now=new Date().toLocaleString('vi-VN');
    if(statusEl){
      statusEl.innerHTML=`✅ Live · <b>${allData.length.toLocaleString('vi-VN')}</b> dòng · ${now}`;
      statusEl.style.color='#1a6b3c';
    }
  }catch(e){
    console.error('fetchSalesFromSheet:',e);
    if(statusEl){
      statusEl.innerHTML=`⚠️ <b>Lỗi:</b> ${e.message} — kiểm tra Sheet đã chia sẻ public chưa?`;
      statusEl.style.color='#e53e3e';
    }
  }
}

// Tự động tải lại mỗi 5 phút
setInterval(fetchSalesFromSheet, 5*60*1000);

"""

TARGET = 'function applyF(){'
if TARGET not in html:
    print('❌ Không tìm thấy function applyF()')
    sys.exit(1)
html = html.replace(TARGET, SALES_JS + TARGET, 1)
print('✓ fetchSalesFromSheet + parseSalesNum/Date/CSV đã inject')

# ─── 5. Cập nhật startup ─────────────────────────────────────────────────────
old_init = 'applyF();\nfetchKPIFromSheet();'
new_init = 'applyF();\nfetchSalesFromSheet().then(()=>fetchKPIFromSheet());'
if old_init in html:
    html = html.replace(old_init, new_init, 1)
    print('✓ Startup: fetchSalesFromSheet().then(KPI)')
else:
    # fallback tìm kiếu khác
    for pat in ['applyF(); fetchKPIFromSheet();', 'applyF();fetchKPIFromSheet();']:
        if pat in html:
            html = html.replace(pat, 'applyF(); fetchSalesFromSheet().then(()=>fetchKPIFromSheet());', 1)
            print(f'✓ Startup (fallback): done')
            break
    else:
        print('⚠ Không cập nhật được startup – tìm thủ công và thêm fetchSalesFromSheet()')

# ─── Save ─────────────────────────────────────────────────────────────────────
with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

new_size = len(html)
saved = orig_size - new_size
print(f'\n{"="*52}')
print(f'✅ Hoàn tất!')
print(f'   {orig_size//1024} KB → {new_size//1024} KB  (tiết kiệm {saved//1024} KB, {round(saved/orig_size*100)}%)')
print(f'   Sheet: https://docs.google.com/spreadsheets/d/{SHEET_ID}')
print(f'{"="*52}')
