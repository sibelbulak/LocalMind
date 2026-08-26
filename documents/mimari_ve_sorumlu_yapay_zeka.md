# Uygulama Mimarisi ve Sorumlu Cevaplar

LocalMind dört katmandan oluşur. İstemci katmanı tarayıcı veya terminal arayüzüdür. RAG servis katmanı belge alımı, retrieval ve cevap üretimini yönetir. Veri katmanı SQLite veritabanında kaynak adını, parça sırasını, metni ve JSON biçimindeki embedding vektörünü saklar. Yapay zekâ katmanı Microsoft Foundry Local üzerinden embedding ve sohbet modellerini cihazda çalıştırır.

SQLite ayrı bir sunucu gerektirmeyen, tek dosyalı ve Python ile hazır gelen bir veritabanıdır. Bu nedenle küçük bir yerel bilgi tabanı için kurulumu kolay ve taşınabilirdir. Koleksiyon küçük olduğundan tüm embedding kayıtları okunup cosine benzerliği Python tarafında hesaplanır. Milyonlarca kayıt için özel bir vektör veritabanı veya SQLite vektör uzantısı daha uygun olur.

Sistem istemi modele yalnızca getirilen bağlamı kullanmasını, tahmin yapmamasını ve kullandığı kaynakları belirtmesini söyler. Yeterli bilgi yoksa uygulama “Bu bilgi yüklenen belgelerde bulunmuyor.” cevabını verir. Arayüz ayrıca bulunan kaynakları, parça numaralarını ve benzerlik skorlarını göstererek cevabın denetlenebilmesini sağlar.
