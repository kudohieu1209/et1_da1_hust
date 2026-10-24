"""Read-only legacy importer, outside the application runtime.

Existing MongoDB records win. Local files are never modified or deleted.
Legacy login sessions are deliberately not imported.
"""
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class MigrationConflictError(ValueError):
    pass


def _rows(path, table):
    if not path.exists():
        return []
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        return [dict(row) for row in connection.execute(f'SELECT * FROM "{table}"')]
    finally:
        connection.close()


def read_legacy(directory):
    directory = Path(directory)
    profiles = [{"key": path.stem, "profile": json.loads(path.read_text(encoding="utf-8"))}
                for path in sorted((directory / "students").glob("*.json"))]
    users = _rows(directory / "auth.sqlite3", "users")
    for user in users:
        for field in ("created_at", "locked_until", "last_login_at"):
            value = user.get(field)
            user[field] = datetime.fromisoformat(value).astimezone(timezone.utc) if value else None
        user["is_admin"] = bool(user.get("is_admin"))
        user["is_demo"] = bool(user.get("is_demo"))
    conversations = _rows(directory / "chat_history.sqlite3", "conversations")
    messages = _rows(directory / "chat_history.sqlite3", "messages")
    for message in messages:
        for source, target, default in (("suggested_actions_json", "suggested_actions", []),
                                         ("data_context_json", "data_context", None), ("sources_json", "sources", [])):
            value = message.pop(source, None)
            message[target] = json.loads(value) if value else default
    for conversation in conversations:
        items = sorted((message for message in messages if message["conversation_id"] == conversation["id"]),
                       key=lambda message: (message["created_at"], message["id"]))
        conversation.update(message_count=len(items), last_message_preview=items[-1]["content"] if items else "")
        conversation["is_archived"] = bool(conversation.get("is_archived"))
        conversation["is_pinned"] = bool(conversation.get("is_pinned"))
    return {"profiles": profiles, "users": users, "conversations": conversations, "messages": messages}


def plan_import(snapshot, database):
    """Compare without writes; reject cross-owner ID collisions before importing."""
    operations = {name: [] for name in snapshot}
    preserved = {name: 0 for name in snapshot}
    differences = {name: 0 for name in snapshot}
    for row in snapshot["profiles"]:
        profile, key = row["profile"], row["key"]
        student_id = str(profile.get("info", {}).get("student_id") or key)
        current = database["student_profiles"].find_one({"_id": key})
        if current and current.get("student_id") != student_id:
            raise MigrationConflictError("Trùng khóa hồ sơ nhưng khác chủ sở hữu; chưa ghi dữ liệu.")
        current = current or database["student_profiles"].find_one({"student_id": student_id})
        if current:
            preserved["profiles"] += 1
            differences["profiles"] += current.get("profile") != profile
        else:
            operations["profiles"].append({"_id": key, "student_id": student_id, "profile": profile,
                                            "updated_at": datetime.now(timezone.utc).isoformat()})
    for user in snapshot["users"]:
        current = database["users"].find_one({"_id": user["student_id"]})
        if current:
            preserved["users"] += 1
            differences["users"] += current["password_hash"] != user["password_hash"]
        else:
            operations["users"].append({"_id": user["student_id"], **{key: value for key, value in user.items() if key != "student_id"}})
    owners = {}
    for conversation in snapshot["conversations"]:
        key = conversation["id"]
        owners[key] = conversation["student_id"]
        current = database["conversations"].find_one({"_id": key})
        if current and current["student_id"] != conversation["student_id"]:
            raise MigrationConflictError("Trùng ID hội thoại nhưng khác chủ sở hữu; chưa ghi dữ liệu.")
        if current:
            preserved["conversations"] += 1
            differences["conversations"] += any(current.get(field) != value for field, value in conversation.items() if field != "id")
        else:
            operations["conversations"].append({"_id": key, **{field: value for field, value in conversation.items() if field != "id"}})
    for message in snapshot["messages"]:
        if message["conversation_id"] not in owners:
            raise MigrationConflictError("Có tin nhắn không thuộc hội thoại nguồn; chưa ghi dữ liệu.")
        key = hashlib.sha256(f"legacy-chat:{message['conversation_id']}:{message['id']}".encode()).hexdigest()
        current = database["messages"].find_one({"migration_key": key}) or database["messages"].find_one({
            "conversation_id": message["conversation_id"], "role": message["role"],
            "content": message["content"], "created_at": message["created_at"],
        })
        if current:
            preserved["messages"] += 1
        else:
            operations["messages"].append({**message, "migration_key": key})
    return {"operations": operations, "preserved": preserved, "differences": differences,
            "would_insert": {name: len(rows) for name, rows in operations.items()}}


def import_legacy(snapshot, database):
    from pymongo import ReturnDocument
    plan = plan_import(snapshot, database)
    database["messages"].create_index("migration_key", unique=True, sparse=True)
    database["messages"].create_index("id", unique=True)
    highest = max([0, *[int(row["id"]) for row in snapshot["messages"]],
                   *[int(row["id"]) for row in database["messages"].find({}, {"id": 1})]])
    database["counters"].update_one({"_id": "messages"}, {"$max": {"seq": highest}}, upsert=True)
    inserted = {name: 0 for name in snapshot}
    for name, collection in (("users", "users"), ("profiles", "student_profiles"), ("conversations", "conversations")):
        for row in plan["operations"][name]:
            result = database[collection].update_one({"_id": row["_id"]}, {"$setOnInsert": row}, upsert=True)
            inserted[name] += result.upserted_id is not None
    for row in plan["operations"]["messages"]:
        row = dict(row)
        if database["messages"].find_one({"id": row["id"]}):
            row["id"] = database["counters"].find_one_and_update(
                {"_id": "messages"}, {"$inc": {"seq": 1}}, return_document=ReturnDocument.AFTER)["seq"]
        result = database["messages"].update_one({"migration_key": row["migration_key"]}, {"$setOnInsert": row}, upsert=True)
        inserted["messages"] += result.upserted_id is not None
    for conversation in snapshot["conversations"]:
        key = conversation["id"]
        latest = database["messages"].find_one({"conversation_id": key}, sort=[("created_at", -1), ("id", -1)])
        database["conversations"].update_one({"_id": key, "student_id": conversation["student_id"]}, {"$set": {
            "message_count": database["messages"].count_documents({"conversation_id": key}),
            "last_message_preview": latest["content"] if latest else "",
        }})
    if any(plan_import(snapshot, database)["would_insert"].values()):
        raise RuntimeError("Đối chiếu sau migration chưa đầy đủ; nguồn cục bộ vẫn được giữ nguyên.")
    return {"inserted": inserted, "preserved": plan["preserved"], "differences_kept_on_mongo": plan["differences"], "verified": True}
