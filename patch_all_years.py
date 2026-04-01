#!/usr/bin/env python3
"""Patch dashboard: use all years (2025+2026) across all tabs including SP chua nhap."""
import re, sys
sys.stdout.reconfigure(encoding='utf-8')

SRC = 'index.html'
OUT = 'index.html'

with open(SRC, 'r', encoding='utf-8') as f:
    html = f.read()

original_size = len(html)

# ─── 1. Default year = "Cả 2 năm" ───────────────────────────────────────────
html = html.replace(
    '<option value="2026" selected>2026</option><option value="2025">2025</option><option value="0">Cả 2 năm</option>',
    '<option value="2026">2026</option><option value="2025">2025</option><option value="0" selected>Cả 2 năm</option>'
)
print('✓ Default year → Cả 2 năm')

# ─── 2. D_CY init = D_ALL (all years) ────────────────────────────────────────
html = html.replace(
    'let D_CY=D_ALL.filter(r=>r.nam===2026);',
    'let D_CY=D_ALL;'
)
print('✓ D_CY = D_ALL')

# ─── 3. Date filter: remove hardcoded 2026-01-01 default ──────────────────────
html = html.replace(
    '<input type="date" id="fFrom" value="2026-01-01">',
    '<input type="date" id="fFrom">'
)
print('✓ Date filter default cleared')

# ─── 4. Miss tab "Cả năm (Q1)" → "Toàn kỳ" ──────────────────────────────────
html = html.replace(
    '<option value="year">Cả năm (Q1)</option>',
    '<option value="year">Toàn kỳ</option>'
)
print('✓ Miss tab period label updated')

# ─── 5. Miss tab table header: dynamic (remove hardcoded T1/T2/T3) ────────────
OLD_THEAD = '''        <thead>
          <tr>
            <th class="left" style="width:40px">#</th>
            <th class="left" style="min-width:60px">Mã hàng</th>
            <th class="left" style="min-width:180px">Tên sản phẩm</th>
            <th style="width:100px">Nhóm</th>
            <th style="width:70px">T1</th>
            <th style="width:70px">T2</th>
            <th style="width:70px">T3</th>
            <th style="width:70px">Q1</th>
            <th style="width:80px">Cả năm</th>
            <th style="width:80px">Trạng thái</th>
          </tr>
        </thead>'''

NEW_THEAD = '''        <thead>
          <tr id="missTheadRow">
            <th class="left" style="width:40px">#</th>
            <th class="left" style="min-width:60px">Mã hàng</th>
            <th class="left" style="min-width:180px">Tên sản phẩm</th>
            <th style="width:100px">Nhóm</th>
            <th style="width:70px">T1</th><th style="width:70px">T2</th><th style="width:70px">T3</th>
            <th style="width:70px">Tổng</th>
            <th style="width:80px">Trạng thái</th>
          </tr>
        </thead>'''

html = html.replace(OLD_THEAD, NEW_THEAD)
print('✓ Miss tab table header → dynamic id')

# ─── 6. onYearChange: also update miss tab ────────────────────────────────────
OLD_YEAR = """function onYearChange(){
  const y=parseInt(document.getElementById('fYear').value)||2026;
  D_CY = y===0 ? D_ALL : D_ALL.filter(r=>r.nam===y);
  applyF();
}"""

NEW_YEAR = """function onYearChange(){
  const y=parseInt(document.getElementById('fYear').value);
  D_CY = (!y||y===0) ? D_ALL : D_ALL.filter(r=>r.nam===y);
  // Clear date filter when switching year
  document.getElementById('fFrom').value='';
  document.getElementById('fTo').value='';
  applyF();
  updateMissMonths();
  if(document.getElementById('page-miss').style.display!=='none') renderMissPage();
}"""

html = html.replace(OLD_YEAR, NEW_YEAR)
print('✓ onYearChange updated')

