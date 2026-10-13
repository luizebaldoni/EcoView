"""Sincroniza usuários, perfis e grupos autorizados no banco existente.

Esse script ajuda a corrigir bases de produção onde os usuários foram criados
sem o grupo Django correspondente, mas já possuem `PerfilUsuario` ou cartão RFID.

Uso:
    python scripts/sync_authorized_users.py
    python scripts/sync_authorized_users.py --dry-run
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from django.contrib.auth.models import Group, User  # noqa: E402

from app.models import CartaoRFID, PerfilUsuario  # noqa: E402


ROLE_TO_GROUP = {
    PerfilUsuario.ROLE_IC: "ic",
    PerfilUsuario.ROLE_ADMIN: "adm",
    PerfilUsuario.ROLE_SUPERVISOR: "professor",
}

GROUP_TO_ROLE = {
    "ic": PerfilUsuario.ROLE_IC,
    "adm": PerfilUsuario.ROLE_ADMIN,
    "mestrado": PerfilUsuario.ROLE_SUPERVISOR,
    "doutorado": PerfilUsuario.ROLE_SUPERVISOR,
    "professor": PerfilUsuario.ROLE_SUPERVISOR,
}


def sync_user(user: User, dry_run: bool = False) -> str:
    profile = getattr(user, "perfil", None)
    card = CartaoRFID.objects.filter(usuario=user).first()

    desired_role = None
    if profile:
        desired_role = profile.role
    elif card:
        desired_role = PerfilUsuario.ROLE_IC
    else:
        groups = set(user.groups.values_list("name", flat=True))
        for group_name in groups:
            if group_name in GROUP_TO_ROLE:
                desired_role = GROUP_TO_ROLE[group_name]
                break

    actions = []

    if desired_role and not profile:
        actions.append(f"criar perfil={desired_role}")
        if not dry_run:
            PerfilUsuario.objects.create(user=user, role=desired_role)
            profile = user.perfil

    if profile and profile.role != desired_role and desired_role:
        actions.append(f"ajustar perfil {profile.role}->{desired_role}")
        if not dry_run:
            profile.role = desired_role
            profile.save(update_fields=["role", "atualizado_em"])

    if desired_role:
        group_name = ROLE_TO_GROUP.get(desired_role)
        if group_name:
            group, _ = Group.objects.get_or_create(name=group_name)
            if not user.groups.filter(name=group_name).exists():
                actions.append(f"adicionar grupo={group_name}")
                if not dry_run:
                    user.groups.add(group)

    if card and not profile and not desired_role:
        actions.append("cartão sem perfil mapeado")

    return ", ".join(actions) if actions else "ok"


def main() -> int:
    parser = argparse.ArgumentParser(description="Sincroniza perfis e grupos autorizados dos usuários.")
    parser.add_argument("--dry-run", action="store_true", help="Mostra as ações sem alterar o banco.")
    args = parser.parse_args()

    total = 0
    changed = 0
    print("== Sincronização de usuários autorizados ==")
    for user in User.objects.all().order_by("username"):
        total += 1
        result = sync_user(user, dry_run=args.dry_run)
        if result != "ok":
            changed += 1
        print(f"- {user.username}: {result}")

    print(f"\nResumo: {total} usuários analisados, {changed} com ajustes necessários.")
    if args.dry_run:
        print("Dry-run concluído: nada foi salvo.")
    else:
        print("Sincronização concluída.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

