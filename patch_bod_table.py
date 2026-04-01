#!/usr/bin/env python3
"""Add product group breakdown table to BOD report tab."""
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# ─── 1. Add CSS for the new table ────────────────────────────────────────────
OLD_CSS = '.bod-row-header{background:#f8fafc;padding:10px 16px;font-size:11px;font-weight:700;color:var(--g);border-bottom:1px solid var(--bdr)}'
NEW_CSS = '''.bod-row-header{background:#f8fafc;padding:10px 16px;font-size:11px;font-weight:700;color:var(--g);border-bottom:1px solid var(--bdr)}
.bod-group-table{width:100%;border-collapse:collapse;font-size:12px}
.bod-group-table th{background:#f0f7f2;color:var(--g);font-weight:700;padding:9px 12px;text-align:right;border-bottom:2px solid var(--g);white-space:nowrap}
.bod-group-table th:first-child{text-align:left}
.bod-group-table td{padding:8px 12px;border-bottom:1px solid var(--bdr);text-align:right}
.bod-group-table td:first-child{text-align:left;font-weight:600;color:#333}
.bod-group-table tr:hover td{background:#f8fff8}
.bod-group-table tr.total-row td{background:#f0f7f2;font-weight:700;color:var(--g);border-top:2px solid var(--g)}
.bod-period-tabs{display:flex;gap:6px;padding:10px 16px;background:#f8fafc;border-bottom:1px solid var(--bdr)}
.bod-period-tab{background:#e8f5ee;color:var(--g);border:1px solid #b7dfc8;border-radius:6px;padding:4px 14px;font-size:11px;font-weight:700;cursor:pointer}
.bod-period-tab.active{background:var(--g);color:#fff;border-color:var(--g)}
.tsln-hi{color:#2d9e5f;font-weight:700}
.tsln-md{color:#d69e2e;font-weight:700}
.tsln-lo{color:#e53e3e;font-weight:700}'''
html = html.replace(OLD_CSS, NEW_CSS, 1)
print('✓ CSS added')

# ─── 2. Add HTML section in BOD page ─────────────────────────────────────────
OLD_BOD_END = '''</div>
</div>

<!-- SO SÁNH YOY -->'''

NEW_BOD_SECTION = '''  <!-- CƠ CẤU THEO NHÓM HÀNG -->
  <div class="bod-section">
    <div class="bod-section-title">📦 Cơ cấu Doanh thu &amp; Lợi nhuận theo Nhóm hàng <span id="bodGroupSub"></span></div>
    <div class="bod-period-tabs">
      <button class="bod-period-tab active" onclick="renderBODGroup('month',this)">Tháng hiện tại</button>
      <button class="bod-period-tab" onclick="renderBODGroup('quarter',this)">Quý hiện tại</button>
      <button class="bod-period-tab" onclick="renderBODGroup('year',this)">Cả năm 2026</button>
    </div>
    <div class="tbl-wrap" style="padding:0">
      <table class="bod-group-table">
        <thead><tr>
          <th style="text-align:left;min-width:160px">Nhóm hàng</th>
          <th>Doanh thu</th>
          <th>Lợi nhuận</th>
          <th>TSLN</th>
          <th>Tỷ trọng DT</th>
          <th>Tỷ trọng LN</th>
        </tr></thead>
        <tbody id="bodGroupTbody"></tbody>
      </table>
    </div>
  </div>

</div>
</div>

<!-- SO SÁNH YOY -->'''

html = html.replace(OLD_BOD_END, NEW_BOD_SECTION, 1)
print('✓ BOD group table HTML added')

# ─── 3. Add renderBODGroup function + hook into renderBOD ────────────────────
# Add renderBODGroup function before copyBOD
OLD_COPY_BOD = 'function copyBOD(){'