# ─── 7. Replace renderMissPage + add updateMissMonths ─────────────────────────
OLD_RENDER_MISS = """function renderMissPage(){
  const selMonth=parseInt(document.getElementById('mMonth').value)||0;
  const selStore=document.getElementById('mStore').value;
  const allMonths=[1,2,3];

  // Chỉ theo dõi 2 nhóm độc quyền
  const NHOM_THEO_DOI=['NL ĐỘC QUYỀN','VL ĐỘC QUYỀN'];
  const catalog=CATALOG.filter(p=>NHOM_THEO_DOI.includes(p.nhomHang));

  // Lấy SL đã nhập theo cửa hàng + tháng → map: maHang → sl
  function getSoldQty(store, month){
    let rows=D_ALL.filter(r=>r.nam===2026&&NHOM_THEO_DOI.includes(r.loaiHang));
    if(store) rows=rows.filter(r=>r.chiNhanh===store);
    if(month) rows=rows.filter(r=>r.thang===month);
    const map={};
    rows.forEach(r=>{if(r.maHang){if(!map[r.maHang])map[r.maHang]=0;map[r.maHang]+=r.sl;}});
    return map;
  }

  // SL theo từng tháng
  const qtyByMonth={};
  allMonths.forEach(m=>{qtyByMonth[m]=getSoldQty(selStore,m);});

  // Xác định tháng lọc
  const filterMonths=selMonth===0?allMonths:[selMonth];
  const soldInFilter=new Set();
  filterMonths.forEach(m=>{Object.keys(qtyByMonth[m]||{}).forEach(k=>soldInFilter.add(k));});

  const catalogMa=new Set(catalog.map(p=>p.maHang).filter(x=>x));
  const missedInFilter=new Set([...catalogMa].filter(x=>!soldInFilter.has(x)));

  const totalCat=catalog.length;
  const soldCount=[...catalogMa].filter(x=>soldInFilter.has(x)).length;
  const missCount=missedInFilter.size;
  const coverage=totalCat>0?soldCount/totalCat:0;

  // KPI cards
  mk0.innerHTML=totalCat;
  mk1.innerHTML=soldCount;
  mk1s.innerHTML=pct(coverage)+' danh mục đã phủ';
  mk2.innerHTML=missCount;
  mk2s.innerHTML=pct(1-coverage)+' danh mục chưa phủ';
  mk3.innerHTML=pct(coverage);
  mk3.style.color=coverage>=.8?'#2d9e5f':coverage>=.6?'#d69e2e':'#e53e3e';

  // Chart tỷ lệ phủ theo tháng
  const covByMonth=allMonths.map(m=>{
    const sold=new Set(Object.keys(getSoldQty(selStore,m)));
    const n=[...catalogMa].filter(x=>sold.has(x)).length;
    return catalogMa.size>0?n/catalogMa.size*100:0;
  });
  dc('missTrend');
  CH['missTrend']=new Chart(document.getElementById('cMissTrend').getContext('2d'),{
    type:'bar',
    data:{labels:allMonths.map(m=>'Tháng '+m),datasets:[
      {label:'Tỷ lệ phủ (%)',data:covByMonth,backgroundColor:covByMonth.map(v=>v>=80?'#2d9e5f99':v>=60?'#d69e2e99':'#e53e3e99'),borderRadius:6}
    ]},
    options:{responsive:true,maintainAspectRatio:false,
      plugins:{legend:{display:false},datalabels:{anchor:'end',align:'top',formatter:v=>v.toFixed(1)+'%',font:{size:11,weight:'bold'},color:'#333'}},
      scales:{y:{max:100,ticks:{callback:v=>v+'%'},grid:{color:'#f0f0f0'}},x:{grid:{display:false}}}}
  });

  // Chart SP chưa nhập theo nhóm
  const missByCat={};
  catalog.filter(p=>missedInFilter.has(p.maHang)).forEach(p=>{if(!missByCat[p.nhomHang])missByCat[p.nhomHang]=0;missByCat[p.nhomHang]++;});
  const catSorted=Object.entries(missByCat).sort((a,b)=>b[1]-a[1]);
  dc('missCat');
  if(catSorted.length>0){
    CH['missCat']=new Chart(document.getElementById('cMissCat').getContext('2d'),{
      type:'bar',
      data:{labels:catSorted.map(x=>x[0]),datasets:[{data:catSorted.map(x=>x[1]),backgroundColor:'#e53e3e99',borderRadius:5}]},
      options:{responsive:true,maintainAspectRatio:false,
        plugins:{legend:{display:false},datalabels:{anchor:'end',align:'top',formatter:v=>v+' SP',font:{size:10,weight:'bold'},color:'#333'}},
        scales:{y:{ticks:{stepSize:1},grid:{color:'#f0f0f0'}},x:{grid:{display:false},ticks:{font:{size:10}}}}}
    });
  }

  // Bảng: có cửa hàng → tất cả SP (đã + chưa); không có → chỉ SP chưa nhập
  const showAll=!!selStore;
  const periodLabel=selMonth===0?'Toàn Q1/2026':('Tháng '+selMonth+'/2026');
  const storeLabel=selStore||'Tất cả cửa hàng';

  document.getElementById('missTableTitle').textContent=showAll
    ?'Chi tiết nhập hàng – '+storeLabel
    :'Sản phẩm chưa nhập – '+storeLabel;
  document.getElementById('missTableSub').textContent=showAll
    ?periodLabel+' | '+totalCat+' sản phẩm ('+missCount+' chưa nhập, '+soldCount+' đã nhập)'
    :periodLabel+' | '+missCount+' sản phẩm chưa được nhập';

  // Danh sách hiển thị
  const displayList=showAll
    ?[...catalog].sort((a,b)=>{
        const aM=missedInFilter.has(a.maHang)?0:1;
        const bM=missedInFilter.has(b.maHang)?0:1;
        if(aM!==bM)return aM-bM;
        return a.nhomHang.localeCompare(b.nhomHang);
      })
    :catalog.filter(p=>missedInFilter.has(p.maHang)).sort((a,b)=>a.nhomHang.localeCompare(b.nhomHang));

  const nhomColor={'NL ĐỘC QUYỀN':'tag-g','VL ĐỘC QUYỀN':'tag-b'};
  const fmtQ=q=>q>0?('<span class="qty-cell">'+fmt(q)+'</span>'):'<span class="zero-cell">–</span>';
  let tb='';
  displayList.forEach((p,i)=>{
    const q1=qtyByMonth[1][p.maHang]||0;
    const q2=qtyByMonth[2][p.maHang]||0;
    const q3=qtyByMonth[3][p.maHang]||0;
    const qQ1=q1+q2+q3;
    const isMissed=missedInFilter.has(p.maHang);
    const tagCls=nhomColor[p.nhomHang]||'tag-o';
    const rowBg=isMissed?'background:#fff8f8':''
    const statusCell=isMissed
      ?'<span class="tag tag-r" style="font-size:10px">Chưa nhập</span>'
      :'<span class="tag tag-g" style="font-size:10px">Đã nhập</span>';
    tb+=`<tr style="${rowBg}">
      <td class="rk">#${i+1}</td>
      <td style="font-family:monospace;font-size:11px">${p.maHang||'–'}</td>
      <td style="font-weight:600;text-align:left">${p.tenHang}</td>
      <td><span class="tag ${tagCls}" style="font-size:10px">${p.nhomHang}</span></td>
      <td>${fmtQ(q1)}</td>
      <td>${fmtQ(q2)}</td>
      <td>${fmtQ(q3)}</td>
      <td style="background:#f8fafc;font-weight:700">${qQ1>0?('<span style="color:var(--g);font-weight:700">'+fmt(qQ1)+'</span>'):'<span class="zero-cell">–</span>'}</td>
      <td style="background:#f8fafc">${qQ1>0?('<span style="color:#3182ce;font-weight:700">'+fmt(qQ1)+'</span>'):'<span class="zero-cell">–</span>'}</td>
      <td>${statusCell}</td>
    </tr>`;
  });
  const emptyMsg=showAll?'✅ Tất cả sản phẩm đã được nhập!':'✅ Tất cả sản phẩm đã được nhập trong kỳ này!';
  document.getElementById('missTbody').innerHTML=tb||`<tr><td colspan="10" style="text-align:center;padding:20px;color:#2d9e5f;font-weight:600">${emptyMsg}</td></tr>`;
}"""

