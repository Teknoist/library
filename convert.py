import re
import os
import json

input_file = "links.txt"  # giriş dosyası
output_file = "files.json"  # çıkış dosyası

with open(input_file, "r", encoding="utf-8") as f:
    input_text = f.read()

pattern = r"Exported\s+(.*?):\s+(https?://\S+)"
matches = re.findall(pattern, input_text)

data = []
for full_path, url in matches:
    filename = os.path.basename(full_path.strip())
    if filename.lower().endswith(".zip"):
        filename = filename[:-4]  # .zip uzantısını kaldır
    data.append({
        "name": filename,
        "download_url": url.strip()
    })

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"{output_file} dosyası oluşturuldu.")
