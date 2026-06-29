import { result, resultBody } from './dom.js';
import { escapeHtml, formatNumber, formatRange, metric } from './format.js';
import { renderKnownMeasuresSummary } from './knownMeasures.js';

const ADJUSTABLE_MEASURES = {
  comprimento: { label: 'Comprimento', unit: 'cm', digits: 2 },
  largura: { label: 'Largura', unit: 'cm', digits: 2 },
  altura: { label: 'Altura', unit: 'cm', digits: 2 },
  peso: { label: 'Peso estimado', unit: 'kg', digits: 3 },
};

function hasCorrection(corrections, field) {
  return Object.prototype.hasOwnProperty.call(corrections, field);
}

function formatAdjustedValue(value, unit, digits) {
  return `${formatNumber(value, digits)} ${unit} <small>ajustado</small>`;
}

function getMeasureValue({ field, range, adjustedValue, corrections, unit, digits }) {
  if (hasCorrection(corrections, field)) {
    return formatAdjustedValue(adjustedValue, unit, digits);
  }

  return formatRange(range, unit, digits);
}

function editableMetric(label, field, value) {
  const buttonLabel = field === 'peso' ? 'Ajustar peso' : 'Ajustar medida';

  return `
    <div class="metric editable-metric">
      <div>
        <div class="metric-label">${escapeHtml(label)}</div>
        <div class="metric-value">${value}</div>
      </div>
      <button type="button" class="adjust-measure-btn" data-adjust-measure="${escapeHtml(field)}">
        ${buttonLabel}
      </button>
    </div>
  `;
}

function renderUserCorrectionsSummary(corrections) {
  const entries = Object.entries(corrections || {});
  if (!entries.length) return '';

  const items = entries
    .map(([field, value]) => {
      const config = ADJUSTABLE_MEASURES[field];
      if (!config) return '';
      return `<span>${escapeHtml(config.label)} ajustado: ${formatNumber(value, config.digits)} ${config.unit}</span>`;
    })
    .filter(Boolean)
    .join('');

  return items ? `<div class="known-measures-summary manual-corrections-summary">${items}</div>` : '';
}

export function renderResult(payload) {
  const resposta = payload.resposta || {};
  const produto = resposta.produto || {};
  const dimensoes = produto.dimensoes_estimadas_cm || {};
  const peso = produto.peso_estimado_kg || {};
  const metricas = payload.metricas_logisticas || {};
  const validacao = payload.validacao || { status: false, erros: [], alertas: [] };
  const corrections = payload.correcoes_usuario || {};
  const adjustedProduct = payload.produto_ajustado || {};
  const adjustedDimensions = adjustedProduct.dimensoes_cm || {};
  const confidence = resposta.nivel_confianca === 'alto' ? 'alto' : 'baixo';

  const comprimentoValue = getMeasureValue({
    field: 'comprimento',
    range: dimensoes.comprimento,
    adjustedValue: adjustedDimensions.comprimento,
    corrections,
    unit: 'cm',
    digits: 2,
  });
  const larguraValue = getMeasureValue({
    field: 'largura',
    range: dimensoes.largura,
    adjustedValue: adjustedDimensions.largura,
    corrections,
    unit: 'cm',
    digits: 2,
  });
  const alturaValue = getMeasureValue({
    field: 'altura',
    range: dimensoes.altura,
    adjustedValue: adjustedDimensions.altura,
    corrections,
    unit: 'cm',
    digits: 2,
  });
  const pesoValue = getMeasureValue({
    field: 'peso',
    range: peso,
    adjustedValue: adjustedProduct.peso_kg,
    corrections,
    unit: 'kg',
    digits: 3,
  });

  const validationItems = [...(validacao.erros || []), ...(validacao.alertas || [])]
    .map(item => `<li>${escapeHtml(item)}</li>`)
    .join('');

  result.classList.remove('error');
  resultBody.innerHTML = `
    <div class="result-summary">
      <div class="result-name">${escapeHtml(resposta.produto_identificado || 'Produto identificado')}</div>
      <div class="result-description">${escapeHtml(resposta.descricao_resumida || '')}</div>
      ${renderKnownMeasuresSummary(payload.medidas_conhecidas_informadas)}
      ${renderUserCorrectionsSummary(corrections)}
      <span class="confidence ${confidence === 'baixo' ? 'low' : ''}">Confiança ${confidence}</span>
      <div class="result-grid">
        ${editableMetric('Comprimento', 'comprimento', comprimentoValue)}
        ${editableMetric('Largura', 'largura', larguraValue)}
        ${editableMetric('Altura', 'altura', alturaValue)}
        ${editableMetric('Peso estimado', 'peso', pesoValue)}
        ${metric('Peso cubado', `${formatNumber(metricas.peso_cubado_kg, 2)} kg`)}
        ${metric('Peso cobrável', `${formatNumber(metricas.peso_cobravel_estimado_kg, 2)} kg`)}
        ${metric('Fator de cubagem', formatNumber(metricas.fator_cubagem, 0))}
      </div>
      ${validationItems ? `<ul class="validation-list">${validationItems}</ul>` : ''}
    </div>
  `;
}

export function renderError(message) {
  result.classList.add('error');
  resultBody.innerHTML = escapeHtml(message);
}
