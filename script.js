function normalizeText(text) {
  if (!text || typeof text !== 'string') return '';
  const map = {
    'İ': 'i', 'I': 'i', 'ı': 'i', 'Ş': 's', 'ş': 's', 'Ğ': 'g', 'ğ': 'g',
    'Ü': 'u', 'ü': 'u', 'Ö': 'o', 'ö': 'o', 'Ç': 'c', 'ç': 'c'
  };
  let normalized = text.replace(/[\u0130IıŞşĞğÜüÖöÇç]/g, c => map[c] || c);
  normalized = normalized.replace(/[^a-zA-Z0-9\s]/g, ''); // özel karakterleri sil
  return normalized.toLowerCase();
}

let files = [];

async function loadFiles() {
  try {
    const res = await fetch('files.json');
    files = await res.json();
    console.log('Dosyalar yüklendi:', files);
  } catch (e) {
    console.error('Dosyalar yüklenemedi:', e);
  }
}

function searchFiles(query) {
  const q = normalizeText(query);
  if (!q) return [];
  return files.filter(f => {
    const name = normalizeText(f.name || '');
    return name.includes(q);
  });
}

function renderResults(results) {
  const resultsEl = document.getElementById('results');
  resultsEl.innerHTML = '';
  if (results.length === 0) {
    resultsEl.innerHTML = '<li>Sonuç bulunamadı.</li>';
    return;
  }
  for (const file of results) {
    const li = document.createElement('li');
    const a = document.createElement('a');
    a.href = file.link;
    a.target = '_blank';
    a.rel = 'noopener noreferrer';
    a.textContent = file.name;
    li.appendChild(a);
    resultsEl.appendChild(li);
  }
}

document.getElementById('searchInput').addEventListener('input', (e) => {
  const results = searchFiles(e.target.value);
  renderResults(results);
});

window.addEventListener('load', loadFiles);
