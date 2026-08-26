# RAG ve Vektör Arama

Retrieval-Augmented Generation (RAG), üretken model cevaplarını özel belgelerdeki bilgiyle temellendiren bir tasarım desenidir. Üç temel adımı vardır: Retrieve aşamasında soruyla ilgili metin parçaları aranır; Augment aşamasında bulunan parçalar model istemine bağlam olarak eklenir; Generate aşamasında dil modeli yalnızca bu bağlamdan yararlanarak cevap üretir. Böylece halüsinasyon azalır, güncel veya kuruma özel bilgiler kullanılabilir ve kaynak gösterilebilir.

Vektör, bir metni bilgisayarın karşılaştırabileceği sayı dizisi biçiminde temsil eden yapıdır. Bu projede vektörler kelimelerin yalnızca yazılışını değil, metnin anlamını da sayısal olarak ifade eder.

Embedding, bir metnin anlamını sayısal bir vektöre dönüştürme işlemidir. Anlamca benzer metinlerin vektörleri birbirine yakın olur. Soru ve belge parçaları aynı embedding modeliyle vektöre çevrilir. Cosine benzerliği iki vektör arasındaki açıyı ölçer; 1'e yakın skor yüksek benzerliğe işaret eder. LocalMind tüm adayları puanlar ve en yüksek skorlu üç parçayı modele bağlam olarak gönderir.

Belgeler yaklaşık 900 karakterlik ve 120 karakter örtüşmeli parçalara ayrılır. Örtüşme, bölüm sınırındaki bilginin kaybolmasını önler. Çok küçük parçalar bağlamı kaybettirebilir; çok büyük parçalar ise alakasız bilgi taşıyıp modelin dikkatini dağıtabilir.
