"""Cria os usuários IC e associa cada UID RFID ao respectivo aluno.

Uso:
    python scripts/seed_ic_cards.py
    python scripts/seed_ic_cards.py --password 123456
    python scripts/seed_ic_cards.py --dry-run

O script assume que o projeto está no diretório raiz do repositório.
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from django.contrib.auth.models import Group, User  # noqa: E402

from app.models import CartaoRFID, PerfilUsuario  # noqa: E402


@dataclass(frozen=True)
class Aluno:
    first_name: str
    last_name: str
    username: str
    uid: str


ALUNOS = [
    Aluno("Luize", "Baldoni", "luize", "0417796A2F6481"),
    Aluno("Gabrielle", "Barcellos", "gabrielle", "047D4B6A2F6480"),
    Aluno("Lyncoln", "Jurich", "lyncoln", "0485EB622F6480"),
    Aluno("Eduarda", "Schossler", "eduarda", "04C6676A2F6480"),
    Aluno("Amanda", "Belitz", "amanda", "0472EA622F6480"),
]


def ensure_user(aluno: Aluno, password: str, dry_run: bool = False) -> User:
    user = User.objects.filter(username=aluno.username).first()
    if user:
        changed = False
        if user.first_name != aluno.first_name:
            user.first_name = aluno.first_name
            changed = True
        if user.last_name != aluno.last_name:
            user.last_name = aluno.last_name
            changed = True
        if not user.is_active:
            user.is_active = True
            changed = True
        if changed and not dry_run:
            user.save()
        if not dry_run:
            user.set_password(password)
            user.save(update_fields=["password"])
    else:
        user = User(
            username=aluno.username,
            first_name=aluno.first_name,
            last_name=aluno.last_name,
            is_active=True,
        )
        if not dry_run:
            user.set_password(password)
            user.save()

    return user


def ensure_role(user: User, dry_run: bool = False) -> None:
    if dry_run:
        return
    PerfilUsuario.objects.get_or_create(user=user, defaults={"role": PerfilUsuario.ROLE_IC})


def ensure_card(user: User, uid: str, dry_run: bool = False) -> CartaoRFID:
    cartao = CartaoRFID.objects.filter(uid=uid).first()
    if cartao:
        if cartao.usuario_id != user.id and not dry_run:
            cartao.usuario = user
            cartao.save(update_fields=["usuario"])
    else:
        if dry_run:
            return CartaoRFID(uid=uid, usuario=user)
        cartao = CartaoRFID.objects.create(uid=uid, usuario=user)
    return cartao


def main() -> int:
    parser = argparse.ArgumentParser(description="Cadastra alunos IC e associa UID RFID ao usuário.")
    parser.add_argument("--password", default="123456", help="Senha inicial para todos os alunos (default: 123456)")
    parser.add_argument("--dry-run", action="store_true", help="Mostra o que seria criado sem salvar no banco")
    args = parser.parse_args()

    grupo_ic, _ = Group.objects.get_or_create(name="ic")

    print("== Cadastro de alunos/UID ==")
    for aluno in ALUNOS:
        user = ensure_user(aluno, args.password, dry_run=args.dry_run)
        if not args.dry_run:
            user.groups.add(grupo_ic)
        ensure_role(user, dry_run=args.dry_run)
        ensure_card(user, aluno.uid, dry_run=args.dry_run)
        print(f"- {aluno.first_name} {aluno.last_name} -> {aluno.uid} ({aluno.username})")

    if args.dry_run:
        print("\nDry-run concluído: nada foi salvo.")
    else:
        print("\nCadastro concluído com sucesso.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

