# LLM Stress Tester

Farklı LLM sağlayıcılarının (OpenRouter, OpenAI, Anthropic, Gemini, Grok) API'lerini
eşzamanlı isteklerle yük testine sokan, performans/gecikme/kararlılık ve
maliyet metriklerini ölçen, isteğe bağlı yanıt kaydı tutan ve sonuçları
görselleştiren test aracı.

## Kurulum

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

OpenRouter kullanacaksan `.env.example` dosyasını `.env` adıyla kopyala ve
anahtarını ekle:

```env
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_MODEL=openrouter/free
```

`OPENROUTER_MODEL` tek model ayarıdır; model değiştirmek için yalnızca bu
değeri güncellemen yeterlidir. `.env` Git tarafından yok sayılır ve anahtar
arayüze gönderilmez.

## Kullanım

### 1) Dashboard (önerilen — FAZ 3/4 dahil)

```bash
streamlit run app.py
```

Tarayıcıda açılan panelden provider/API anahtarı/model/concurrency/prompt gibi
parametreleri gir, "Testi Başlat"a bas. OpenRouter anahtarı maskeli alandan
girilebilir ve kaynak koda kaydedilmez; `.env` ayarı isteğe bağlı yedek olarak
desteklenir. Sonuçlar: metrik kartları, eşzamanlı
istek zaman çizelgesi, throughput grafiği, (birden fazla koşu yapılırsa)
provider karşılaştırma grafiği, yanıt inceleme paneli (Yanıtları Kaydet
açıksa) ve JSON/CSV/HTML export butonları.

### 2) CLI (hızlı doğrulama / otomasyon için)

```bash
python main.py --provider openai --api-key sk-... --model gpt-4o \
  --prompt "500 kelimelik bir makale yaz" --concurrency 5 --total 20 \
  --output sonuc.json
```

OpenRouter için `.env` hazırsa anahtar ve model argümanları gerekmez:

```bash
python main.py --provider openrouter --prompt "Kısa bir performans testi" --total 20
```

## Proje Yapısı

| Dosya | Sorumluluk |
|---|---|
| `config.py` | `TestConfig`, `RequestResult` veri modelleri |
| `providers/` | Sağlayıcı adaptörleri (openrouter, openai, anthropic, gemini, grok) — yenisini eklemek için `base.py`'yi miras al |
| `engine.py` | Core async engine: concurrency (semaphore), ramp-up, T0/T1/T2 zamanlama, streaming/non-streaming |
| `tokenizer.py` | Gerçek `usage` verisi yoksa tiktoken ile yaklaşık token sayımı |
| `metrics.py` | Success rate, min/max/avg, P50/P90/P99, TTFT, TPS hesaplama |
| `chart_data.py` | Dashboard grafikleri için DataFrame hazırlama |
| `logger.py` | JSON export |
| `exporters.py` | CSV ve HTML rapor export |
| `app.py` | Streamlit dashboard (FAZ 3 + FAZ 4 export butonları) |
| `main.py` | CLI giriş noktası |

## Notlar / Bilinen Sınırlamalar

- Streaming yanıtlarda token sayımı tiktoken ile YAKLAŞIK yapılır (sağlayıcılar
  streaming'de kesin usage'ı farklı şekillerde döner); streaming olmayan
  isteklerde sağlayıcının döndürdüğü KESİN `usage` alanı kullanılır.
- Gemini/Anthropic streaming ayrıştırması temel SSE formatına göre yazıldı;
  sağlayıcı API'lerinde değişiklik olursa `providers/*.py` güncellenmeli.
- Prompt dataset'i basit bir JSON string listesi olarak yüklenir
  (`["prompt 1", "prompt 2", ...]`) ve round-robin kullanılır.
