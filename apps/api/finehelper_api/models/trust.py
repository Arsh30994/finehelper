"""Trust scoring Mongo repositories."""

from __future__ import annotations

from finehelper_core.db.mongo import Mongo
from finehelper_core.models import TrustProfile, TrustScore, TrustSignalBatch


async def find_profile(db: Mongo, user_id: str) -> TrustProfile | None:
    return TrustProfile.from_mongo(await db.trust_profiles.find_one({"user_id": user_id}))


async def upsert_profile(db: Mongo, profile: TrustProfile) -> TrustProfile:
    profile.touch()
    await db.trust_profiles.replace_one({"user_id": profile.user_id}, profile.to_mongo(), upsert=True)
    return profile


async def insert_signals(db: Mongo, batch: TrustSignalBatch) -> TrustSignalBatch:
    await db.insert(db.trust_signal_batches, batch)
    return batch


async def latest_signals(db: Mongo, user_id: str) -> TrustSignalBatch | None:
    doc = await db.trust_signal_batches.find({"user_id": user_id}).sort("created_at", -1).limit(1).to_list(1)
    return TrustSignalBatch.from_mongo(doc[0]) if doc else None


async def insert_score(db: Mongo, score: TrustScore) -> TrustScore:
    await db.insert(db.trust_scores, score)
    return score


async def latest_score(db: Mongo, user_id: str) -> TrustScore | None:
    doc = await db.trust_scores.find({"user_id": user_id}).sort("created_at", -1).limit(1).to_list(1)
    return TrustScore.from_mongo(doc[0]) if doc else None
