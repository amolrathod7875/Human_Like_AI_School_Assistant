from app.repositories.base import FirestoreRepository
from app.schemas.collections import AuditLog


class AuditLogRepository(FirestoreRepository[AuditLog]):
    def __init__(self, client=None) -> None:
        super().__init__(AuditLog, "audit_logs", client=client)

    def record(
        self,
        actor_id: str,
        action: str,
        target: str | None = None,
        metadata: dict | None = None,
    ) -> AuditLog:
        log = AuditLog(
            id="",  # assigned by Firestore on create
            actor_id=actor_id,
            action=action,
            target=target,
            metadata=metadata or {},
        )
        return self.create(log)
