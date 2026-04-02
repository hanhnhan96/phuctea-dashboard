#!/usr/bin/env python3
"""
Patch BOD:
1. Cache dt_kh / ln_kh từ recalcKPI vào _kpiCache để BOD đọc được
2. Update getKH() dùng _kpiCache trước
3. Thêm date picker "Báo cáo đến ngày" vào BOD header
4. renderBOD filter dữ liệu theo ngày chọn (thay vì luôn lấy ngày cuối)
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

orig = len(html)

# ═══════════════════════════════════════════════════════════════
# 1. Thêm let _kpiCache = {}; trước function applyF()
# ═══════════════════════════════════════════════════════════════
TARGET_BEFORE_APPLYF = 'function updateBadge(){'
if TARGET_BEFORE_APPLYF in html:
    html = html.replace(
        TARGET_BEFORE_APPLYF,
        'let _kpiCache = {};\n\n' + TARGET_BEFORE_APPLYF,
        1
    )
    print('✓ Thêm _kpiCache global')
else:
    print('❌ Không tìm thấy updateBadge để chèn _kpiCache')

# ═══════════════════════════════════════════════════════════════
# 2. Cache dt_kh trong section 1 của recalcKPI (sau khi tính dt_kh)
# ═══════════════════════════════════════════════════════════════
OLD_DT_KH = (
    "    var dt_kh = (ht_kh!==null&&tl_kh!==null) ? ht_kh*tl_kh/100 : null;\n"
    "    // Tỷ lệ TT = DT BH TT / DT HT TT"
)
NEW_DT_KH = (
    "    var dt_kh = (ht_kh!==null&&tl_kh!==null) ? ht_kh*tl_kh/100 : null;\n"
    "    _kpiCache['dt_kh_'+m]=dt_kh;  // để renderBOD đọc\n"
    "    // Tỷ lệ TT = DT BH TT / DT HT TT"
)
if OLD_DT_KH in html:
    html = html.replace(OLD_DT_KH, NEW_DT_KH, 1)
    print('✓ Cache dt_kh trong recalcKPI section 1')
else:
    print('❌ Không match dt_kh calc')

# ═══════════════════════════════════════════════════════════════
# 3. Cache ln_kh trong section 3 (dt_kh*tsln_kh/100)
# ═══════════════════════════════════════════════════════════════
OLD_TSLN = (
    "    var tsln_kh=gV('tsln_kh_'+m);\n"
    "    var tsln_tt=TSLN_ACT[m];"
)
NEW_TSLN = (
    "    var tsln_kh=gV('tsln_kh_'+m);\n"
    "    var tsln_tt=TSLN_ACT[m];\n"
    "    // Cache ln_kh = dt_kh * tsln_kh / 100 cho BOD\n"
    "    _kpiCache['ln_kh_'+m]=(_kpiCache['dt_kh_'+m]!=null&&tsln_kh!=null)?_kpiCache['dt_kh_'+m]*tsln_kh/100:null;"
)
if OLD_TSLN in html:
    html = html.replace(OLD_TSLN, NEW_TSLN, 1)
    print('✓ Cache ln_kh trong recalcKPI section 3')
else:
    print('❌ Không match tsln_kh calc')

# ═══════════════════════════════════════════════════════════════
# 4. Cuối recalcKPI: nếu BOD đang mở thì re-render
# ═══════════════════════════════════════════════════════════════
OLD_END_ACHIEVE = "buildAchieve(allMs,'Cả năm '+lastYear)}</div>`;\n}"
NEW_END_ACHIEVE = (
    "buildAchieve(allMs,'Cả năm '+lastYear)}</div>`;\n"
    "  // Re-render BOD nếu đang mở để cập nhật mục tiêu từ KPI\n"
    "  const _bodP=document.getElementById('page-bod');\n"
    "  if(_bodP&&_bodP.style.display!=='none') renderBOD();\n"
    "}"
)
if OLD_END_ACHIEVE in html:
    html = html.replace(OLD_END_ACHIEVE, NEW_END_ACHIEVE, 1)
    print('✓ Cuối recalcKPI: re-render BOD nếu đang mở')
else:
    print('❌ Không match cuối recalcKPI')

# ═══════════════════════════════════════════════════════════════
# 5. Update getKH() trong renderBOD để đọc _kpiCache trước
# ═══════════════════════════════════════════════════════════════
OLD_GETKH = (
    "  function getKH(field,month){\n"
    "    const el=document.getElementById(field+'_'+month);\n"
    "    return el&&el.value?pN(el.value):null;\n"
    "  }"
)
NEW_GETKH = (
    "  function getKH(field,month){\n"
    "    const key=field+'_'+month;\n"
    "    // _kpiCache chứa các giá trị tính toán (dt_kh, ln_kh) từ recalcKPI\n"
    "    if(_kpiCache[key]!==undefined) return _kpiCache[key];\n"
    "    const el=document.getElementById(key);\n"
    "    return el&&el.value?pN(el.value):null;\n"
    "  }"
)
if OLD_GETKH in html:
    html = html.replace(OLD_GETKH, NEW_GETKH, 1)
    print('✓ getKH() đọc _kpiCache trước')
else:
    print('❌ Không match getKH()')

# ═══════════════════════════════════════════════════════════════
# 6. BOD header HTML: thêm date picker
# ═══════════════════════════════════════════════════════════════
OLD_BOD_HEADER_BTNS = (
    '    <div>\n'
    '      <button class="bod-print-btn" onclick="window.print()">🖨️ In báo cáo</button>\n'
    '      <button class="bod-copy-btn" onclick="copyBOD()">📋 Copy gửi Zalo</button>\n'
    '    </div>'
)
NEW_BOD_HEADER_BTNS = (
    '    <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">\n'
    '      <div class="fg" style="gap:6px">\n'
    '        <label style="font-size:11px;font-weight:700;color:#555;white-space:nowrap">📅 Báo cáo đến:</label>\n'
    '        <input type="date" id="bodReportDate" onchange="renderBOD()"\n'
    '               style="border:1px solid #d0d7de;border-radius:6px;padding:4px 8px;font-size:12px;cursor:pointer">\n'
    '        <button style="background:#6b7a8d;color:#fff;border:none;border-radius:6px;padding:5px 10px;font-size:11px;cursor:pointer" onclick="document.getElementById(\'bodReportDate\').value=\'\';renderBOD()">Mới nhất</button>\n'
    '      </div>\n'
    '      <button class="bod-print-btn" onclick="window.print()">🖨️ In báo cáo</button>\n'
    '      <button class="bod-copy-btn" onclick="copyBOD()">📋 Copy gửi Zalo</button>\n'
    '    </div>'
)
if OLD_BOD_HEADER_BTNS in html:
    html = html.replace(OLD_BOD_HEADER_BTNS, NEW_BOD_HEADER_BTNS, 1)
    print('✓ BOD header: thêm date picker')
else:
    print('❌ Không match BOD header buttons')

# ═══════════════════════════════════════════════════════════════
# 7. renderBOD: thay phần xác định lastDate bằng logic dùng date picker
# ═══════════════════════════════════════════════════════════════
OLD_BOD_TOP = (
    "function renderBOD(){\n"
    "  const data2026=D_ALL.filter(r=>r.nam===2026);\n"
    "  if(!data2026.length){document.getElementById('bodDateInfo').textContent='Không có dữ liệu 2026';return;}\n"
    "\n"
    "  // Ngày có dữ liệu gần nhất\n"
    "  const dates=data2026.map(r=>r.ngay).filter(x=>x).map(x=>new Date(x)).filter(x=>!isNaN(x));\n"
    "  const lastDate=new Date(Math.max(...dates));\n"
    "  const lastDay=lastDate.getDate(), lastMonth=lastDate.getMonth()+1, lastYear=lastDate.getFullYear();\n"
    "  const daysInMonth=new Date(lastYear,lastMonth,0).getDate();\n"
    "  const paceRatio=lastDay/daysInMonth; // % ngày đã qua trong tháng"
)
NEW_BOD_TOP = (
    "function renderBOD(){\n"
    "  const allData2026=D_ALL.filter(r=>r.nam===2026);\n"
    "  if(!allData2026.length){document.getElementById('bodDateInfo').textContent='Không có dữ liệu 2026';return;}\n"
    "\n"
    "  // Xác định ngày báo cáo: dùng date picker nếu có, không thì lấy ngày mới nhất\n"
    "  const selDateEl=document.getElementById('bodReportDate');\n"
    "  const sortedDates=allData2026.map(r=>r.ngay).filter(x=>x&&x.length>=10).map(x=>x.slice(0,10)).sort();\n"
    "  const autoDate=sortedDates[sortedDates.length-1]||new Date().toISOString().slice(0,10);\n"
    "  const reportDateStr=(selDateEl&&selDateEl.value)?selDateEl.value:autoDate;\n"
    "  // Set date picker nếu chưa set\n"
    "  if(selDateEl&&!selDateEl.value) selDateEl.value=autoDate;\n"
    "\n"
    "  // Lọc dữ liệu đến ngày báo cáo\n"
    "  const data2026=allData2026.filter(r=>r.ngay&&r.ngay.slice(0,10)<=reportDateStr);\n"
    "  if(!data2026.length){document.getElementById('bodDateInfo').textContent='Không có dữ liệu trước ngày '+reportDateStr;return;}\n"
    "\n"
    "  const lastDate=new Date(reportDateStr);\n"
    "  const lastDay=lastDate.getDate(), lastMonth=lastDate.getMonth()+1, lastYear=lastDate.getFullYear();\n"
    "  const daysInMonth=new Date(lastYear,lastMonth,0).getDate();\n"
    "  const paceRatio=lastDay/daysInMonth; // % ngày đã qua trong tháng"
)
if OLD_BOD_TOP in html:
    html = html.replace(OLD_BOD_TOP, NEW_BOD_TOP, 1)
    print('✓ renderBOD dùng date picker để xác định ngày báo cáo')
else:
    print('❌ Không match renderBOD top (data2026 / dates detection)')

# ═══════════════════════════════════════════════════════════════
# Save
# ═══════════════════════════════════════════════════════════════
with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f'\n{"="*52}')
print(f'✅ Xong! {orig//1024} KB → {len(html)//1024} KB')
