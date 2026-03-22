import argparse
import random
import sys
import time
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class CheckResult:
    name: str
    passed: bool
    details: str


def _normalize_base_url(base_url: str) -> str:
    value = (base_url or "").strip().rstrip("/")
    if not value:
        raise ValueError("Base URL is required")
    if not value.startswith(("http://", "https://")):
        value = f"https://{value}"
    return value


def _safe_json(response: httpx.Response) -> Any:
    try:
        return response.json()
    except Exception:
        return None


def run_verification(base_url: str, email: str, password: str, timeout: float) -> tuple[list[CheckResult], dict[str, Any]]:
    results: list[CheckResult] = []
    context: dict[str, Any] = {
        "token": None,
        "created_store_id": None,
    }

    api_base = f"{base_url}/api/v1/admin"

    with httpx.Client(timeout=timeout, follow_redirects=False) as client:
        login_resp = client.post(
            f"{api_base}/login",
            json={"email": email, "password": password},
        )
        login_json = _safe_json(login_resp)
        token = (login_json or {}).get("access_token") if isinstance(login_json, dict) else None
        set_cookie_header = login_resp.headers.get("set-cookie", "")

        login_ok = login_resp.status_code == 200 and bool(token)
        results.append(
            CheckResult(
                name="Admin login",
                passed=login_ok,
                details=f"status={login_resp.status_code}, token={'yes' if token else 'no'}",
            )
        )

        cookie_ok = "access_token=" in set_cookie_header
        results.append(
            CheckResult(
                name="Login sets access_token cookie",
                passed=cookie_ok,
                details="set-cookie contains access_token" if cookie_ok else f"set-cookie missing access_token: {set_cookie_header[:200]}",
            )
        )

        if not token:
            return results, context

        context["token"] = token
        auth_headers = {"Authorization": f"Bearer {token}"}

        debug_resp = client.get(f"{api_base}/debug/db", headers=auth_headers)
        debug_json = _safe_json(debug_resp)
        debug_ok = debug_resp.status_code == 200 and isinstance(debug_json, dict)
        results.append(
            CheckResult(
                name="DB debug endpoint",
                passed=debug_ok,
                details=f"status={debug_resp.status_code}",
            )
        )

        if isinstance(debug_json, dict):
            tables = debug_json.get("tables", {})
            stores_meta = tables.get("stores", {}) if isinstance(tables, dict) else {}
            vendors_meta = tables.get("vendors", {}) if isinstance(tables, dict) else {}
            stores_exists = bool(stores_meta.get("exists"))
            vendors_exists = bool(vendors_meta.get("exists"))

            results.append(
                CheckResult(
                    name="Stores table exists",
                    passed=stores_exists,
                    details=f"metadata={stores_meta}",
                )
            )
            results.append(
                CheckResult(
                    name="Vendors table exists",
                    passed=vendors_exists,
                    details=f"metadata={vendors_meta}",
                )
            )

        stores_resp = client.get(f"{api_base}/stores", headers=auth_headers)
        stores_json = _safe_json(stores_resp)
        stores_list = stores_json.get("stores", []) if isinstance(stores_json, dict) else []
        stores_ok = stores_resp.status_code == 200 and isinstance(stores_list, list)
        results.append(
            CheckResult(
                name="List stores",
                passed=stores_ok,
                details=f"status={stores_resp.status_code}, count={len(stores_list) if isinstance(stores_list, list) else 'n/a'}",
            )
        )

        vendors_resp = client.get(f"{api_base}/vendors", headers=auth_headers)
        vendors_json = _safe_json(vendors_resp)
        vendors_list = vendors_json.get("vendors", []) if isinstance(vendors_json, dict) else []
        vendors_ok = vendors_resp.status_code == 200 and isinstance(vendors_list, list)
        results.append(
            CheckResult(
                name="List vendors",
                passed=vendors_ok,
                details=f"status={vendors_resp.status_code}, count={len(vendors_list) if isinstance(vendors_list, list) else 'n/a'}",
            )
        )

        unique_suffix = f"{int(time.time())}{random.randint(100, 999)}"
        phone = f"91{unique_suffix[-10:]}"
        create_payload = {
            "name": "Railway Verification Store",
            "owner_name": "Deployment Check",
            "contact_phone": phone,
            "address": "Railway Validation",
        }
        create_resp = client.post(f"{api_base}/stores", headers=auth_headers, json=create_payload)
        create_json = _safe_json(create_resp)

        created_store_id = None
        if isinstance(create_json, dict):
            created_store_id = ((create_json.get("store") or {}) if isinstance(create_json.get("store"), dict) else {}).get("id")

        create_ok = create_resp.status_code == 200 and (create_json or {}).get("status") == "created" and bool(created_store_id)
        results.append(
            CheckResult(
                name="Create store",
                passed=create_ok,
                details=f"status={create_resp.status_code}, store_id={created_store_id}",
            )
        )

        context["created_store_id"] = created_store_id

        if created_store_id:
            delete_resp = client.delete(f"{api_base}/stores/{created_store_id}", headers=auth_headers)
            delete_json = _safe_json(delete_resp)
            delete_ok = delete_resp.status_code == 200 and isinstance(delete_json, dict) and delete_json.get("status") == "deleted"
            results.append(
                CheckResult(
                    name="Delete verification store",
                    passed=delete_ok,
                    details=f"status={delete_resp.status_code}",
                )
            )
        else:
            results.append(
                CheckResult(
                    name="Delete verification store",
                    passed=False,
                    details="skipped (store was not created)",
                )
            )

    return results, context


def print_report(base_url: str, results: list[CheckResult]) -> None:
    print(f"\nRailway deployment verification: {base_url}")
    print("-" * 72)
    for item in results:
        status = "PASS" if item.passed else "FAIL"
        print(f"[{status}] {item.name}: {item.details}")

    passed_count = sum(1 for item in results if item.passed)
    total = len(results)
    print("-" * 72)
    print(f"Summary: {passed_count}/{total} checks passed")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify live Railway deployment for ZnShop admin API flows",
    )
    parser.add_argument("--base-url", required=True, help="Railway public base URL (e.g. https://your-app.up.railway.app)")
    parser.add_argument("--email", required=True, help="Admin login email")
    parser.add_argument("--password", required=True, help="Admin login password")
    parser.add_argument("--timeout", type=float, default=20.0, help="HTTP timeout in seconds")

    args = parser.parse_args()

    try:
        base_url = _normalize_base_url(args.base_url)
    except ValueError as exc:
        print(f"Input error: {exc}")
        return 2

    try:
        results, _ = run_verification(base_url, args.email, args.password, args.timeout)
    except Exception as exc:
        print(f"Verification failed to run: {exc}")
        return 2

    print_report(base_url, results)

    all_passed = all(item.passed for item in results)
    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
