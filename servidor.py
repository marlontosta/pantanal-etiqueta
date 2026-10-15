#!/usr/bin/env python3
"""Servidor local para testar a etiqueta. Uso: python3 servidor.py [porta]"""
import functools
import http.server
import pathlib
import socket
import sys

PORTA = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
PASTA = pathlib.Path(__file__).resolve().parent / "public"
EXEMPLO = "?placa=LMV4G22&oleo-km=95178&oleo-dt=2026-10-15&rev-km=95178&rev-dt=2026-10-15&geo-km=95178&geo-dt=2026-10-15"


def ip_da_rede():
    # Descobre o IP da máquina na rede local (não envia nada).
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(PASTA))
with http.server.ThreadingHTTPServer(("0.0.0.0", PORTA), handler) as srv:
    ip = ip_da_rede()
    print(f"Página do cliente:  http://localhost:{PORTA}/{EXEMPLO}")
    print(f"Área da oficina:    http://localhost:{PORTA}/gravar.html")
    print(f"Pelo celular (mesma rede Wi-Fi): http://{ip}:{PORTA}/{EXEMPLO}")
    print("Ctrl+C para parar.")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
