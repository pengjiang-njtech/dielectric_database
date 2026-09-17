/* Responsive scientific chart renderer: explicit ticks, labels and DPR-safe canvas. */
const chartRegistry = new Map();

function niceTicks(min, max, count = 6) {
  if (!Number.isFinite(min) || !Number.isFinite(max)) return [];
  if (min === max) return [min];
  const raw = Math.abs(max - min) / Math.max(2, count - 1);
  const power = 10 ** Math.floor(Math.log10(raw));
  const fraction = raw / power;
  const step = (fraction <= 1 ? 1 : fraction <= 2 ? 2 : fraction <= 5 ? 5 : 10) * power;
  const start = Math.ceil(min / step) * step;
  const values = [];
  for (let value = start; value <= max + step * 1e-8; value += step) values.push(value);
  return values;
}

function tickText(value, span) {
  if (!Number.isFinite(value)) return '';
  if ((Math.abs(value) >= 10000) || (Math.abs(value) > 0 && Math.abs(value) < 0.001)) return value.toExponential(2);
  const decimals = span < 0.1 ? 3 : span < 1 ? 2 : span < 10 ? 1 : 0;
  return value.toFixed(decimals);
}

drawChart = function(canvas, series, xLabel, yLabel, opt = {}) {
  chartRegistry.set(canvas, {series, xLabel, yLabel, opt});
  const rect = canvas.getBoundingClientRect();
  const width = Math.max(640, Math.round(rect.width || canvas.parentElement.clientWidth || 900));
  const height = Math.max(360, Math.round(rect.height || 420));
  const dpr = Math.min(2, window.devicePixelRatio || 1);
  canvas.width = Math.round(width * dpr);
  canvas.height = Math.round(height * dpr);
  const ctx = canvas.getContext('2d');
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, width, height);
  const margin = {left: 82, right: 28, top: 24, bottom: 72};
  const plotWidth = width - margin.left - margin.right;
  const plotHeight = height - margin.top - margin.bottom;
  const points = series.flatMap(s => s.points || []).filter(p => Number.isFinite(p[0]) && Number.isFinite(p[1]) && (!opt.logX || p[0] > 0));
  ctx.font = '12px "Microsoft YaHei", Arial, sans-serif';
  ctx.fillStyle = '#64748b';
  if (!points.length) {
    ctx.textAlign = 'center';
    ctx.fillText('暂无符合条件的数据', width / 2, height / 2);
    return;
  }

  const transformedX = points.map(p => opt.logX ? Math.log10(p[0]) : p[0]);
  const valuesY = points.map(p => p[1]);
  let xmin = Math.min(...transformedX), xmax = Math.max(...transformedX);
  let ymin = Math.min(...valuesY), ymax = Math.max(...valuesY);
  if (xmin === xmax) { xmin -= 0.5; xmax += 0.5; }
  if (ymin === ymax) { ymin -= Math.max(1, Math.abs(ymin) * 0.05); ymax += Math.max(1, Math.abs(ymax) * 0.05); }
  const xPad = (xmax - xmin) * 0.04;
  const yPad = (ymax - ymin) * 0.08;
  xmin -= xPad; xmax += xPad; ymin -= yPad; ymax += yPad;
  const X = value => margin.left + ((opt.logX ? Math.log10(value) : value) - xmin) / (xmax - xmin) * plotWidth;
  const Y = value => margin.top + (ymax - value) / (ymax - ymin) * plotHeight;

  const yTicks = niceTicks(ymin, ymax, 6);
  const xTicks = opt.logX
    ? Array.from({length: Math.floor(xmax) - Math.ceil(xmin) + 1}, (_, i) => 10 ** (Math.ceil(xmin) + i))
    : niceTicks(xmin, xmax, 7);

  ctx.lineWidth = 1;
  yTicks.forEach(value => {
    const y = Y(value);
    ctx.strokeStyle = '#e5eaf2';
    ctx.beginPath(); ctx.moveTo(margin.left, y); ctx.lineTo(width - margin.right, y); ctx.stroke();
    ctx.fillStyle = '#64748b'; ctx.textAlign = 'right'; ctx.textBaseline = 'middle';
    ctx.fillText(tickText(value, ymax - ymin), margin.left - 12, y);
  });
  xTicks.forEach(value => {
    const x = X(value);
    if (x < margin.left - 1 || x > width - margin.right + 1) return;
    ctx.strokeStyle = '#eef2f7';
    ctx.beginPath(); ctx.moveTo(x, margin.top); ctx.lineTo(x, height - margin.bottom); ctx.stroke();
    ctx.fillStyle = '#64748b'; ctx.textAlign = 'center'; ctx.textBaseline = 'top';
    const label = opt.logX ? (value >= 0.01 && value < 1000 ? String(Number(value.toPrecision(3))) : value.toExponential(0)) : tickText(value, xmax - xmin);
    ctx.fillText(label, x, height - margin.bottom + 12);
  });

  ctx.strokeStyle = '#94a3b8'; ctx.lineWidth = 1.2;
  ctx.beginPath(); ctx.moveTo(margin.left, margin.top); ctx.lineTo(margin.left, height - margin.bottom); ctx.lineTo(width - margin.right, height - margin.bottom); ctx.stroke();
  ctx.fillStyle = '#334155'; ctx.font = '13px "Microsoft YaHei", Arial, sans-serif';
  ctx.textAlign = 'center'; ctx.textBaseline = 'alphabetic';
  ctx.fillText(xLabel, margin.left + plotWidth / 2, height - 16);
  ctx.save(); ctx.translate(20, margin.top + plotHeight / 2); ctx.rotate(-Math.PI / 2); ctx.fillText(yLabel, 0, 0); ctx.restore();

  ctx.save(); ctx.beginPath(); ctx.rect(margin.left, margin.top, plotWidth, plotHeight); ctx.clip();
  series.forEach(s => {
    const clean = (s.points || []).filter(p => Number.isFinite(p[0]) && Number.isFinite(p[1]) && (!opt.logX || p[0] > 0)).sort((a, b) => a[0] - b[0]);
    ctx.strokeStyle = s.color; ctx.fillStyle = s.color; ctx.lineWidth = s.lineWidth || 2;
    ctx.setLineDash(s.dash ? [7, 5] : []);
    if (s.line && clean.length > 1) {
      ctx.beginPath(); clean.forEach((p, i) => i ? ctx.lineTo(X(p[0]), Y(p[1])) : ctx.moveTo(X(p[0]), Y(p[1]))); ctx.stroke();
    } else {
      clean.forEach(p => { ctx.beginPath(); ctx.arc(X(p[0]), Y(p[1]), s.radius || 3.8, 0, Math.PI * 2); ctx.fill(); });
    }
  });
  ctx.restore();
};

