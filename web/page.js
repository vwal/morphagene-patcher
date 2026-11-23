// Browser helpers shared by the options editor and firmware patcher.
'use strict';

const $ = (id) => document.getElementById(id);

function download(name, bytes, type) {
  const url = URL.createObjectURL(new Blob([bytes], { type: type || 'application/octet-stream' }));
  const a = document.createElement('a');
  a.href = url;
  a.download = name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 5000);
}

function status(id, text, kind) {
  const el = $(id);
  el.textContent = text;
  el.dataset.kind = kind || '';
}

function bindFileDrop(inputId, zoneId, load, rejectDrop) {
  $(inputId).addEventListener('change', e => {
    const file = e.target.files[0];
    e.target.value = ''; // Allow choosing the same file again.
    return load(file);
  });
  const zone = $(zoneId);
  function dragOver(e) {
    e.preventDefault();
    const hasFiles = e.dataTransfer.types.includes('Files');
    e.dataTransfer.dropEffect = hasFiles ? 'copy' : 'none';
    zone.classList.toggle('is-dragging', hasFiles);
  }
  zone.addEventListener('dragenter', dragOver);
  zone.addEventListener('dragover', dragOver);
  zone.addEventListener('dragleave', e => {
    if (!zone.contains(e.relatedTarget)) zone.classList.remove('is-dragging');
  });
  zone.addEventListener('drop', e => {
    e.preventDefault();
    zone.classList.remove('is-dragging');
    const transfer = e.dataTransfer;
    if (!transfer.types.includes('Files')) return;
    if (transfer.files.length !== 1 || transfer.items?.[0]?.webkitGetAsEntry?.()?.isDirectory) {
      return rejectDrop();
    }
    return load(transfer.files[0]);
  });
}