NEW_GROUP_FUNC = '''// Cache để renderBODGroup dùng lại dữ liệu từ renderBOD
var _bodCache={};

function renderBODGroup(period, tabEl){
  // Cập nhật tab active
  document.querySelectorAll('.bod-period-tab').forEach(t=>t.classList.remove('active'));
  if(tabEl) tabEl.classList.add('active');

  const c=_bodCache;
  if(!c.data2026||!c.data2026.length) return;

  let rows;
  if(period==='day') rows=c.rDay;
  else if(period==='month') rows=c.rMon;
  else if(period==='quarter') rows=c.rQ;
  else rows=c.rY;

  // Gom nhóm theo loaiHang
  const map={};
  rows.forEach(r=>{
    const g=r.loaiHang||'Khác';
    if(!map[g]) map[g]={dt:0,ln:0};
    map[g].dt+=(r.tongThanhTien||0);
    map[g].ln+=(r.tongLoiNhuan||0);
  });

  const totalDT=Object.values(map).reduce((s,v)=>s+v.dt,0);
  const totalLN=Object.values(map).reduce((s,v)=>s+v.ln,0);

  // Sắp xếp theo DT giảm dần
  const sorted=Object.entries(map)
    .map(([g,v])=>({g,dt:v.dt,ln:v.ln,tsln:v.dt>0?v.ln/v.dt:0,wDT:totalDT>0?v.dt/totalDT:0,wLN:totalLN>0?v.ln/totalLN:0}))
    .sort((a,b)=>b.dt-a.dt);

  const fmtPct=v=>(v*100).toFixed(1)+'%';
  const tsClass=v=>v>=0.3?'tsln-hi':v>=0.2?'tsln-md':'tsln-lo';
  const bar=v=>{const p=Math.min(100,v*100).toFixed(1);const c=v>=0.5?'#2d9e5f':v>=0.25?'#d69e2e':'#94a3b8';return `<div style="display:flex;align-items:center;gap:4px"><div style="flex:1;height:6px;background:#e8f0ed;border-radius:3px;overflow:hidden"><div style="width:${p}%;height:100%;background:${c};border-radius:3px"></div></div><span style="font-size:10px;min-width:34px">${p}%</span></div>`;};

  let tb='';
  sorted.forEach((v,i)=>{
    tb+=`<tr>
      <td>${v.g}</td>
      <td style="font-weight:700;color:var(--g)">${fmtB(v.dt)}</td>
      <td>${fmtB(v.ln)}</td>
      <td><span class="${tsClass(v.tsln)}">${fmtPct(v.tsln)}</span></td>
      <td>${bar(v.wDT)}</td>
      <td>${bar(v.wLN)}</td>
    </tr>`;
  });

  // Total row
  const tsln_tot=totalDT>0?totalLN/totalDT:0;
  tb+=`<tr class="total-row">
    <td>TỔNG CỘNG</td>
    <td>${fmtB(totalDT)}</td>
    <td>${fmtB(totalLN)}</td>
    <td><span class="${tsClass(tsln_tot)}">${fmtPct(tsln_tot)}</span></td>
    <td><span style="font-weight:700">100%</span></td>
    <td><span style="font-weight:700">100%</span></td>
  </tr>`;

  document.getElementById('bodGroupTbody').innerHTML=tb||'<tr><td colspan="6" style="text-align:center;color:var(--muted)">Không có dữ liệu</td></tr>';

  const periodLabel=period==='month'?`T${c.lastMonth}/${c.lastYear}`:period==='quarter'?`Q${Math.ceil(c.lastMonth/3)}/${c.lastYear}`:`Năm ${c.lastYear}`;
  const subEl=document.getElementById('bodGroupSub');
  if(subEl) subEl.textContent=periodLabel;
}

function copyBOD(){'''

html = html.replace(OLD_COPY_BOD, NEW_GROUP_FUNC, 1)
print('✓ renderBODGroup function added')

# ─── 4. Cache BOD data + call renderBODGroup at end of renderBOD ─────────────
OLD_BOD_END2 = '''  document.getElementById('bodDayTbody').innerHTML=tb||'<tr><td colspan="5" style="text-align:center;color:var(--muted)">Không có dữ liệu</td></tr>';
}'''

NEW_BOD_END2 = '''  document.getElementById('bodDayTbody').innerHTML=tb||'<tr><td colspan="5" style="text-align:center;color:var(--muted)">Không có dữ liệu</td></tr>';

  // Cache cho renderBODGroup
  _bodCache={data2026,rDay,rMon,rQ,rY,lastMonth,lastYear};
  // Render bảng nhóm hàng (mặc định: tháng hiện tại)
  const activeTab=document.querySelector('.bod-period-tab.active');
  const activePeriod=activeTab?(['month','quarter','year'][Array.from(document.querySelectorAll('.bod-period-tab')).indexOf(activeTab)]):'month';
  renderBODGroup(activePeriod||'month', activeTab);
}'''

html = html.replace(OLD_BOD_END2, NEW_BOD_END2, 1)
print('✓ renderBOD now calls renderBODGroup + caches data')

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f'\nDone! {len(html)//1024} KB')
