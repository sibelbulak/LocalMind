# LocalMind — Microsoft Foundry Local RAG Asistanı

LocalMind; belgeleri parçalara ayıran, embedding'leri SQLite'ta saklayan, cosine benzerliği ile ilgili parçaları bulan ve Microsoft Foundry Local modeliyle kaynaklı cevap üreten tamamen yerel bir RAG uygulamasıdır.

## Hızlı başlangıç (internetsiz demo)

Python 3.11+ yeterlidir; ek paket gerekmez:

```bash
python3 main.py ingest
python3 main.py web
```

Tarayıcıdan `http://127.0.0.1:8000` adresini açın. Bu mod hash tabanlı yerel embedding ve extractive cevap üretici kullanır; sunum/demo için model indirmeden çalışır.

Web arayüzündeki **Belge yükle** düğmesiyle veya dosyayı sayfaya sürükleyerek `.txt`, `.md` ve `.pdf` belgeleri ekleyebilirsiniz. Yüklenen belge otomatik olarak parçalanır ve yeniden indekslenir. PDF desteği `requirements.txt` içindeki `pypdf` paketiyle sağlanır.

## Foundry Local ile gerçek model modu

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py web --backend foundry
```

Windows'ta `foundry-local-sdk` yerine `foundry-local-sdk-winml` kurun. İlk çalıştırmada `qwen3-embedding-0.6b` ve `qwen2.5-0.5b` modelleri indirilir; sonraki kullanımlar tamamen yereldir. Bilgisayarda en az 8 GB RAM önerilir.

Uygulama, mevcut indeksin farklı bir embedding backend'iyle oluşturulduğunu algılarsa `documents/` klasörünü otomatik olarak yeniden indeksler. Bu nedenle `local` ve `foundry` modları arasında geçerken veritabanını elle silmeniz gerekmez.

## Kullanım

```bash
# Belge ekle (.txt/.md)
python main.py ingest documents

# Terminal arayüzü
python main.py cli

# Testler
python -m unittest discover -s tests -v
```

Yeni bilgi belgelerini `documents/` içine koyup ingest komutunu tekrar çalıştırın. Aynı dosyanın eski parçaları otomatik yenilenir; klasörden çıkarılan belgeler indeksten de kaldırılır. Proje planı gibi uygulamanın cevap vermemesi gereken referanslar `project_reference/` altında tutulur.

## Mimari

1. **Ingestion:** Belgeler yaklaşık 900 karakterlik örtüşen parçalara ayrılır.
2. **Embedding:** Foundry Local embedding modeli (veya demosu kolay hash backend) metni vektöre çevirir.
3. **Depolama:** Metin, kaynak, sıra ve JSON vektörleri `data/knowledge.db` içinde tutulur.
4. **Retrieval:** Soru embedding'i tüm kayıtlarla cosine benzerliğine göre sıralanır; en iyi 3 parça seçilir.
5. **Generation:** Bağlam ve soru, yalnızca verilen kaynaklara dayanma talimatıyla yerel chat modeline gönderilir.
6. **Citations:** Cevapla birlikte kaynak adı, parça numarası ve benzerlik skoru gösterilir.

## Örnek sorular

- Foundry Local nedir ve neden kullanılır?
- RAG hangi üç adımdan oluşur?
- Embedding ve cosine benzerliği ne işe yarar?
- SQLite neden bu proje için uygun?
- Sistem internete veri gönderiyor mu?
- Mars'ta kaç koloni var? *(bilgi yok davranışını gösterir)*

## Tasarım kararları ve sınırlamalar

- Küçük belge kümelerinde anlaşılır olması için vektörler SQLite'tan okunup benzerlik Python'da hesaplanır.
- `local` backend semantik model değildir; anahtar sözcük tabanlı, deterministik bir demo/yedek moddur. En kaliteli sonuç için `foundry` kullanın.
- PDF alımı için isteğe bağlı `pypdf` gerekir; temel proje `.txt` ve `.md` dosyalarını bağımlılıksız işler.
- Veriler ve çıkarım yerelde kalır; Foundry modellerinin ilk indirilmesi için internet gerekir.

## Proje yapısı

```text
main.py                 Komut satırı giriş noktası
localmind/              RAG, veri tabanı, embedding/model katmanları ve web sunucusu
static/                 Tek sayfalık kullanıcı arayüzü
documents/              Örnek bilgi tabanı
tests/                  Birim ve uçtan uca testler
VIDEO_SCRIPT.md         Hazır video anlatım metni
```

Uygulama, Microsoft'un resmi [Foundry Local RAG öğreticisindeki](https://learn.microsoft.com/en-us/azure/foundry-local/tutorials/tutorial-build-rag-app) SDK akışı temel alınarak hazırlanmıştır. Sohbet modeli olarak hızlı `qwen2.5-0.5b`, embedding modeli olarak `qwen3-embedding-0.6b` kullanılır. Küçük model bağlam dışına çıkarsa groundedness kontrolü cevabı reddeder ve doğrudan kaynak cümlelerinden güvenli bir cevap üretir.
