"""
app/services/forensics.py
Forensic analysis services — detects data anomalies engineered by the Shadow Controller:
  - Cloned node identities (same serial_number on multiple node_uuids)
  - These are deliberately planted inconsistencies per the problem statement
"""
import logging
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.orm import Node
from pydantic import BaseModel

logger = logging.getLogger("aegis.forensics")


class ClonedIdentityEntry(BaseModel):
    serial_number: str
    node_uuids: list[int]
    infected_count: int
    clone_count: int


class ClonedIdentityReport(BaseModel):
    total_cloned_serials: int
    total_affected_nodes: int
    clones: list[ClonedIdentityEntry]


async def detect_cloned_identities(session: AsyncSession) -> ClonedIdentityReport:
    """
    Detects nodes sharing the same decoded serial number.
    This is a Shadow Controller tactic: clone a legitimate node's identity
    to mask malicious hardware behind a trusted SN.
    """
    stmt = (
        select(
            Node.serial_number,
            func.count(Node.node_uuid).label("clone_count"),
            func.sum(Node.is_infected.cast("int")).label("infected_count"),
            func.array_agg(Node.node_uuid).label("node_uuids"),
        )
        .group_by(Node.serial_number)
        .having(func.count(Node.node_uuid) > 1)
        .order_by(func.count(Node.node_uuid).desc())
    )

    rows = (await session.execute(stmt)).fetchall()

    clones = [
        ClonedIdentityEntry(
            serial_number=row.serial_number,
            node_uuids=sorted(row.node_uuids),
            infected_count=int(row.infected_count or 0),
            clone_count=row.clone_count,
        )
        for row in rows
    ]

    total_affected = sum(c.clone_count for c in clones)
    logger.warning("Cloned identity report: %d serials cloned across %d nodes", len(clones), total_affected)

    return ClonedIdentityReport(
        total_cloned_serials=len(clones),
        total_affected_nodes=total_affected,
        clones=clones,
    )
