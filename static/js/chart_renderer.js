/**
 * Renderizador de Gráficos Autónomo en SVG Puro (100% Offline / Cero Dependencias).
 * Dibuja gráficos interactivos de barras, líneas y donas sin requerir librerías CDN externas.
 */

// Formateador monetario
function formatMoney(amount) {
  if (amount === undefined || amount === null) return '$0.00';
  return '$' + Number(amount).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

/**
 * Dibuja el gráfico combinado de barras (Ingresos/Egresos) y línea (Flujo Neto)
 */
function renderCashflowSVG(containerId, meses) {
  const container = document.getElementById(containerId);
  if (!container || !meses || meses.length === 0) return;

  const width = container.clientWidth || 700;
  const height = 280;
  const padding = { top: 25, right: 30, bottom: 45, left: 65 };
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;

  // Encontrar valores mínimos y máximos para la escala Y
  let maxVal = Math.max(...meses.map(m => Math.max(m.ingresos, m.egresos, m.flujo_neto, 1000)));
  let minVal = Math.min(...meses.map(m => Math.min(m.flujo_neto, 0)));
  
  // Agregar margen
  maxVal = Math.ceil(maxVal * 1.15 / 500) * 500;
  if (minVal < 0) {
    minVal = Math.floor(minVal * 1.25 / 200) * 200;
  } else {
    minVal = 0;
  }

  const range = maxVal - minVal;
  const getY = (val) => padding.top + plotHeight - ((val - minVal) / range) * plotHeight;
  const yZero = getY(0);

  const numMonths = meses.length;
  const groupWidth = plotWidth / numMonths;
  const barWidth = Math.min(groupWidth * 0.28, 28);

  let svg = `<svg viewBox="0 0 ${width} ${height}" class="w-full h-full" style="font-family: inherit;">`;

  // 1. Grid horizontal y etiquetas Y
  const numSteps = 5;
  for (let i = 0; i <= numSteps; i++) {
    const v = minVal + (range / numSteps) * i;
    const yPos = getY(v);
    svg += `
      <line x1="${padding.left}" y1="${yPos}" x2="${width - padding.right}" y2="${yPos}" stroke="#e2e8f0" stroke-dasharray="${v === 0 ? '0' : '4,4'}" stroke-width="${v === 0 ? '1.5' : '1'}"/>
      <text x="${padding.left - 10}" y="${yPos + 4}" fill="#64748b" font-size="10" text-anchor="end">${formatMoney(v).split('.')[0]}</text>
    `;
  }

  // 2. Barras de Ingresos y Egresos
  let linePoints = [];

  meses.forEach((m, idx) => {
    const groupCenter = padding.left + (idx + 0.5) * groupWidth;
    
    // Barra de Ingreso (Azul)
    const xIngreso = groupCenter - barWidth - 2;
    const yIngreso = getY(m.ingresos);
    const hIngreso = Math.max(0, yZero - yIngreso);
    svg += `
      <rect x="${xIngreso}" y="${yIngreso}" width="${barWidth}" height="${hIngreso}" rx="4" fill="#0284c7" opacity="0.9">
        <title>${m.mes_nombre} - Ingresos: ${formatMoney(m.ingresos)}</title>
      </rect>
    `;

    // Barra de Egreso (Rosa/Rojo)
    const xEgreso = groupCenter + 2;
    const yEgreso = getY(m.egresos);
    const hEgreso = Math.max(0, yZero - yEgreso);
    svg += `
      <rect x="${xEgreso}" y="${yEgreso}" width="${barWidth}" height="${hEgreso}" rx="4" fill="#f43f5e" opacity="0.85">
        <title>${m.mes_nombre} - Egresos: ${formatMoney(m.egresos)}</title>
      </rect>
    `;

    // Punto para la línea de Flujo Neto
    const yFlujo = getY(m.flujo_neto);
    linePoints.push({ x: groupCenter, y: yFlujo, val: m.flujo_neto, name: m.mes_nombre });

    // Etiqueta de Mes en eje X
    svg += `
      <text x="${groupCenter}" y="${height - 15}" fill="#475569" font-size="11" font-weight="600" text-anchor="middle">
        ${m.mes_nombre.split(' ')[0]}
      </text>
    `;
  });

  // 3. Línea y puntos de Flujo Neto (Verde)
  if (linePoints.length > 0) {
    const pathD = linePoints.reduce((acc, p, i) => `${acc} ${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`, '');
    svg += `
      <path d="${pathD}" fill="none" stroke="#10b981" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
    `;
    
    linePoints.forEach(p => {
      const isPos = p.val >= 0;
      svg += `
        <circle cx="${p.x}" cy="${p.y}" r="4.5" fill="${isPos ? '#10b981' : '#e11d48'}" stroke="#ffffff" stroke-width="2">
          <title>${p.name} - Flujo Neto: ${formatMoney(p.val)}</title>
        </circle>
      `;
    });
  }

  svg += `</svg>`;
  container.innerHTML = svg;
}

/**
 * Dibuja el gráfico de Dona SVG para la distribución de gastos por categoría
 */
function renderCategorySVG(containerId, legendId, gastos) {
  const container = document.getElementById(containerId);
  const legendContainer = document.getElementById(legendId);
  if (!container || !gastos) return;

  const categories = Object.keys(gastos);
  if (categories.length === 0) {
    container.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100%;color:#94a3b8;font-size:12px;">Sin datos de gastos</div>';
    if (legendContainer) legendContainer.innerHTML = '';
    return;
  }

  const colors = [
    '#0284c7', '#10b981', '#f59e0b', '#ec4899', '#8b5cf6', 
    '#6366f1', '#14b8a6', '#f43f5e', '#64748b'
  ];

  const size = 180;
  const center = size / 2;
  const radius = 68;
  const innerRadius = 45;

  let totalMonto = 0;
  categories.forEach(k => { totalMonto += gastos[k].monto_total; });
  if (totalMonto === 0) totalMonto = 1;

  let startAngle = 0;
  let paths = '';

  categories.forEach((cat, idx) => {
    const val = gastos[cat].monto_total;
    const sliceAngle = (val / totalMonto) * 2 * Math.PI;
    const endAngle = startAngle + sliceAngle;

    const x1 = center + radius * Math.sin(startAngle);
    const y1 = center - radius * Math.cos(startAngle);
    const x2 = center + radius * Math.sin(endAngle);
    const y2 = center - radius * Math.cos(endAngle);

    const x3 = center + innerRadius * Math.sin(endAngle);
    const y3 = center - innerRadius * Math.cos(endAngle);
    const x4 = center + innerRadius * Math.sin(startAngle);
    const y4 = center - innerRadius * Math.cos(startAngle);

    const largeArc = sliceAngle > Math.PI ? 1 : 0;
    const color = colors[idx % colors.length];

    const d = `
      M ${x1} ${y1}
      A ${radius} ${radius} 0 ${largeArc} 1 ${x2} ${y2}
      L ${x3} ${y3}
      A ${innerRadius} ${innerRadius} 0 ${largeArc} 0 ${x4} ${y4}
      Z
    `;

    paths += `
      <path d="${d}" fill="${color}" stroke="#ffffff" stroke-width="2">
        <title>${cat}: ${formatMoney(val)} (${gastos[cat].porcentaje}%)</title>
      </path>
    `;

    startAngle = endAngle;
  });

  const svg = `
    <svg viewBox="0 0 ${size} ${size}" width="${size}" height="${size}">
      ${paths}
      <text x="${center}" y="${center + 4}" font-size="11" font-weight="700" fill="#475569" text-anchor="middle">
        Gastos
      </text>
    </svg>
  `;
  container.innerHTML = svg;

  // Renderizar leyenda
  if (legendContainer) {
    legendContainer.innerHTML = '';
    categories.forEach((cat, idx) => {
      const color = colors[idx % colors.length];
      const item = document.createElement('div');
      item.className = 'category-legend-item';
      item.innerHTML = `
        <div style="display:flex;align-items:center;gap:6px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">
          <span style="width:9px;height:9px;border-radius:2px;background-color:${color};flex-shrink:0;"></span>
          <span style="color:#475569;overflow:hidden;text-overflow:ellipsis;">${cat}</span>
        </div>
        <span style="font-weight:700;color:#0f172a;margin-left:8px;">${gastos[cat].porcentaje}%</span>
      `;
      legendContainer.appendChild(item);
    });
  }
}
