let files = [];

// Türkçe karakterleri ve özel sembolleri normalize eden fonksiyon
function normalize(text) {
  if (!text || typeof text !== 'string') return '';
  const map = {
    'İ': 'i', 'I': 'i', 'ı': 'i', 'Ş': 's', 'ş': 's', 'Ğ': 'g', 'ğ': 'g',
    'Ü': 'u', 'ü': 'u', 'Ö': 'o', 'ö': 'o', 'Ç': 'c', 'ç': 'c'
  };
  let normalized = text.replace(/[\u0130IıŞşĞğÜüÖöÇç]/g, c => map[c] || c);
  normalized = normalized.replace(/[^a-zA-Z0-9\s]/g, ''); // özel karakterleri sil
  return normalized.toLowerCase();
}

// Arama fonksiyonu (sadece name üzerinden)
function searchFiles(query) {
  const q = normalize(query);
  if (!q || q === '*') return files;
  return files.filter(f => normalize(f.name || '').includes(q));
}

// Sonuçları ekrana yazdır
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
    a.href = file.download_url;
    a.target = '_blank';
    a.rel = 'noopener noreferrer';
    a.textContent = file.name;
    li.appendChild(a);
    resultsEl.appendChild(li);
  }
}

// JSON dosyasını yükle (cache bypass için zaman damgası ekliyoruz)
async function loadFiles() {
  try {
    const timestamp = Date.now(); // her seferinde farklı URL
    const res = await fetch(`files.json?v=${timestamp}`);
    files = await res.json();
    renderResults(files); // ilk yüklemede tüm dosyaları göster
  } catch (e) {
    document.getElementById('results').innerHTML = '<li>Dosya yüklenemedi.</li>';
    console.error('Dosya yükleme hatası:', e);
  }
}

// Sayfa yüklendiğinde başlat
document.addEventListener('DOMContentLoaded', () => {
  loadFiles();

  const searchInput = document.getElementById('searchInput');
  searchInput.addEventListener('input', () => {
    const query = searchInput.value;
    const results = searchFiles(query);
    renderResults(results);
  });

  // UX: Sayfa açıldığında arama kutusuna odaklan
  searchInput.focus();
});
