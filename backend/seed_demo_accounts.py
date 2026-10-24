"""Tạo tài khoản đăng nhập cho các hồ sơ demo đang có trong kho hồ sơ.

    python seed_demo_accounts.py                    # tạo tài khoản còn thiếu
    python seed_demo_accounts.py --reset-password   # cấp mật khẩu mới cho mọi tài khoản demo
    python seed_demo_accounts.py --admin 20220001   # cấp quyền quản trị cho một MSSV
    python seed_demo_accounts.py --reset-password --password Demo@2026
                                                    # đặt chung mật khẩu cố định (ghi trong README) để demo

Mặc định mật khẩu sinh ngẫu nhiên và CHỈ in ra màn hình (không ghi file, không commit).
Ghi kết quả vào nơi an toàn; quên thì chạy lại với --reset-password.
Dùng cùng kho MongoDB với backend.
"""
import argparse
import secrets
import sys
from datetime import datetime, timezone

from app.auth.passwords import PasswordPolicyError, hash_password, validate_password
from app.auth.runtime import auth_service
from app.auth.store import UserExistsError
from app.core.config import MONGODB_URI
from app.services.mongo_client import redact_uri


def _demo_password() -> str:
    # 12 ký tự URL-safe (~72 bit), đủ mạnh mà vẫn gõ tay được khi demo.
    return secrets.token_urlsafe(9)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--reset-password", action="store_true", help="Cấp mật khẩu mới cho tài khoản demo đã có")
    parser.add_argument("--admin", metavar="MSSV", help="Cấp quyền quản trị cho MSSV này")
    parser.add_argument("--password", help="Dùng mật khẩu này cho mọi tài khoản demo thay vì sinh ngẫu nhiên")
    args = parser.parse_args()
    if args.password:
        try:
            validate_password(args.password)
        except PasswordPolicyError as exc:
            print(f"--password không hợp lệ: {exc}", file=sys.stderr)
            return 1
    new_password = (lambda: args.password) if args.password else _demo_password

    store = auth_service.store
    print(f"Kho tài khoản: {'MongoDB ' + redact_uri(MONGODB_URI)}\n")
    rows = []
    for key, profile in auth_service.profiles.list():
        info = profile.get("info", {})
        student_id = str(info.get("student_id") or key)
        name = info.get("student_name", "")
        existing = store.get_user(student_id)
        if existing is None:
            password = new_password()
            try:
                store.create_user({
                    "student_id": student_id,
                    "password_hash": hash_password(password),
                    "is_demo": True,
                    "created_at": datetime.now(timezone.utc),
                })
            except UserExistsError:
                continue
            rows.append((student_id, name, password, "tạo mới"))
        elif args.reset_password and existing["is_demo"]:
            password = new_password()
            store.set_password(student_id, hash_password(password))
            store.delete_sessions_for(student_id)
            rows.append((student_id, name, password, "đổi mật khẩu"))
        else:
            rows.append((student_id, name, "(giữ nguyên)", "đã có"))

    if args.admin:
        if store.get_user(args.admin) is None:
            print(f"Không có tài khoản {args.admin} để cấp quyền quản trị.", file=sys.stderr)
            return 1
        store.set_admin(args.admin, True)
        print(f"Đã cấp quyền quản trị cho {args.admin}.\n")

    width = max((len(name) for _, name, _, _ in rows), default=10)
    print(f"{'MSSV':<10} {'Họ tên':<{width}}  {'Mật khẩu':<14} Trạng thái")
    for student_id, name, password, status in rows:
        print(f"{student_id:<10} {name:<{width}}  {password:<14} {status}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
