"""Gerenciar usuários da área da oficina.

  python -m app.usuarios criar marlon "Marlon Tosta"   (pede a senha)
  python -m app.usuarios senha marlon                 (troca a senha)
  python -m app.usuarios remover marlon
  python -m app.usuarios listar
"""
import getpass
import sys

from . import db, seguranca


def pedir_senha() -> str:
    while True:
        s = getpass.getpass("Senha (mínimo 8 caracteres): ")
        if len(s) < 8:
            print("Senha curta demais.")
        elif s != getpass.getpass("Repita a senha: "):
            print("As senhas não conferem.")
        else:
            return s


def main(args: list[str]) -> int:
    db.criar_tabelas()
    cmd = args[0] if args else ""
    with db.transacao() as con:
        if cmd == "listar":
            for u in con.execute("SELECT usuario, nome, criado_em FROM usuarios ORDER BY usuario"):
                print(f"{u['usuario']:<20} {u['nome']:<30} desde {u['criado_em'][:10]}")
            return 0
        if len(args) < 2:
            print(__doc__)
            return 1
        usuario = args[1]
        existe = con.execute("SELECT id FROM usuarios WHERE usuario = ?", (usuario,)).fetchone()
        if cmd == "criar":
            if existe:
                print("Usuário já existe.")
                return 1
            con.execute("INSERT INTO usuarios (usuario, nome, senha_hash) VALUES (?, ?, ?)",
                        (usuario, " ".join(args[2:]), seguranca.gerar_hash(pedir_senha())))
        elif cmd in ("senha", "remover") and not existe:
            print("Usuário não encontrado.")
            return 1
        elif cmd == "senha":
            con.execute("UPDATE usuarios SET senha_hash = ? WHERE id = ?", (seguranca.gerar_hash(pedir_senha()), existe["id"]))
            con.execute("DELETE FROM sessoes WHERE usuario_id = ?", (existe["id"],))
        elif cmd == "remover":
            con.execute("DELETE FROM usuarios WHERE id = ?", (existe["id"],))
        else:
            print(__doc__)
            return 1
    print("Feito.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
