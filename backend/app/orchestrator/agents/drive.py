"""Drive agent: semantic search, file context (with text export), and sharing."""
from __future__ import annotations

from app.google.clients import execute_async
from app.orchestrator.agents.base import BaseAgent, filters_from_step
from app.schemas import PlanStep
from app.search import hybrid_search

_EXPORTABLE = {
    "application/vnd.google-apps.document": "text/plain",
    "application/vnd.google-apps.spreadsheet": "text/csv",
    "application/vnd.google-apps.presentation": "text/plain",
}


class DriveAgent(BaseAgent):
    service = "drive"

    async def search(self, step: PlanStep, top_k: int = 5) -> list[dict]:
        async with self.ctx.new_session() as session:
            return await hybrid_search.search_drive(
                session, self.ctx.user_id, step.query, top_k=top_k,
                filters=filters_from_step(step),
            )

    async def get_context(self, item_id: str) -> dict:
        svc = await self.ctx.get_services()
        drive = svc.drive
        meta = await execute_async(
            drive.files().get(
                fileId=item_id,
                fields="id,name,mimeType,modifiedTime,webViewLink,owners(emailAddress)",
            )
        )
        mime = meta.get("mimeType", "")
        content = ""
        try:
            if mime in _EXPORTABLE:
                data = await execute_async(
                    drive.files().export_media(fileId=item_id, mimeType=_EXPORTABLE[mime])
                )
                content = data.decode("utf-8", errors="replace") if isinstance(data, bytes) else str(data)
            elif mime.startswith("text/"):
                data = await execute_async(drive.files().get_media(fileId=item_id))
                content = data.decode("utf-8", errors="replace") if isinstance(data, bytes) else str(data)
        except Exception:  # noqa: BLE001 - content export is best-effort
            content = ""
        return {
            "id": item_id,
            "name": meta.get("name"),
            "mime_type": mime,
            "web_view_link": meta.get("webViewLink"),
            "content": content[:6000],
        }

    # ---- writes -------------------------------------------------------------
    async def execute(self, action_type: str, payload: dict) -> dict:
        svc = await self.ctx.get_services()
        if action_type == "share_file":
            perm = await execute_async(
                svc.drive.permissions().create(
                    fileId=payload["file_id"],
                    body={
                        "type": "user",
                        "role": payload.get("role", "reader"),
                        "emailAddress": payload["email"],
                    },
                    sendNotificationEmail=payload.get("notify", True),
                )
            )
            return {"executed": True, "permission_id": perm.get("id"), "file_id": payload["file_id"]}
        raise ValueError(f"DriveAgent cannot execute {action_type}")
