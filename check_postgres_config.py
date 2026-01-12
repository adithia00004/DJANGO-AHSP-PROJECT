#!/usr/bin/env python
"""
Check PostgreSQL configuration for connection pool optimization.
Provides auto-detection and detailed fix instructions.
"""
import os
import sys
import django
import platform

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.db import connection

def find_postgresql_conf():
    """Try to locate postgresql.conf file."""
    with connection.cursor() as cursor:
        try:
            cursor.execute("SHOW config_file;")
            config_file = cursor.fetchone()[0]
            return config_file
        except Exception:
            return None

def check_postgres_config():
    """Check PostgreSQL configuration."""
    print("="*80)
    print("POSTGRESQL CONFIGURATION CHECK")
    print("="*80)
    print()

    issues_found = []
    recommendations = []

    with connection.cursor() as cursor:
        # Get PostgreSQL version
        cursor.execute("SELECT version();")
        pg_version = cursor.fetchone()[0]
        print(f"PostgreSQL Version: {pg_version.split(',')[0]}")
        print()

        # Check max_connections
        cursor.execute("SHOW max_connections;")
        max_conn = cursor.fetchone()[0]
        max_conn_int = int(max_conn)

        # Check current connections
        cursor.execute("""
            SELECT count(*)
            FROM pg_stat_activity
            WHERE datname = current_database();
        """)
        current_conn = cursor.fetchone()[0]

        # Check active connections
        cursor.execute("""
            SELECT count(*)
            FROM pg_stat_activity
            WHERE datname = current_database() AND state = 'active';
        """)
        active_conn = cursor.fetchone()[0]

        print(f"max_connections: {max_conn}")
        print(f"current_connections: {current_conn}/{max_conn} ({current_conn/max_conn_int*100:.1f}%)")
        print(f"active_connections: {active_conn}")
        print()

        # Check shared_buffers
        cursor.execute("SHOW shared_buffers;")
        shared_buf = cursor.fetchone()[0]
        print(f"shared_buffers: {shared_buf}")

        # Check work_mem
        cursor.execute("SHOW work_mem;")
        work_mem = cursor.fetchone()[0]
        print(f"work_mem: {work_mem}")

        # Check statement_timeout
        cursor.execute("SHOW statement_timeout;")
        stmt_timeout = cursor.fetchone()[0]
        print(f"statement_timeout: {stmt_timeout}")

        # Check idle_in_transaction_session_timeout
        cursor.execute("SHOW idle_in_transaction_session_timeout;")
        idle_timeout = cursor.fetchone()[0]
        print(f"idle_in_transaction_session_timeout: {idle_timeout}")

        # Check effective_cache_size
        cursor.execute("SHOW effective_cache_size;")
        cache_size = cursor.fetchone()[0]
        print(f"effective_cache_size: {cache_size}")

        print()
        print("-"*80)
        print("ANALYSIS:")
        print("-"*80)

        # Check max_connections
        if max_conn_int < 100:
            issues_found.append(f"[CRITICAL] max_connections = {max_conn} is VERY LOW!")
            recommendations.append(("max_connections", "200", "CRITICAL - Causing auth failures!"))
        elif max_conn_int < 200:
            issues_found.append(f"[HIGH] max_connections = {max_conn} is TOO LOW for 50+ users")
            recommendations.append(("max_connections", "200", "HIGH - Will cause issues at scale"))
        else:
            print(f"[OK] max_connections = {max_conn} is sufficient")

        # Check connection usage
        usage_percent = (current_conn / max_conn_int) * 100
        if usage_percent > 80:
            issues_found.append(f"[WARN] Connection usage at {usage_percent:.1f}% - near limit!")
        elif usage_percent > 50:
            print(f"[WARN] Connection usage at {usage_percent:.1f}% - monitor closely")
        else:
            print(f"[OK] Connection usage at {usage_percent:.1f}%")

        # Check statement_timeout
        if stmt_timeout == '0':
            print(f"[INFO] statement_timeout = 0 (unlimited)")
            print(f"       Django settings override this to 60s")
        elif 'ms' in stmt_timeout:
            timeout_ms = int(stmt_timeout.replace('ms', ''))
            if timeout_ms < 60000:
                print(f"[INFO] statement_timeout = {stmt_timeout}")
                print(f"       Django settings override this to 60000ms (60s)")

        print()
        print("-"*80)
        print("RECOMMENDATIONS:")
        print("-"*80)

        if not issues_found:
            print("[OK] No critical issues found!")
            print()
        else:
            print("Issues found:")
            for issue in issues_found:
                print(f"  {issue}")
            print()

        if recommendations:
            print("Recommended Changes:")
            for param, value, priority in recommendations:
                print(f"  [{priority}] {param} = {value}")
            print()

            # Try to find postgresql.conf
            config_file = find_postgresql_conf()

            print("="*80)
            print("HOW TO FIX:")
            print("="*80)
            print()

            if config_file:
                print(f"1. Edit PostgreSQL configuration file:")
                print(f"   {config_file}")
            else:
                print(f"1. Find and edit postgresql.conf:")
                if platform.system() == 'Windows':
                    print(f"   Common location: C:\\Program Files\\PostgreSQL\\15\\data\\postgresql.conf")
                else:
                    print(f"   Common locations:")
                    print(f"   - /etc/postgresql/15/main/postgresql.conf")
                    print(f"   - /var/lib/pgsql/data/postgresql.conf")

            print()
            print("2. Add or modify these lines:")
            print()
            for param, value, _ in recommendations:
                print(f"   {param} = {value}")

            if any(p[0] == 'max_connections' for p in recommendations):
                print()
                print("   # Also recommended when increasing max_connections:")
                print(f"   shared_buffers = 256MB      # 25% of RAM")
                print(f"   work_mem = 16MB              # For complex queries")
                print(f"   effective_cache_size = 1GB   # 50-75% of RAM")

            print()
            print("3. Restart PostgreSQL:")
            if platform.system() == 'Windows':
                print("   # As Administrator:")
                print("   net stop postgresql-x64-15")
                print("   net start postgresql-x64-15")
                print()
                print("   # Or use Services:")
                print("   services.msc -> postgresql-x64-15 -> Restart")
            else:
                print("   sudo systemctl restart postgresql")
                print("   # or")
                print("   sudo service postgresql restart")

            print()
            print("4. Verify changes:")
            print("   python check_postgres_config.py")

            print()
            print("="*80)

if __name__ == '__main__':
    try:
        check_postgres_config()
    except Exception as e:
        print(f"[ERROR] Failed to check PostgreSQL config: {e}")
        print()
        print("Troubleshooting:")
        print("1. Make sure PostgreSQL is running")
        print("2. Check Django database settings in config/settings/base.py")
        print("3. Verify database connection credentials")
        print()
        import traceback
        traceback.print_exc()
        sys.exit(1)
