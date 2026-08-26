# Microsoft Foundry Local

Microsoft Foundry Local, yapay zekâ modellerini bulut bağlantısı ve Azure aboneliği gerektirmeden doğrudan kullanıcının cihazında çalıştıran yerel bir yapay zekâ çözümüdür. Model kataloğundaki optimize edilmiş modelleri indirir, yönetir ve ONNX Runtime üzerinden CPU, GPU veya NPU gibi uygun donanımı otomatik olarak kullanır. Model ilk kez indirildikten sonra çıkarım tamamen çevrimdışı yapılabilir; soru ve belgeler cihazdan dışarı gönderilmez.

Foundry Local SDK; Python, C#, JavaScript ve Rust dillerini destekler. Python tarafında `Configuration` ve `FoundryLocalManager` ile sistem başlatılır. Bu projede hızlı sohbet modeli olarak `qwen2.5-0.5b`, embedding modeli olarak `qwen3-embedding-0.6b` kullanılır. Model bağlam dışına çıkarsa sistem kaynak cümlelerine geri döner.

Yerel çalışma gizlilik, düşük gecikme, internet kesintilerinden etkilenmeme ve bulut API maliyeti olmaması gibi avantajlar sunar. İlk model indirmesi internet gerektirir ve yerel cihazın belleği ile işlem gücü cevap hızını etkiler.
