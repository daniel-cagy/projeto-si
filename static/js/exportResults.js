import { exportActions, exportCsvBtn, exportJsonBtn } from './dom.js';

let latestPayload = null;

export function resetExport() {
  latestPayload = null;
  exportActions.hidden = true;
}

export function setExportPayload(payload) {
  latestPayload = payload;
  exportActions.hidden = false;
}

function getExportBaseName() {
  const productName = latestPayload?.resposta?.produto_identificado || 'estimativa-produto';
  const safeProductName = productName
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]+/gi, '-')
    .replace(/^-|-$/g, '')
    .toLowerCase() || 'estimativa-produto';
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  return `${safeProductName}-${timestamp}`;
}

function downloadBlob(content, type, filename) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function csvEscape(value) {
  const text = String(value ?? '');
  return `"${text.replaceAll('"', '""')}"`;
}

function addRangeFields(data, prefix, range) {
  data[`${prefix}_min`] = range?.min ?? '';
  data[`${prefix}_estimativa`] = range?.estimativa ?? '';
  data[`${prefix}_max`] = range?.max ?? '';
}

function buildCsv(payload) {
  const resposta = payload.resposta || {};
  const produto = resposta.produto || {};
  const dimensoes = produto.dimensoes_estimadas_cm || {};
  const metricas = payload.metricas_logisticas || {};
  const corrections = payload.correcoes_usuario || {};
  const adjustedProduct = payload.produto_ajustado || {};
  const adjustedDimensions = adjustedProduct.dimensoes_cm || {};
  const validacao = payload.validacao || {};
  const knownMeasures = payload.medidas_conhecidas_informadas || {};
  const data = {
    produto_identificado: resposta.produto_identificado || '',
    descricao_resumida: resposta.descricao_resumida || '',
    nivel_confianca: resposta.nivel_confianca || '',
    modo_processamento_imagem: payload.modo_processamento_imagem || '',
  };

  addRangeFields(data, 'comprimento_cm', dimensoes.comprimento);
  addRangeFields(data, 'largura_cm', dimensoes.largura);
  addRangeFields(data, 'altura_cm', dimensoes.altura);
  addRangeFields(data, 'peso_kg', produto.peso_estimado_kg);

  data.medida_conhecida_comprimento_cm = knownMeasures.comprimento ?? '';
  data.medida_conhecida_largura_cm = knownMeasures.largura ?? '';
  data.medida_conhecida_altura_cm = knownMeasures.altura ?? '';
  data.medida_conhecida_peso_kg = knownMeasures.peso ?? '';
  data.volume_produto_cm3 = metricas.volume_produto_cm3 ?? '';
  data.densidade_produto_kg_cm3 = metricas.densidade_produto_kg_cm3 ?? '';
  data.peso_cubado_kg = metricas.peso_cubado_kg ?? '';
  data.peso_cobravel_estimado_kg = metricas.peso_cobravel_estimado_kg ?? '';
  data.fator_cubagem = metricas.fator_cubagem ?? '';
  data.correcao_comprimento_cm = corrections.comprimento ?? '';
  data.correcao_largura_cm = corrections.largura ?? '';
  data.correcao_altura_cm = corrections.altura ?? '';
  data.correcao_peso_kg = corrections.peso ?? '';
  data.comprimento_ajustado_cm = adjustedDimensions.comprimento ?? '';
  data.largura_ajustada_cm = adjustedDimensions.largura ?? '';
  data.altura_ajustada_cm = adjustedDimensions.altura ?? '';
  data.peso_ajustado_kg = adjustedProduct.peso_kg ?? '';
  data.recalculado_localmente = payload.recalculado_localmente ?? '';
  data.validacao_status = validacao.status ?? '';
  data.validacao_erros = (validacao.erros || []).join(' | ');
  data.validacao_alertas = (validacao.alertas || []).join(' | ');

  const headers = Object.keys(data);
  const values = headers.map(header => csvEscape(data[header]));
  return `${headers.join(',')}\n${values.join(',')}\n`;
}

export function setupExportActions() {
  exportJsonBtn.addEventListener('click', () => {
    if (!latestPayload) return;
    downloadBlob(
      JSON.stringify(latestPayload, null, 2),
      'application/json;charset=utf-8',
      `${getExportBaseName()}.json`,
    );
  });

  exportCsvBtn.addEventListener('click', () => {
    if (!latestPayload) return;
    downloadBlob(
      buildCsv(latestPayload),
      'text/csv;charset=utf-8',
      `${getExportBaseName()}.csv`,
    );
  });
}