/* Frequency charts open at the temperature nearest 25 °C; users can still select all temperatures. */
renderFrequency = function() {
  const rows = state.currentCompoundRows.filter(r => rv(r,'sample_type') === 'pure' && rv(r,'frequency_ghz') > 0 && (rv(r,'epsilon_real') != null || rv(r,'epsilon_imag') != null));
  const temps = [...new Set(rows.map(r => rv(r,'temperature_c')).filter(x => x != null))].sort((a,b) => a-b);
  $('#frequencyTemp').innerHTML = '<option value="all">全部温度</option>' + temps.map(t => `<option value="${t}">${fmt(t)} °C</option>`).join('');
  if (temps.length) $('#frequencyTemp').value = String(temps.reduce((a,b) => Math.abs(b-25) < Math.abs(a-25) ? b : a));
  $('#frequencyTemp').onchange = () => drawFrequency(rows);
  drawFrequency(rows);
  const sm = chartSourceMap(rows);
  $('#frequencySources').onclick = () => openDrawer(sm);
  $('#frequencyCsv').onclick = () => downloadMeasurements(filterFrequencyRows(rows), `${safeName(state.currentCompound.name_en)}_frequency.csv`);
};

/* Normalize mixture composition to the first selected component before plotting. */
renderMix = function() {
  const basis=$('#mixBasis').value,tv=$('#mixTemp').value,prop=$('#mixProperty').value,selected=findCompound($('#mixC1').value);
  const rows=state.currentMixRows.filter(r=>(!basis||rv(r,'composition_basis')===basis)&&(tv==='all'||rv(r,'temperature_c')===+tv));
  const temps=[...new Set(rows.map(r=>rv(r,'temperature_c')))],series=[];
  temps.forEach((t,i)=>{
    const color=palette[i%palette.length];
    const points=rows.filter(r=>rv(r,'temperature_c')===t&&rv(r,prop)!=null).map(r=>{
      const x=selected&&rv(r,'component1_id')===selected.id?rv(r,'x1'):selected&&rv(r,'component2_id')===selected.id?rv(r,'x2'):rv(r,'x1');
      return [x,rv(r,prop)];
    }).filter(p=>p[0]!=null);
    if(points.length){series.push({label:`${fmt(t)} °C · 实验值`,color,line:false,points});const fit=fittedCurve(points);if(fit.length)series.push({label:`${fmt(t)} °C · 拟合`,color,line:true,points:fit});}
  });
  const component=selected?(selected.name_cn||selected.name_en||'组分1'):'组分1';
  drawChart($('#mixtureChart'),series,`${component}${basisNames[basis]||basis||'组成'}`,prop==='epsilon_static'?'εs':prop==='epsilon_real'?'ε′':'ε″');
  $('#mixtureLegend').innerHTML=series.map(s=>`<span><i style="background:${s.color}"></i>${esc(s.label)}</span>`).join('');
  const sm=chartSourceMap(rows,'M');$('#mixSources').onclick=()=>openDrawer(sm);$('#mixCount').textContent=`${rows.length} 条；组成基准：${basisNames[basis]||basis||'未注明'}`;
  $('#mixtureTable').innerHTML='<thead><tr><th>组分 1</th><th>组分 2</th><th>x1</th><th>x2</th><th>组成基准</th><th>T / °C</th><th>f / GHz</th><th>εs</th><th>ε′</th><th>ε″</th><th>来源</th></tr></thead><tbody>'+rows.slice(0,500).map(r=>`<tr><td>${esc(compoundName(rv(r,'component1_id')))}</td><td>${esc(compoundName(rv(r,'component2_id')))}</td><td>${fmt(rv(r,'x1'))}</td><td>${fmt(rv(r,'x2'))}</td><td>${esc(basisNames[rv(r,'composition_basis')]||rv(r,'composition_basis')||'—')}</td><td>${fmt(rv(r,'temperature_c'))}</td><td>${fmt(rv(r,'frequency_ghz'),6)}</td><td>${fmt(rv(r,'epsilon_static'))}</td><td>${fmt(rv(r,'epsilon_real'))}</td><td>${fmt(rv(r,'epsilon_imag'))}</td><td>${esc(sourceById(rv(r,'source_id'))?.source_key||'—')}</td></tr>`).join('')+'</tbody>';
};

function chooseNearestTemperature(select, target=25) {
  const values=[...select.options].map(o=>Number(o.value)).filter(Number.isFinite);
  if(values.length) select.value=String(values.reduce((a,b)=>Math.abs(b-target)<Math.abs(a-target)?b:a));
}

/* Apply scientifically useful defaults once the database has finished loading. */
const defaultTimer=setInterval(()=>{
  if(!state.meta||$('#app').hidden)return;
  clearInterval(defaultTimer);
  const methanol=state.compounds.find(c=>c.cas==='67-56-1');
  const water=state.compounds.find(c=>c.cas==='7732-18-5');
  if(methanol) openCompound(methanol);
  if(methanol&&water){$('#mixC1').value=compoundLabel(methanol);refreshC2();$('#mixC2').value=compoundLabel(water);runMix();chooseNearestTemperature($('#mixTemp'));renderMix();}
},50);

let resizeTimer;
window.addEventListener('resize',()=>{clearTimeout(resizeTimer);resizeTimer=setTimeout(()=>chartRegistry.forEach((cfg,canvas)=>drawChart(canvas,cfg.series,cfg.xLabel,cfg.yLabel,cfg.opt)),120)});
