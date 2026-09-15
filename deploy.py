"""Cross-platform one-click deployment runner for royal300 Monthly Report.
Usage:
    python deploy.py
"""
from pathlib import Path
import paramiko

VPS_HOST = "93.127.206.52"
VPS_USER = "root"
VPS_PASS = "Royal300@2026"
REMOTE_ENV_PATH = "/var/www/royal300_monthly_report/.env"

def main():
    print(f"[*] Connecting to VPS {VPS_HOST} as {VPS_USER}...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(VPS_HOST, username=VPS_USER, password=VPS_PASS, timeout=15)
        print("[+] Connected successfully.")

        # Sync local .env to VPS
        local_env = Path(__file__).parent / ".env"
        if local_env.exists():
            print("[*] Uploading latest .env credentials to VPS...")
            sftp = client.open_sftp()
            sftp.put(str(local_env), REMOTE_ENV_PATH)
            sftp.close()
            print("[+] .env credentials synced successfully.")

        print("[*] Triggering git pull, dependency check, and service restart...")
        cmd = "bash /root/deploy_royal300_monthly_report.sh && systemctl is-active royal300_monthly_report_gunicorn.service"
        stdin, stdout, stderr = client.exec_command(cmd)

        out = stdout.read().decode("utf-8", "ignore")
        err = stderr.read().decode("utf-8", "ignore")

        if out:
            print("[STDOUT]\n" + out.strip())
        if err:
            print("[STDERR]\n" + err.strip())

        print("\n[+] Deployment successfully completed! App is live at: https://report.royal300.com")

    except Exception as e:
        print(f"[-] Deployment failed: {e}")
        sys.exit(1)
    finally:
        client.close()

if __name__ == "__main__":
    main()
