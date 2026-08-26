import argparse
from .backends import create_backend
from .config import DB_PATH, DOCUMENTS_PATH, MIN_SCORE, TOP_K
from .database import KnowledgeDB
from .rag import RAGService


def parser():
    result = argparse.ArgumentParser(description="LocalMind yerel RAG asistanı")
    result.add_argument("command", nargs="?", choices=["ingest", "cli", "web"], default="web")
    result.add_argument("path", nargs="?", default=str(DOCUMENTS_PATH))
    result.add_argument("--backend", choices=["local", "foundry"], default="local")
    result.add_argument("--host", default="127.0.0.1")
    result.add_argument("--port", type=int, default=8000)
    return result


def main():
    args = parser().parse_args()
    backend = create_backend(args.backend)
    service = RAGService(KnowledgeDB(DB_PATH), backend, TOP_K, MIN_SCORE)
    try:
        if args.command == "ingest":
            from pathlib import Path
            result = service.ingest_path(Path(args.path))
            print(f"Tamamlandı: {result['files']} belge, {result['chunks']} parça indekslendi.")
            for item in result["skipped"]:
                print(f"Atlandı: {item['source']} — {item['reason']}")
        elif args.command == "cli":
            if service.ensure_index_compatible(DOCUMENTS_PATH):
                print(f"Bilgi tabanı {backend.name} için hazırlandı.")
            print("LocalMind hazır. Çıkmak için 'çık' yazın.")
            while True:
                question = input("\nSoru: ").strip()
                if question.lower() in {"çık", "quit", "exit"}:
                    break
                result = service.ask(question)
                print(f"Cevap: {result['answer']}")
        else:
            if service.ensure_index_compatible(DOCUMENTS_PATH):
                print(f"Bilgi tabanı {backend.name} için hazırlandı.")
            from .web import serve
            serve(service, args.host, args.port)
    finally:
        backend.close()
