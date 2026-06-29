import {
  btnIcon,
  btnLabel,
  charNum,
  description,
  fileInput,
  form,
  result,
  resultBody,
  spinner,
  step3,
  submitBtn,
} from './js/dom.js';
import { resetExport, setExportPayload, setupExportActions } from './js/exportResults.js';
import { collectKnownMeasures, setupKnownMeasures } from './js/knownMeasures.js';
import { renderError, renderResult } from './js/render.js';
import { getCubageFactor, getImageProcessingMode, getSelectedModel, setupAdvancedSettings } from './js/settings.js';
import { setupUpload } from './js/upload.js';

let hasFile = false;
let currentPayload = null;

const ADJUSTABLE_MEASURES = {
  comprimento: { label: 'Comprimento', unit: 'cm', digits: 2 },
  largura: { label: 'Largura', unit: 'cm', digits: 2 },
  altura: { label: 'Altura', unit: 'cm', digits: 2 },
  peso: { label: 'Peso', unit: 'kg', digits: 3 },
};



function getCurrentCorrectionValue(field) {
  const corrections = currentPayload?.correcoes_usuario || {};
  if (Object.prototype.hasOwnProperty.call(corrections, field)) {
    return corrections[field];
  }

  const produto = currentPayload?.resposta?.produto || {};
  const dimensoes = produto.dimensoes_estimadas_cm || {};
  if (field === 'peso') return produto.peso_estimado_kg?.estimativa || '';
  return dimensoes[field]?.estimativa || '';
}

function closeMeasureEditModal() {
  document.querySelector('.measure-edit-backdrop')?.remove();
}

function openMeasureEditModal(field) {
  if (!currentPayload) return;

  const config = ADJUSTABLE_MEASURES[field];
  if (!config) return;

  closeMeasureEditModal();

  const backdrop = document.createElement('div');
  backdrop.className = 'measure-edit-backdrop';
  backdrop.innerHTML = `
    <form class="measure-edit-modal">
      <div class="measure-edit-title">Ajustar ${config.label.toLowerCase()}</div>
      <label class="measure-edit-field">
        <span>${config.label} (${config.unit})</span>
        <input type="number" min="0.0001" step="any" inputmode="decimal" value="${getCurrentCorrectionValue(field)}" />
      </label>
      <div class="measure-edit-actions">
        <button type="button" class="measure-edit-cancel">Cancelar</button>
        <button type="submit" class="measure-edit-submit">Aplicar ajuste</button>
      </div>
    </form>
  `;

  document.body.appendChild(backdrop);
  const input = backdrop.querySelector('input');
  input.focus();
  input.select();

  backdrop.addEventListener('click', event => {
    if (event.target === backdrop || event.target.closest('.measure-edit-cancel')) {
      closeMeasureEditModal();
    }
  });

  backdrop.querySelector('form').addEventListener('submit', async event => {
    event.preventDefault();
    const value = Number(input.value.replace(',', '.'));
    if (!Number.isFinite(value) || value <= 0) {
      input.focus();
      return;
    }

    const corrections = { ...(currentPayload.correcoes_usuario || {}), [field]: value };
    try {
      await recalculateResult(corrections);
      closeMeasureEditModal();
    } catch (error) {
      closeMeasureEditModal();
      renderError(error.message || 'Não foi possível recalcular o resultado.');
      result.style.display = 'block';
    }
  });
}

async function recalculateResult(corrections) {
  const response = await fetch('/recalculate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      payload: currentPayload,
      correcoes_usuario: corrections,
    }),
  });

  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(payload?.detail || 'Não foi possível recalcular o resultado.');
  }

  currentPayload = payload;
  setExportPayload(currentPayload);
  renderResult(currentPayload);
}

function updateSubmit() {
  const hasText = description.value.trim().length > 0;
  submitBtn.disabled = !(hasFile && hasText);
}

function setLoading(isLoading) {
  submitBtn.disabled = isLoading || !(hasFile && description.value.trim().length > 0);
  spinner.style.display = isLoading ? 'block' : 'none';
  btnIcon.style.display = isLoading ? 'none' : 'block';
  btnLabel.textContent = isLoading ? 'Analisando...' : 'Analisar produto';
}

setupUpload({
  onFileChange(fileIsSelected) {
    hasFile = fileIsSelected;
    currentPayload = null;
    resetExport();
    updateSubmit();
  },
});

setupKnownMeasures({
  onChange() {
    currentPayload = null;
    resetExport();
  },
});

setupExportActions();

setupAdvancedSettings({
  onChange() {
    currentPayload = null;
    resetExport();
  },
});


resultBody.addEventListener('click', event => {
  const button = event.target.closest('[data-adjust-measure]');
  if (!button) return;

  openMeasureEditModal(button.dataset.adjustMeasure);
});

description.addEventListener('input', () => {
  charNum.textContent = description.value.length;
  updateSubmit();
});

form.addEventListener('submit', async e => {
  e.preventDefault();
  if (submitBtn.disabled) return;

  const file = fileInput.files[0];
  if (!file) return;

  const formData = new FormData();
  const knownMeasures = collectKnownMeasures();
  formData.append('image', file);
  formData.append('description', description.value.trim());
  formData.append('known_measures', JSON.stringify(knownMeasures));
  formData.append('image_processing_mode', getImageProcessingMode());
  formData.append('model', getSelectedModel());
  formData.append('cubage_factor', getCubageFactor());

  setLoading(true);
  currentPayload = null;
  resetExport();
  result.style.display = 'none';

  try {
    const response = await fetch('/estimate', {
      method: 'POST',
      body: formData,
    });

    const payload = await response.json().catch(() => null);
    if (!response.ok) {
      throw new Error(payload?.detail || 'Não foi possível analisar o produto.');
    }

    step3.classList.add('active');
    step3.querySelector('.step-num').style.background = 'var(--green)';
    step3.querySelector('.step-num').style.color = '#fff';

    currentPayload = payload;
    setExportPayload(currentPayload);
    renderResult(currentPayload);
  } catch (error) {
    currentPayload = null;
    resetExport();
    renderError(error.message || 'Erro inesperado ao analisar o produto.');
  } finally {
    result.style.display = 'block';
    setLoading(false);
  }
});
