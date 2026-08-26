import hashlib
import math
import re
from collections import Counter


STOP_WORDS = {"ve", "veya", "ile", "bu", "bir", "için", "da", "de", "mi", "ne", "nedir", "nasıl", "the", "is", "a", "of", "to"}


def tokens(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-zçğıöşü0-9]+", text.lower()) if len(w) > 1 and w not in STOP_WORDS]


class LocalBackend:
    """Dependency-free deterministic backend for offline demos and tests."""
    name = "Yerel demo"
    dimensions = 384

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(text) for text in texts]

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        words = tokens(text)
        features = words + [f"{a}_{b}" for a, b in zip(words, words[1:])]
        for feature, count in Counter(features).items():
            digest = hashlib.blake2b(feature.encode(), digest_size=8).digest()
            value = int.from_bytes(digest, "big")
            vector[value % self.dimensions] += count * (1 if value & 1 else -1)
        norm = math.sqrt(sum(x * x for x in vector)) or 1
        return [x / norm for x in vector]

    def answer(self, question: str, results: list[dict]) -> str:
        query_words = set(tokens(question))
        normalized_question = re.sub(r"[^a-zçğıöşü0-9 ]", "", question.lower())
        definition_query = " nedir" in f" {normalized_question}" or normalized_question.endswith(" ne")
        candidates = []
        sequence = 0
        for result_rank, result in enumerate(results):
            clean_content = re.sub(r"\s+", " ", result["content"]).strip()
            clean_content = re.sub(r"^#{1,6}\s*", "", clean_content)
            # Chunking can place a Markdown heading directly before a sentence
            # that starts with the same title; collapse that duplicated prefix.
            clean_content = re.sub(r"^(.{3,80}?)\s+\1(?=[,.;:!?]|\s)", r"\1", clean_content, count=1)
            for sentence_rank, sentence in enumerate(re.split(r"(?<=[.!?])\s+", clean_content)):
                sentence = re.sub(r"^#+\s*", "", sentence).strip()
                sentence_words = set(tokens(sentence))
                overlap = len(query_words & sentence_words)
                if overlap and not sentence.startswith("http") and len(sentence) >= 35:
                    lexical = overlap / max(1, len(query_words))
                    retrieval = float(result.get("score", 0.0))
                    definition_bonus = 0.0
                    if definition_query and any(
                        re.match(rf"^{re.escape(word)}\s*[,;:]?\s+(?:bir|metni|metnin|sayısal)", sentence.lower())
                        for word in query_words
                    ):
                        definition_bonus = 3.0
                    priority = lexical * 3 + retrieval + definition_bonus - result_rank * 0.12 - sentence_rank * 0.015
                    candidates.append((priority, sequence, sentence, result["source"], result["chunk_index"]))
                    sequence += 1
        candidates.sort(key=lambda item: (-item[0], item[1]))
        if not candidates:
            return "Bu bilgi yüklenen belgelerde bulunmuyor."
        selected, seen = [], set()
        for _, _, sentence, source, index in candidates:
            if sentence not in seen:
                selected.append(f"{sentence} [{source} · parça {index}]")
                seen.add(sentence)
            if len(selected) == (1 if definition_query else 2):
                break
        return " ".join(selected)

    def summarize(self, results: list[dict]) -> str:
        if not results:
            return "Özetlenecek bir belge bulunmuyor."
        sentences = []
        sentence_tokens = []
        for result in results:
            clean = re.sub(r"\s+", " ", result["content"]).strip()
            for sentence in re.split(r"(?<=[.!?])\s+", clean):
                sentence = sentence.strip(" #-•")
                words = set(tokens(sentence))
                is_duplicate = any(
                    len(words & previous) / max(1, min(len(words), len(previous))) > 0.72
                    for previous in sentence_tokens
                )
                if 45 <= len(sentence) <= 650 and sentence not in sentences and not is_duplicate:
                    sentences.append(sentence)
                    sentence_tokens.append(words)
                if len(sentences) == 4:
                    break
            if len(sentences) == 4:
                break
        source = results[0]["source"]
        if not sentences:
            sentences = [results[0]["content"][:600].strip()]
        return f'“{source}” belgesinin özeti:\n\n' + " ".join(sentences) + f" [{source}]"

    def close(self):
        pass


class FoundryBackend:
    name = "Microsoft Foundry Local"

    def __init__(self):
        try:
            from foundry_local_sdk import Configuration, FoundryLocalManager
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "Foundry Local SDK bu Python ortamında bulunamadı. "
                "macOS/Linux için şu komutu kullanın: "
                "'.venv/bin/python main.py web --backend foundry'"
            ) from exc
        from .config import CHAT_MODEL, EMBEDDING_MODEL
        FoundryLocalManager.initialize(Configuration(app_name="localmind_rag"))
        self.manager = FoundryLocalManager.instance
        self.embedding_model = self.manager.catalog.get_model(EMBEDDING_MODEL)
        self.embedding_model.download()
        self.embedding_model.load()
        self.embedding_client = self.embedding_model.get_embedding_client()
        self.chat_model = self.manager.catalog.get_model(CHAT_MODEL)
        self.chat_model.download()
        self.chat_model.load()
        self.chat_client = self.chat_model.get_chat_client()
        self.chat_client.settings.temperature = 0.0
        self.chat_client.settings.top_p = 0.8
        self.chat_client.settings.max_tokens = 280
        self.chat_client.settings.random_seed = 42

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        response = self.embedding_client.generate_embeddings(texts)
        return [item.embedding for item in response.data]

    def embed(self, text: str) -> list[float]:
        return self.embedding_client.generate_embedding(text).data[0].embedding

    def answer(self, question: str, results: list[dict]) -> str:
        context = "\n\n".join(
            f"KAYNAK {i}: {r['source']}, parça {r['chunk_index']}\n{r['content']}"
            for i, r in enumerate(results, 1)
        )
        messages = [{"role": "system", "content": (
            "Sen LocalMind adlı Türkçe bir belge asistanısın. Aşağıdaki kurallara kesinlikle uy:\n"
            "1. Yalnızca BAĞLAM içinde açıkça yazan gerçekleri kullan.\n"
            "2. Bağlamda olmayan hiçbir ayrıntı, yorum veya örnek ekleme.\n"
            "3. En fazla üç kısa Türkçe cümle yaz.\n"
            "4. Her cümlenin sonuna dayandığı [Kaynak N] etiketini ekle.\n"
            "5. Cevap bağlamda yoksa yalnızca 'Bu bilgi yüklenen belgelerde bulunmuyor.' yaz.\n\n"
            "BAĞLAM:\n" + context
        )}, {"role": "user", "content": question}]
        response = self.chat_client.complete_chat(messages)
        generated = (response.choices[0].message.content or "").strip()
        # Small on-device models can occasionally drift beyond the supplied context.
        # Reject an ungrounded/verbose generation and return exact source sentences.
        context_words = set(tokens(" ".join(r["content"] for r in results)))
        answer_words = tokens(generated)
        grounded_ratio = sum(word in context_words for word in answer_words) / max(1, len(answer_words))
        if not generated or len(generated) > 900 or grounded_ratio < 0.62:
            return LocalBackend().answer(question, results)
        return generated

    def summarize(self, results: list[dict]) -> str:
        return LocalBackend().summarize(results)

    def close(self):
        self.embedding_model.unload()
        self.chat_model.unload()


def create_backend(kind: str):
    if kind == "foundry":
        return FoundryBackend()
    return LocalBackend()