NEW_RENDER_MISS = """// Cập nhật dropdown tháng cho tab SP chưa nhập (dynamic từ D_CY)
function updateMissMonths(){
  const NHOM=['NL ĐỘC QUYỀN','VL ĐỘC QUYỀN'];
  const months=[...new Set(D_CY.filter(r=>NHOM.includes(r.loaiHang)).map(r=>r.thang))].sort((a,b)=>a-b);
  const sel=document.getElementById('mMonth');
  const cur=sel.value;
  sel.innerHTML='<option value="0">Tất cả tháng</option>';
  months.forEach(m=>{
    const o=document.createElement('option');
    o.value=m; o.textContent='Tháng '+m;
    if(String(m)===cur) o.selected=true;
    sel.appendChild(o);
  });
}

function renderMissPage(){
  const selMonth=parseInt(document.getElementById('mMonth').value)||0;
  const selStore=document.getElementById('mStore').value;
  const NHOM_THEO_DOI=['NL ĐỘC QUYỀN','VL ĐỘC QUYỀN'];
  const catalog=CATALOG.filter(p=>NHOM_THEO_DOI.includes(p.nhomHang));

  // Tháng động từ D_CY
  const allMonths=[...new Set(D_CY.filter(r=>NHOM_THEO_DOI.includes(r.loaiHang)).map(r=>r.thang))].sort((a,b)=>a-b);
  if(!allMonths.length){[1,2,3].forEach(m=>allMonths.push(m));}

  // Lấy SL đã nhập theo cửa hàng + tháng → map: maHang → sl (dùng D_CY)
  function getSoldQty(store, month){
    let rows=D_CY.filter(r=>NHOM_THEO_DOI.includes(r.loaiHang));
    if(store) rows=rows.filter(r=>r.chiNhanh===store);
    if(month) rows=rows.filter(r=>r.thang===month);
    const map={};
    rows.forEach(r=>{if(r.maHang){if(!map[r.maHang])map[r.maHang]=0;map[r.maHang]+=r.sl;}});
    return map;
  }

  const qtyByMonth={};
  allMonths.forEach(m=>{qtyByMonth[m]=getSoldQty(selStore,m);});

  const filterMonths=selMonth===0?allMonths:[selMonth];
  const soldInFilter=new Set();
  filterMonths.forEach(m=>{Object.keys(qtyByMonth[m]||{}).forEach(k=>soldInFilter.add(k));});

  const catalogMa=new Set(catalog.map(p=>p.maHang).filter(x=>x));
  const missedInFilter=new Set([...catalogMa].filter(x=>!soldInFilter.has(x)));

  const totalCat=catalog.length;
  const soldCount=[...catalogMa].filter(x=>soldInFilter.has(x)).length;
  const missCount=missedInFilter.size;
  const coverage=totalCat>0?soldCount/totalCat:0;

  // KPI cards
  mk0.innerHTML=totalCat;
  mk1.innerHTML=soldCount;
  mk1s.innerHTML=pct(coverage)+' danh mục đã phủ';
  mk2.innerHTML=missCount;
  mk2s.innerHTML=pct(1-coverage)+' danh mục chưa phủ';
  mk3.innerHTML=pct(coverage);
  mk3.style.color=coverage>=.8?'#2d9e5f':coverage>=.6?'#d69e2e':'#e53e3e';

  // Chart tỷ lệ phủ theo tháng (dynamic)
  const covByMonth=allMonths.map(m=>{
    const sold=new Set(Object.keys(getSoldQty(selStore,m)));
    const n=[...catalogMa].filter(x=>sold.has(x)).length;
    return catalogMa.size>0?n/catalogMa.size*100:0;
  });
  dc('missTrend');
  CH['missTrend']=new Chart(document.getElementById('cMissTrend').getContext('2d'),{
    type:'bar',
    data:{labels:allMonths.map(m=>'T'+m),datasets:[
      {label:'Tỷ lệ phủ (%)',data:covByMonth,backgroundColor:covByMonth.map(v=>v>=80?'#2d9e5f99':v>=60?'#d69e2e99':'#e53e3e99'),borderRadius:6}
    ]},
    options:{responsive:true,maintainAspectRatio:false,
      plugins:{legend:{display:false},datalabels:{anchor:'end',align:'top',formatter:v=>v.toFixed(1)+'%',font:{size:11,weight:'bold'},color:'#333'}},
      scales:{y:{max:100,ticks:{callback:v=>v+'%'},grid:{color:'#f0f0f0'}},x:{grid:{display:false}}}}
  });

  // Chart SP chưa nhập theo nhóm
  const missByCat={};
  catalog.filter(p=>missedInFilter.has(p.maHang)).forEach(p=>{if(!missByCat[p.nhomHang])missByCat[p.nhomHang]=0;missByCat[p.nhomHang]++;});
  const catSorted=Object.entries(missByCat).sort((a,b)=>b[1]-a[1]);
  dc('missCat');
  if(catSorted.length>0){
    CH['missCat']=new Chart(document.getElementById('cMissCat').getContext('2d'),{
      type:'bar',
      data:{labels:catSorted.map(x=>x[0]),datasets:[{data:catSorted.map(x=>x[1]),backgroundColor:'#e53e3e99',borderRadius:5}]},
      options:{responsive:true,maintainAspectRatio:false,
        plugins:{legend:{display:false},datalabels:{anchor:'end',align:'top',formatter:v=>v+' SP',font:{size:10,weight:'bold'},color:'#333'}},
        scales:{y:{ticks:{stepSize:1},grid:{color:'#f0f0f0'}},x:{grid:{display:false},ticks:{font:{size:10}}}}}
    });
  }

  // Cập nhật header bảng động theo số tháng
  const theadRow=document.getElementById('missTheadRow');
  if(theadRow){
    const mthCols=allMonths.map(m=>`<th style="width:60px">T${m}</th>`).join('');
    theadRow.innerHTML=`<th class="left" style="width:40px">#</th><th class="left" style="min-width:60px">Mã hàng</th><th class="left" style="min-width:180px">Tên sản phẩm</th><th style="width:100px">Nhóm</th>${mthCols}<th style="width:70px">Tổng</th><th style="width:80px">Trạng thái</th>`;
  }

  const showAll=!!selStore;
  const yVal=parseInt(document.getElementById('fYear').value);
  const yLabel=(!yVal||yVal===0)?'2025-2026':String(yVal);
  const periodLabel=selMonth===0?('Toàn kỳ '+yLabel):('Tháng '+selMonth+'/'+yLabel);
  const storeLabel=selStore||'Tất cả cửa hàng';

  document.getElementById('missTableTitle').textContent=showAll
    ?'Chi tiết nhập hàng – '+storeLabel
    :'Sản phẩm chưa nhập – '+storeLabel;
  document.getElementById('missTableSub').textContent=showAll
    ?periodLabel+' | '+totalCat+' sản phẩm ('+missCount+' chưa nhập, '+soldCount+' đã nhập)'
    :periodLabel+' | '+missCount+' sản phẩm chưa được nhập';

  const displayList=showAll
    ?[...catalog].sort((a,b)=>{
        const aM=missedInFilter.has(a.maHang)?0:1;
        const bM=missedInFilter.has(b.maHang)?0:1;
        if(aM!==bM)return aM-bM;
        return a.nhomHang.localeCompare(b.nhomHang);
      })
    :catalog.filter(p=>missedInFilter.has(p.maHang)).sort((a,b)=>a.nhomHang.localeCompare(b.nhomHang));

  const nhomColor={'NL ĐỘC QUYỀN':'tag-g','VL ĐỘC QUYỀN':'tag-b'};
  const fmtQ=q=>q>0?('<span class="qty-cell">'+fmt(q)+'</span>'):'<span class="zero-cell">–</span>';
  const colCount=4+allMonths.length+2;
  let tb='';
  displayList.forEach((p,i)=>{
    const mQtys=allMonths.map(m=>qtyByMonth[m][p.maHang]||0);
    const qTot=mQtys.reduce((s,q)=>s+q,0);
    const isMissed=missedInFilter.has(p.maHang);
    const tagCls=nhomColor[p.nhomHang]||'tag-o';
    const rowBg=isMissed?'background:#fff8f8':'';
    const statusCell=isMissed
      ?'<span class="tag tag-r" style="font-size:10px">Chưa nhập</span>'
      :'<span class="tag tag-g" style="font-size:10px">Đã nhập</span>';
    const mCells=mQtys.map(q=>`<td>${fmtQ(q)}</td>`).join('');
    tb+=`<tr style="${rowBg}">
      <td class="rk">#${i+1}</td>
      <td style="font-family:monospace;font-size:11px">${p.maHang||'–'}</td>
      <td style="font-weight:600;text-align:left">${p.tenHang}</td>
      <td><span class="tag ${tagCls}" style="font-size:10px">${p.nhomHang}</span></td>
      ${mCells}
      <td style="background:#f8fafc;font-weight:700">${qTot>0?('<span style="color:var(--g);font-weight:700">'+fmt(qTot)+'</span>'):'<span class="zero-cell">–</span>'}</td>
      <td style="background:#f8fafc">${statusCell}</td>
    </tr>`;
  });
  const emptyMsg=showAll?'✅ Tất cả sản phẩm đã được nhập!':'✅ Tất cả sản phẩm đã được nhập trong kỳ này!';
  document.getElementById('missTbody').innerHTML=tb||`<tr><td colspan="${colCount}" style="text-align:center;padding:20px;color:#2d9e5f;font-weight:600">${emptyMsg}</td></tr>`;
}"""

if OLD_RENDER_MISS in html:
    html = html.replace(OLD_RENDER_MISS, NEW_RENDER_MISS)
    print('✓ renderMissPage + updateMissMonths replaced')
else:
    print('✗ ERROR: Could not find renderMissPage to replace!')
    sys.exit(1)

# ─── 8. Call updateMissMonths at init (after initFilters) ─────────────────────
# Find initFilters call and add updateMissMonths after it
if 'initFilters();' in html:
    html = html.replace(
        'initFilters();',
        'initFilters(); updateMissMonths();'
    )
    print('✓ updateMissMonths called at init')
else:
    print('⚠ initFilters not found standalone, skipping')

# ─── 9. Also sync mStore to include all-years stores ─────────────────────────
# The mStore dropdown is populated with stores from D_CY, which now = D_ALL by default
# initFilters already populates both fStore and mStore from D_CY.forEach — no change needed
# since D_CY is now D_ALL by default.

# ─── Write output ─────────────────────────────────────────────────────────────
with open(OUT, 'w', encoding='utf-8') as f:
    f.write(html)

new_size = len(html)
print(f'\nDone! {new_size//1024} KB (was {original_size//1024} KB)')
