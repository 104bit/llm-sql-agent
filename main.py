# src klasörünün altından çağırmamız gerekiyor
from src.database import Database
from src.agents import LLMExplorer, LLMPlanner, LLMCoder, LLMVerifier
import time

def main():
    # 1. Başlatma
    try:
        db = Database()
        print("✅ Veritabanı bağlantısı başarılı.")
    except Exception as e:
        print(f"❌ Veritabanı hatası: {e}")
        return

    # 2. Keşif (Discovery) Aşaması
    # Bu aşama, ajanın "Neredeyim?" sorusuna cevap bulduğu yerdir.
    explorer = LLMExplorer(db)
    schema_summary = explorer.explore()
    full_schema = db.get_schema() # Coder için detaylı şema
    
    print("\n🗺️  VERİTABANI ÖZETİ (EXPLORER):")
    print("-" * 40)
    print(schema_summary)
    print("-" * 40)

    planner = LLMPlanner()
    coder = LLMCoder()
    verifier = LLMVerifier()

    # 3. Etkileşim Döngüsü
    while True:
        user_input = input("\n👤 İsteğiniz (Çıkış için 'q'): ")
        if user_input.lower() == 'q':
            break

        print("\n🧠 PLANNER: Düşünülüyor...")
        plan = planner.plan(user_input, schema_summary)
        print(f"📝 Plan:\n{plan}")

        # Self-Correction Döngüsü (Maksimum 3 deneme)
        max_retries = 3
        last_error = ""
        
        for attempt in range(max_retries):
            print(f"\n💻 CODER (Deneme {attempt + 1}/{max_retries}): SQL Yazılıyor...")
            sql = coder.generate_code(user_input, plan, full_schema, last_error)
            print(f"Generated SQL: {sql}")

            print("🚀 EXECUTOR: Çalıştırılıyor...")
            result = db.execute_query(sql)

            print("gözcü VERIFIER: Kontrol ediliyor...")
            is_valid, message = verifier.verify(user_input, result, sql)

            if is_valid:
                print("\n✅ SONUÇ BAŞARILI!")
                print("=" * 40)
                # Sonucu güzel yazdır
                if isinstance(result, dict):
                    print(f"Kolonlar: {result['columns']}")
                    for row in result['data']:
                        print(row)
                else:
                    print(result)
                print("=" * 40)
                break # Döngüden çık, yeni soruya geç
            else:
                print(f"⚠️ DOĞRULAMA BAŞARISIZ: {message}")
                last_error = message # Hatayı Coder'a geri besle (Feedback Loop)
                if attempt == max_retries - 1:
                    print("❌ Ajan bu sorunu çözemedi.")

    db.close()

if __name__ == "__main__":
    main()