#!/usr/bin/env python3
"""
Servidor Local para Site Baixado via DeepMirror-WebSites
Escolha entre versão RAW ou CLEAN do site.

Uso:
    python3 serve.py
    python serve.py

Requisitos: Python 3.7+
"""
import os
import sys
import subprocess
from pathlib import Path


def main():
    print("=" * 60)
    print("DeepMirror WebSites - Seletor de Versão")
    print("=" * 60)
    print("\\nQual versão do site você deseja visualizar?\\n")
    print("1. RAW   - Versão completa com todos os recursos")
    print("2. CLEAN - Versão otimizada para IA (sem canvas/scripts)")
    print("\\n" + "=" * 60)

    while True:
        choice = input("\\nEscolha (1/2): ").strip()

        if choice == "1":
            folder = "raw"
            break
        elif choice == "2":
            folder = "clean"
            break
        else:
            print("Opção inválida. Digite 1 ou 2.")

    # Get path to serve.py in selected folder
    serve_path = Path(__file__).parent / folder / "serve.py"

    if not serve_path.exists():
        print(f"\\nErro: Arquivo {serve_path} não encontrado!")
        sys.exit(1)

    print(f"\\nIniciando versão {folder.upper()}...\\n")

    # Execute the serve.py in the selected folder
    try:
        subprocess.run([sys.executable, str(serve_path)])
    except KeyboardInterrupt:
        print("\\n\\nServidor encerrado pelo usuário.")
        sys.exit(0)


if __name__ == "__main__":
    main()