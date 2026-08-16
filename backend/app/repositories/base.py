from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Generic, List, Optional, Sequence, Tuple, Type, TypeVar

from pydantic import BaseModel

from app.providers.firestore_provider import get_firestore_client

T = TypeVar("T", bound=BaseModel)


@dataclass
class Page(Generic[T]):
    """A page of results plus an opaque token for the next page (if any)."""

    items: List[T]
    next_page_token: Optional[str] = None


class RepositoryError(Exception):
    """Mapped Firestore/DB error with a stable code and suggested HTTP status."""

    def __init__(self, code: str, message: str, status_code: int = 500) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def map_firestore_error(exc: Exception) -> RepositoryError:
    """Map a raw Firestore/Google exception to a RepositoryError.

    Mapping is done by HTTP status code (available on google.cloud exceptions
    via `.code`) so it is robust to exception-class renames across SDK versions.
    """
    try:
        from google.cloud import exceptions as gexc
    except ImportError:  # pragma: no cover - google.cloud present with firestore
        return RepositoryError("REPOSITORY_ERROR", str(exc), status_code=500)

    if isinstance(exc, gexc.GoogleCloudError):
        code = getattr(exc, "code", None)
        mapping = {
            404: ("NOT_FOUND", 404),
            409: ("ALREADY_EXISTS", 409),
            403: ("PERMISSION_DENIED", 403),
            400: ("INVALID_ARGUMENT", 400),
        }
        if code in mapping:
            name, status = mapping[code]
            return RepositoryError(name, str(exc), status_code=status)

    return RepositoryError("REPOSITORY_ERROR", str(exc), status_code=500)


class FirestoreRepository(Generic[T]):
    """Generic, typed Firestore repository.

    Responsibilities (this layer only):
    - document <-> Pydantic model mapping
    - created_at / updated_at server timestamps
    - cursor pagination
    - error mapping

    It deliberately contains NO business rules (e.g. "is this parent allowed to
    see this child"). Authorization belongs to services.
    """

    def __init__(self, model: Type[T], collection: str, client: Any = None) -> None:
        self.model = model
        self.collection_name = collection
        self._client = client

    @property
    def client(self) -> Any:
        if self._client is None:
            self._client = get_firestore_client()
        return self._client

    @property
    def _coll(self):
        return self.client.collection(self.collection_name)

    def _to_model(self, doc) -> Optional[T]:
        if doc is None or not doc.exists:
            return None
        data = dict(doc.to_dict() or {})
        data["id"] = doc.id
        return self.model(**data)

    def _model_dump(self, model: T) -> Dict[str, Any]:
        return model.model_dump(mode="json", exclude={"id"})

    def _prepare_changes(self, changes: Dict[str, Any]) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for key, value in changes.items():
            if isinstance(value, BaseModel):
                out[key] = value.model_dump(mode="json")
            elif isinstance(value, Enum):
                out[key] = value.value
            else:
                out[key] = value
        return out

    def get(self, doc_id: str) -> Optional[T]:
        try:
            doc = self._coll.document(doc_id).get()
        except Exception as exc:
            raise map_firestore_error(exc) from exc
        return self._to_model(doc)

    def create(self, model: T, doc_id: Optional[str] = None) -> T:
        from firebase_admin import firestore as fs

        ref = self._coll.document(doc_id) if doc_id else self._coll.document()
        data = self._model_dump(model)
        data["created_at"] = fs.SERVER_TIMESTAMP
        data["updated_at"] = fs.SERVER_TIMESTAMP
        try:
            ref.set(data)
        except Exception as exc:
            raise map_firestore_error(exc) from exc
        return self.model(**{**model.model_dump(exclude={"id"}), "id": ref.id})

    def update(self, doc_id: str, changes: Dict[str, Any]) -> None:
        from firebase_admin import firestore as fs

        data = self._prepare_changes(changes)
        data["updated_at"] = fs.SERVER_TIMESTAMP
        try:
            self._coll.document(doc_id).update(data)
        except Exception as exc:
            raise map_firestore_error(exc) from exc

    def delete(self, doc_id: str) -> None:
        try:
            self._coll.document(doc_id).delete()
        except Exception as exc:
            raise map_firestore_error(exc) from exc

    def list(
        self,
        *,
        filters: Optional[Sequence[Tuple[str, str, Any]]] = None,
        order_by: Optional[str] = None,
        page_size: int = 20,
        start_after: Optional[str] = None,
    ) -> Page[T]:
        try:
            query = self._coll
            for field, op, value in filters or []:
                query = query.where(field, op, value)
            if order_by:
                query = query.order_by(order_by)
            if start_after:
                query = query.start_after(start_after)
            query = query.limit(page_size + 1)
            docs = list(query.get())
        except Exception as exc:
            raise map_firestore_error(exc) from exc

        items = [self._to_model(d) for d in docs[:page_size]]
        # The token is the id of the last returned document; Firestore's
        # start_after() then resumes *after* it, so no document is skipped or
        # duplicated across pages.
        next_token = docs[page_size - 1].id if len(docs) > page_size else None
        return Page(items=items, next_page_token=next_token)
