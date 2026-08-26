import tempfile
import unittest
from pathlib import Path
from localmind.backends import LocalBackend
from localmind.database import KnowledgeDB
from localmind.rag import RAGService, cosine_similarity
from localmind.text import chunk_text


class LocalMindTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = KnowledgeDB(Path(self.temp.name) / "test.db")
        self.service = RAGService(self.db, LocalBackend(), min_score=0.08)
        chunks = ["SQLite ayrı sunucu gerektirmeyen tek dosyalı bir veritabanıdır.", "RAG retrieve, augment ve generate adımlarından oluşur."]
        self.db.replace_source("test.md", chunks, self.service.backend.embed_many(chunks))

    def tearDown(self):
        self.temp.cleanup()

    def test_cosine(self):
        self.assertAlmostEqual(cosine_similarity([1, 0], [1, 0]), 1)
        self.assertEqual(cosine_similarity([1, 0], [0, 1]), 0)

    def test_chunking(self):
        self.assertEqual(chunk_text(""), [])
        self.assertGreaterEqual(len(chunk_text("Birinci bölüm.\n\nİkinci bölüm.")), 1)

    def test_retrieves_relevant_source(self):
        result = self.service.ask("SQLite neden ayrı sunucu gerektirmez?")
        self.assertIn("SQLite", result["answer"])
        self.assertEqual(result["sources"][0]["source"], "test.md")

    def test_unknown_question_falls_back(self):
        result = self.service.ask("Mars kolonisinde kaç astronot var?")
        self.assertEqual(result["answer"], "Bu bilgi yüklenen belgelerde bulunmuyor.")

    def test_empty_question_is_rejected(self):
        with self.assertRaises(ValueError):
            self.service.ask("   ")

    def test_help_question_lists_topics(self):
        result = self.service.ask("Ne sorabilirim?")
        self.assertIn("Şunları sorabilirsin", result["answer"])
        self.assertIn("test.md", result["answer"])
        self.assertEqual(result["sources"], [])

    def test_confusion_message_shows_help(self):
        result = self.service.ask("Anlamıyorum")
        self.assertIn("Şunları sorabilirsin", result["answer"])

    def test_unknown_question_hides_irrelevant_sources(self):
        result = self.service.ask("Ay yüzeyindeki hava bugün nasıl?")
        self.assertEqual(result["sources"], [])

    def test_answer_hides_retrieved_but_uncited_sources(self):
        self.db.replace_source(
            "irrelevant.md",
            ["SQLite ifadesi burada geçer ancak ayrı sunucu sorusunu açıklamaz."],
            self.service.backend.embed_many(["SQLite ifadesi burada geçer ancak ayrı sunucu sorusunu açıklamaz."]),
        )
        self.service.backend.answer = lambda question, results: (
            "SQLite tek dosyalıdır. [test.md · parça 1]"
        )
        result = self.service.ask("SQLite neden ayrı sunucu gerektirmez?")
        cited_names = {source["source"] for source in result["sources"]}
        self.assertIn("test.md", cited_names)
        self.assertNotIn("irrelevant.md", cited_names)

    def test_summary_question_uses_latest_document(self):
        result = self.service.ask("Bu belge ne anlatıyor?")
        self.assertIn("belgesinin özeti", result["answer"])
        self.assertTrue(result["sources"])
        self.assertEqual(result["sources"][0]["source"], "test.md")

    def test_summary_question_tolerates_common_typo(self):
        result = self.service.ask("ne analatıyor")
        self.assertIn("belgesinin özeti", result["answer"])

    def test_directory_ingest_skips_unreadable_file(self):
        folder = Path(self.temp.name) / "docs"
        folder.mkdir()
        (folder / "usable.md").write_text("SQLite yerel bir veritabanıdır.", encoding="utf-8")
        (folder / "broken.pdf").write_bytes(b"not a real pdf")
        result = self.service.ingest_path(folder)
        self.assertEqual(result["files"], 1)
        self.assertEqual(len(result["skipped"]), 1)
        self.assertEqual(result["skipped"][0]["source"], "broken.pdf")

    def test_markdown_heading_is_not_repeated_in_answer(self):
        chunks = ["# Microsoft Foundry Local\n\nMicrosoft Foundry Local cihaz üzerinde çalışır."]
        self.db.replace_source("heading.md", chunks, self.service.backend.embed_many(chunks))
        result = self.service.ask("Microsoft Foundry Local nerede çalışır?")
        self.assertNotIn("Microsoft Foundry Local Microsoft Foundry Local", result["answer"])

    def test_definition_question_prefers_direct_definition(self):
        chunks = [
            "Milyonlarca kayıt için vektör veritabanı uygundur.",
            "Vektör, metni sayı dizisi biçiminde temsil eden bir yapıdır.",
        ]
        self.db.replace_source("vector.md", chunks, self.service.backend.embed_many(chunks))
        result = self.service.ask("Vektör ne?")
        self.assertTrue(result["answer"].startswith("Vektör, metni sayı dizisi"))

    def test_directory_reingest_removes_stale_sources(self):
        folder = Path(self.temp.name) / "sync-docs"
        folder.mkdir()
        document = folder / "current.md"
        document.write_text("Geçerli bilgi belgesi.", encoding="utf-8")
        self.service.ingest_path(folder)
        self.assertEqual({row["source"] for row in self.db.all_chunks()}, {"current.md"})

    def test_incompatible_embedding_index_is_rebuilt(self):
        folder = Path(self.temp.name) / "dimension-docs"
        folder.mkdir()
        (folder / "current.md").write_text("Foundry Local cihazda çalışır.", encoding="utf-8")
        self.db.replace_source("old.md", ["eski"], [[1.0, 0.0]])
        rebuilt = self.service.ensure_index_compatible(folder)
        self.assertTrue(rebuilt)
        self.assertEqual(len(self.db.all_chunks()[0]["embedding"]), self.service.backend.dimensions)


if __name__ == "__main__":
    unittest.main()
