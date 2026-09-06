"""One-off discovery script: prints the Pages and Ad Accounts this system
user token can see, with their numeric IDs, so you can wire them into
main.py runs. Usage: python src/list_assets.py
"""
from graph_api import GraphAPIClient
from config import META_BUSINESS_ID


def main():
    client = GraphAPIClient()

    print("=== Pages (via /me/accounts) ===")
    try:
        pages = client.list_assigned_pages()
        if not pages:
            print("  (none returned — check pages_show_list permission / page assignment)")
        for p in pages:
            print(f"  {p.get('name'):40s} id={p.get('id')}  fans={p.get('fan_count')}")
    except Exception as e:
        print(f"  ERROR: {e}")

    print("\n=== Owned Ad Accounts (via business) ===")
    try:
        data = client._get(f"{META_BUSINESS_ID}/owned_ad_accounts", {"fields": "id,name,account_id"})
        for a in data.get("data", []):
            print(f"  {a.get('name'):40s} id={a.get('id')}")
    except Exception as e:
        print(f"  ERROR: {e}")

    print("\n=== Client Ad Accounts (via business) ===")
    try:
        data = client._get(f"{META_BUSINESS_ID}/client_ad_accounts", {"fields": "id,name,account_id"})
        for a in data.get("data", []):
            print(f"  {a.get('name'):40s} id={a.get('id')}")
    except Exception as e:
        print(f"  ERROR: {e}")


if __name__ == "__main__":
    main()
