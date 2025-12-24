import requests
import json
import sys
import os

# Config dosyasını yükle
try:
    with open('config.json', 'r') as f:
        CONFIG = json.load(f)
except FileNotFoundError:
    print("Hata: config.json dosyası bulunamadı.")
    sys.exit(1)

# API anahtarını ortam değişkeninden al (güvenlik için)
# Ortam değişkeni yoksa config.json'dan okur
CONFIG['api_key'] = os.getenv('OPENROUTER_API_KEY', CONFIG.get('api_key', ''))

def call_llm(prompt: str) -> str:
    headers = {
        "Authorization": f"Bearer {CONFIG['api_key']}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://localhost:3000", # OpenRouter istatistikleri için (zorunlu değil)
        "X-Title": "Veritabani Ajani"
    }

    # OpenRouter (OpenAI Uyumlu) Formatı
    data = {
        "model": CONFIG["model"],
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1 # Kodlama için düşük sıcaklık iyidir
    }

    try:
        response = requests.post(CONFIG["base_url"], headers=headers, json=data)
        response.raise_for_status()
        
        # Yanıtı parse et (OpenAI formatı: choices -> message -> content)
        json_response = response.json()
        
        if 'choices' in json_response and len(json_response['choices']) > 0:
            return json_response['choices'][0]['message']['content']
        else:
            return f"Hata: API boş yanıt döndü. {json_response}"

    except Exception as e:
        return f"API Bağlantı Hatası: {str(e)}"

class LLMExplorer:
    def __init__(self, db):
        self.db = db

    def explore(self):
        # Ham şema verisini al
        raw_schema = self.db.get_schema()
        # LLM'e bunu özetlettir (Token tasarrufu ve anlamlandırma için)
        prompt = f"""Sen bir veritabanı haritalayıcısısın. Aşağıdaki ham şema bilgisini analiz et.
Hangi tabloların birbiriyle ilişkili olabileceğini (ID'lere bakarak) ve tabloların amaçlarını özetle.

Ham Şema:
{json.dumps(raw_schema, indent=2)}

Çıktı sadece özet olsun."""
        print(">> Explorer: Veritabanı haritası çıkarılıyor...")
        return call_llm(prompt)

class LLMPlanner:
    def plan(self, request: str, schema_summary: str):
        prompt = f"""Sen uzman bir SQL stratejistisin.
GÖREV: Kullanıcı isteğini veritabanı şemasına uygun mantıksal adımlara böl.

BAĞLAM (Veritabanı Yapısı):
{schema_summary}

KULLANICI İSTEĞİ: "{request}"

Sadece adımları listele (1., 2., 3. gibi). SQL kodu yazma."""
        return call_llm(prompt)

class LLMCoder:
    def generate_code(self, request: str, plan: str, full_schema: dict, previous_error: str = ""):
        # Şemayı stringe çevir
        schema_str = json.dumps(full_schema, indent=2)
        
        prompt = f"""Sen bir SQL uzmanısın (SQLite Dialect).
GÖREV: Planı takip ederek SQL sorgusu yaz.

ŞEMA:
{schema_str}

PLAN:
{plan}

KULLANICI İSTEĞİ:
{request}

{f"DİKKAT! Önceki denemede şu hata alındı, bunu düzelt: {previous_error}" if previous_error else ""}

KURALLAR:
1. Sadece tek bir SQL sorgusu döndür.
2. Markdown blokları (```sql) kullanma, sadece saf SQL metni ver.
3. Asla açıklama yazma.
"""
        response = call_llm(prompt)
        # Temizlik
        clean_sql = response.replace("```sql", "").replace("```", "").strip()
        return clean_sql

class LLMVerifier:
    def verify(self, request: str, sql_result, sql_query: str):
        # 1. Güvenlik ve Teknik Kontrol
        if isinstance(sql_result, str) and "SQL Hatası" in sql_result:
            return False, sql_result # Doğrudan hata mesajını döndür

        # 2. Mantıksal Kontrol (LLM)
        # Veri çok büyükse sadece başını gösterelim (Token limiti yememek için)
        data_preview = str(sql_result)[:1000]
        
        prompt = f"""Sen bir denetçisin. Aşağıdaki SQL sonucu kullanıcı isteğini karşılıyor mu?

Kullanıcı İsteği: "{request}"
Çalıştırılan SQL: "{sql_query}"
Dönen Sonuç (Önizleme): {data_preview}

Karar ver:
- Sonuç boş mu? -> YETERSİZ
- Sonuç istekle alakasız mı? -> YETERSİZ
- Sonuç mantıklı mı? -> YETERLİ

Format:
Eğer uygunsa sadece "YETERLİ" yaz.
Değilse "YETERSİZ: [Kısa Neden]" yaz.
"""
        response = call_llm(prompt)
        if "YETERLİ" in response.upper() and "YETERSİZ" not in response.upper():
            return True, "Onaylandı"
        else:
            return False, response