let files = [];

// Küçük/büyük harf ve Türkçe karakter uyumlu normalize fonksiyonu
function normalize(text) {
  return text.toLowerCase()
    .replace(/İ/g, 'i')
    .replace(/I/g, 'ı')
    .normalize('NFD').replace(/[\u0300-\u036f]/g, "");
}

// Arama fonksiyonu
function searchFiles(files, query) {
  if (query.trim() === '*') return files;
  const q = normalize(query);
  return files.filter(f => normalize(f.name).includes(q) || normalize(f.brand).includes(q));
}

// Sonuçları güncelle
function updateResults() {
  const query = document.getElementById('searchInput').value;
  const results = searchFiles(files, query);

  const ul = document.getElementById('results');
  ul.innerHTML = '';

  if(results.length === 0) {
    ul.innerHTML = '<li>Sonuç bulunamadı.</li>';
    return;
  }

  results.forEach(f => {
    const li = document.createElement('li');

    const a = document.createElement('a');
    a.href = f.download_url;
    a.textContent = f.name;
    a.target = "_blank";
    li.appendChild(a);

    const brandSpan = document.createElement('span');
    brandSpan.className = 'brand';
    brandSpan.textContent = f.brand;
    li.appendChild(brandSpan);

    ul.appendChild(li);
  });
}

// JSON dosyasını yükle ve ilk listeyi göster
function loadFiles() {
  fetch('files.json')
    .then(response => response.json())
    .then(data => {
      files = data;
      updateResults();
    })
    .catch(() => {
      document.getElementById('results').innerHTML = '<li>Dosya yüklenemedi.</li>';
    });
}

// Sayfa yüklendiğinde dosyaları yükle ve arama inputuna event ata
document.addEventListener('DOMContentLoaded', () => {
  loadFiles();
  document.getElementById('searchInput').addEventListener('input', updateResults);
});
