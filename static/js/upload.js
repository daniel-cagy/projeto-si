import { dropzone, fileInput, previewList, previewWrap, removeBtn } from './dom.js';

const MAX_FILES = 3;

function getAcceptedFiles(fileList) {
  return Array.from(fileList)
    .filter(file => file.type.startsWith('image/'))
    .slice(0, MAX_FILES);
}

function setFileInputFiles(files) {
  const dataTransfer = new DataTransfer();
  files.forEach(file => dataTransfer.items.add(file));
  fileInput.files = dataTransfer.files;
}

function renderPreviewItem(file, index) {
  const item = document.createElement('div');
  item.className = 'preview-item';

  const img = document.createElement('img');
  img.alt = `Preview ${index + 1} do produto`;
  img.src = URL.createObjectURL(file);
  img.addEventListener('load', () => URL.revokeObjectURL(img.src), { once: true });

  const badge = document.createElement('span');
  badge.textContent = `Imagem ${index + 1}`;

  item.appendChild(img);
  item.appendChild(badge);
  return item;
}

function showPreviews(files, onFileChange) {
  previewList.innerHTML = '';
  files.forEach((file, index) => {
    previewList.appendChild(renderPreviewItem(file, index));
  });

  previewWrap.style.display = files.length ? 'block' : 'none';
  dropzone.style.display = files.length ? 'none' : 'block';
  onFileChange(files.length > 0);
}

function applySelectedFiles(fileList, onFileChange) {
  const files = getAcceptedFiles(fileList);
  setFileInputFiles(files);
  showPreviews(files, onFileChange);
}

export function setupUpload({ onFileChange }) {
  fileInput.addEventListener('change', () => {
    applySelectedFiles(fileInput.files, onFileChange);
  });

  removeBtn.addEventListener('click', () => {
    previewList.innerHTML = '';
    previewWrap.style.display = 'none';
    dropzone.style.display = 'block';
    fileInput.value = '';
    onFileChange(false);
  });

  dropzone.addEventListener('dragover', e => {
    e.preventDefault();
    dropzone.classList.add('drag-over');
  });

  dropzone.addEventListener('dragleave', () => {
    dropzone.classList.remove('drag-over');
  });

  dropzone.addEventListener('drop', e => {
    e.preventDefault();
    dropzone.classList.remove('drag-over');
    applySelectedFiles(e.dataTransfer.files, onFileChange);
  });
}
