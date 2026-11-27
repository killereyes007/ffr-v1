"""Base de données du jeu (PostgreSQL en production, SQLite en secours local).

Variable d'environnement :
  DATABASE_URL  ex. postgresql://user:motdepasse@localhost:5432/xo_game
                (mysql+pymysql://… fonctionne aussi). Absente : fichier SQLite
                local `xo_game.db` dans le dossier des données.

Le schéma est créé au démarrage et le contenu (game_content.py) est inséré de
façon idempotente : relancer ne duplique rien.
"""

import logging
import os
import random
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    func,
    insert,
    select,
    text,
)

from game_content import CONTENT, DOMAINS, iter_items

logger = logging.getLogger("xo.db")

KIND_TO_LEVEL = {"mot": "facile", "phrase": "moyen", "paragraphe": "difficile"}

metadata = MetaData()

domains_t = Table(
    "domains", metadata,
    Column("id", String(40), primary_key=True),
    Column("label", String(120), nullable=False),
    Column("mode", String(12), nullable=False),  # histoire | phrases
    Column("position", Integer, nullable=False, default=0),
    Column("story_kicker", String(160)),
    Column("story_title", String(160)),
    Column("story_body", Text),
    Column("active", Boolean, nullable=False, default=True),
)

items_t = Table(
    "items", metadata,
    Column("id", String(36), primary_key=True),
    Column("domain_id", String(40), ForeignKey("domains.id"), nullable=False),
    Column("kind", String(12), nullable=False),  # mot | phrase | paragraphe
    Column("difficulty", String(12), nullable=False),  # facile | moyen | difficile
    Column("french_text", Text, nullable=False),
    Column("position", Integer, nullable=False, default=0),
    Column("active", Boolean, nullable=False, default=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Index("ix_items_domain_kind", "domain_id", "kind"),
)

contributions_t = Table(
    "contributions", metadata,
    Column("id", String(36), primary_key=True),  # = sample_id du dossier disque
    Column("item_id", String(36), ForeignKey("items.id")),
    Column("domain_id", String(40)),
    Column("speaker_id", String(80)),
    Column("speaker_label", String(120)),
    Column("french_text", Text),
    Column("fon_text", Text),
    Column("contribution_mode", String(20)),
    Column("review_status", String(20), nullable=False, default="unreviewed"),
    Column("has_human_audio", Boolean, nullable=False, default=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Index("ix_contrib_speaker", "speaker_id"),
    Index("ix_contrib_item", "item_id"),
)

_engine = None


def _database_url(default_dir: Path) -> str:
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        default_dir.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{(default_dir / 'xo_game.db').as_posix()}"
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


def init_db(default_dir: Path) -> None:
    """Crée le schéma et insère le contenu manquant."""
    global _engine
    url = _database_url(default_dir)
    _engine = create_engine(url, pool_pre_ping=True, future=True)
    metadata.create_all(_engine)
    inserted = seed_content()
    logger.info("Base de données prête (%s), %s éléments ajoutés", _engine.dialect.name, inserted)


def engine():
    if _engine is None:
        raise RuntimeError("Base de données non initialisée")
    return _engine


def item_id_for(domain_id: str, text_value: str) -> str:
    """Identifiant stable : le même texte reçoit toujours le même id."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"xo:{domain_id}:{text_value}"))


def seed_content() -> int:
    now = datetime.now(timezone.utc)
    added = 0
    with engine().begin() as conn:
        known_domains = {row[0] for row in conn.execute(select(domains_t.c.id))}
        for d in DOMAINS:
            if d["id"] in known_domains:
                continue
            conn.execute(insert(domains_t).values(
                id=d["id"], label=d["label"], mode=d["mode"], position=d["position"],
                story_kicker=d.get("story_kicker"), story_title=d.get("story_title"),
                story_body=d.get("story_body"), active=True,
            ))
        known_items = {row[0] for row in conn.execute(select(items_t.c.id))}
        batch = []
        for domain_id, kind, text_value, position in iter_items():
            iid = item_id_for(domain_id, text_value)
            if iid in known_items:
                continue
            known_items.add(iid)
            batch.append(dict(
                id=iid, domain_id=domain_id, kind=kind, difficulty=KIND_TO_LEVEL[kind],
                french_text=text_value, position=position, active=True, created_at=now,
            ))
        if batch:
            conn.execute(insert(items_t), batch)
            added = len(batch)
    return added


def list_domains() -> list[dict]:
    with engine().connect() as conn:
        counts = {}
        for domain_id, kind, n in conn.execute(
            select(items_t.c.domain_id, items_t.c.kind, func.count())
            .where(items_t.c.active.is_(True))
            .group_by(items_t.c.domain_id, items_t.c.kind)
        ):
            counts.setdefault(domain_id, {})[kind] = n
        rows = conn.execute(
            select(domains_t).where(domains_t.c.active.is_(True)).order_by(domains_t.c.position)
        ).mappings().all()
    return [
        {
            "id": r["id"], "label": r["label"], "mode": r["mode"],
            "story": (
                {"kicker": r["story_kicker"], "title": r["story_title"], "body": r["story_body"]}
                if r["story_body"] else None
            ),
            "counts": counts.get(r["id"], {}),
            "total": sum(counts.get(r["id"], {}).values()),
        }
        for r in rows
    ]


# Composition d'une manche selon le niveau du joueur (1 = découverte).
# (mot, phrase, paragraphe) pour 5 cartes ; le serveur complète si un type manque.
ROUND_RECIPES = {
    1: (5, 0, 0),
    2: (3, 2, 0),
    3: (2, 3, 0),
    4: (1, 3, 1),
    5: (0, 4, 1),
}


def draw_round(domain_id: str | None, level: int, size: int, exclude: list[str]) -> list[dict]:
    """Tire au hasard les cartes d'une manche, sans répéter celles déjà vues.

    domain_id None = mélange de tous les domaines.
    """
    level = max(1, min(5, level))
    size = max(1, min(10, size))
    base = ROUND_RECIPES[level]
    wanted = {"mot": 0, "phrase": 0, "paragraphe": 0}
    # adapte la recette à la taille demandée (5 par défaut)
    for kind, share in zip(("mot", "phrase", "paragraphe"), base):
        wanted[kind] = round(share * size / 5)
    while sum(wanted.values()) < size:
        wanted["phrase" if level > 1 else "mot"] += 1
    while sum(wanted.values()) > size:
        biggest = max(wanted, key=wanted.get)
        wanted[biggest] -= 1

    excluded = set(exclude)
    picked: list[dict] = []
    with engine().connect() as conn:
        def pool(kind: str, skip_seen: bool = True):
            q = select(
                items_t.c.id, items_t.c.domain_id, items_t.c.kind,
                items_t.c.difficulty, items_t.c.french_text,
            ).where(items_t.c.active.is_(True), items_t.c.kind == kind)
            if domain_id:
                q = q.where(items_t.c.domain_id == domain_id)
            rows = [dict(r) for r in conn.execute(q).mappings()]
            if skip_seen:
                rows = [r for r in rows if r["id"] not in excluded]
            return rows

        taken: set[str] = set()
        for kind, n in wanted.items():
            if n <= 0:
                continue
            candidates = [r for r in pool(kind) if r["id"] not in taken]
            if len(candidates) < n:  # tout vu : on repioche dans l'ensemble
                candidates = [r for r in pool(kind, skip_seen=False) if r["id"] not in taken]
            chosen = random.sample(candidates, min(n, len(candidates)))
            taken.update(r["id"] for r in chosen)
            picked.extend(chosen)
        # complète si un type manquait
        if len(picked) < size:
            for kind in ("phrase", "mot", "paragraphe"):
                extra = [r for r in pool(kind, skip_seen=False) if r["id"] not in taken]
                random.shuffle(extra)
                for r in extra[: size - len(picked)]:
                    taken.add(r["id"])
                    picked.append(r)
                if len(picked) >= size:
                    break
        labels = {
            row[0]: row[1]
            for row in conn.execute(select(domains_t.c.id, domains_t.c.label))
        }
    random.shuffle(picked)
    # les paragraphes en dernier : montée en difficulté dans la manche
    picked.sort(key=lambda r: {"mot": 0, "phrase": 1, "paragraphe": 2}[r["kind"]])
    return [
        {
            "id": r["id"], "domain_id": r["domain_id"], "domain_label": labels.get(r["domain_id"], ""),
            "kind": r["kind"], "difficulty": r["difficulty"], "text": r["french_text"],
        }
        for r in picked
    ]


def record_contribution(
    sample_id: str,
    domain_id,
    french_text,
    fon_text,
    contribution_mode,
    speaker_id,
    speaker_label,
    review_status,
    has_human_audio,
) -> None:
    """Copie des métadonnées dans la base ; ne doit jamais bloquer l'envoi."""
    try:
        item_id = None
        if domain_id and french_text:
            candidate = item_id_for(domain_id, french_text.strip())
            with engine().connect() as conn:
                found = conn.execute(select(items_t.c.id).where(items_t.c.id == candidate)).first()
            item_id = candidate if found else None
        with engine().begin() as conn:
            conn.execute(insert(contributions_t).values(
                id=sample_id, item_id=item_id, domain_id=domain_id, speaker_id=speaker_id,
                speaker_label=speaker_label, french_text=french_text, fon_text=fon_text or None,
                contribution_mode=contribution_mode, review_status=review_status,
                has_human_audio=bool(has_human_audio), created_at=datetime.now(timezone.utc),
            ))
    except Exception:  # noqa: BLE001 - la copie en base est secondaire
        logger.exception("Copie de la contribution en base impossible")


def stats() -> dict:
    with engine().connect() as conn:
        n_items = conn.execute(select(func.count()).select_from(items_t)).scalar_one()
        n_contrib = conn.execute(select(func.count()).select_from(contributions_t)).scalar_one()
        per_domain = {
            d: n for d, n in conn.execute(
                select(items_t.c.domain_id, func.count()).group_by(items_t.c.domain_id)
            )
        }
        conn.execute(text("SELECT 1"))
    return {"items": n_items, "contributions": n_contrib, "items_per_domain": per_domain}
