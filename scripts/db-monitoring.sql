-- =============================================================================
-- Kaasb Platform — Database Health Monitoring Queries
-- =============================================================================
-- Run these queries against the production database to monitor health.
-- Recommended schedule (see comments per section):
--   Hourly    : connection counts, long-running queries, locks
--   Daily     : cache hit ratio, index usage, dead tuples
--   Weekly    : table sizes, unused indexes, bloat estimate
--
-- Usage:
--   psql -U kaasb_user -d kaasb_db -f scripts/db-monitoring.sql
--   or run individual sections in your monitoring tool (Grafana, Metabase, etc.)
-- =============================================================================


-- =============================================================================
-- SECTION 1: CONNECTION POOL HEALTH  [Run: Hourly or on alert]
-- =============================================================================

-- 1a. Connection counts by state and application
-- Watch for: "idle in transaction" > 5 (likely connection leaks)
--            total connections approaching max_connections
SELECT
    state,
    application_name,
    COUNT(*)  AS connection_count,
    MAX(EXTRACT(EPOCH FROM (now() - state_change)))::INT AS max_age_seconds
FROM pg_stat_activity
WHERE datname = current_database()
GROUP BY state, application_name
ORDER BY connection_count DESC;

-- 1b. Connection count vs limit — alert if > 85%
SELECT
    current_setting('max_connections')::INT           AS max_connections,
    COUNT(*)                                           AS active_connections,
    ROUND(100.0 * COUNT(*) / current_setting('max_connections')::INT, 1)
                                                       AS pct_used,
    CASE
        WHEN 100.0 * COUNT(*) / current_setting('max_connections')::INT > 85
        THEN '⚠ ALERT: approaching max_connections'
        ELSE 'OK'
    END AS status
FROM pg_stat_activity
WHERE datname = current_database();

-- 1c. Sessions with open transactions older than 60 seconds
-- These should normally be 0 (idle_in_transaction_session_timeout kills them at 60s)
SELECT
    pid,
    application_name,
    usename,
    state,
    query_start,
    EXTRACT(EPOCH FROM (now() - query_start))::INT AS seconds_in_transaction,
    LEFT(query, 120) AS query_preview
FROM pg_stat_activity
WHERE datname = current_database()
  AND state IN ('idle in transaction', 'idle in transaction (aborted)')
  AND query_start < now() - INTERVAL '30 seconds'
ORDER BY seconds_in_transaction DESC;


-- =============================================================================
-- SECTION 2: SLOW / LONG-RUNNING QUERIES  [Run: Every 5 minutes on alert]
-- =============================================================================

-- 2a. Currently running queries > 5 seconds
-- These may be holding locks and blocking other queries
SELECT
    pid,
    usename,
    application_name,
    state,
    EXTRACT(EPOCH FROM (now() - query_start))::INT AS running_seconds,
    wait_event_type,
    wait_event,
    LEFT(query, 200) AS query_preview
FROM pg_stat_activity
WHERE datname = current_database()
  AND state = 'active'
  AND query_start < now() - INTERVAL '5 seconds'
  AND query NOT LIKE '%pg_stat_activity%'  -- exclude monitoring queries
ORDER BY running_seconds DESC;

-- 2b. Top 15 slowest queries (requires pg_stat_statements extension)
-- Reset stats with: SELECT pg_stat_statements_reset();
SELECT
    ROUND(total_exec_time::NUMERIC, 2)            AS total_ms,
    calls,
    ROUND((total_exec_time / calls)::NUMERIC, 2)  AS avg_ms,
    ROUND(stddev_exec_time::NUMERIC, 2)           AS stddev_ms,
    rows,
    ROUND((rows::NUMERIC / calls), 1)             AS avg_rows,
    LEFT(query, 150)                              AS query_preview
FROM pg_stat_statements
WHERE calls > 10
ORDER BY avg_ms DESC
LIMIT 15;

-- 2c. Most frequently called queries (high volume = high cumulative load)
SELECT
    calls,
    ROUND(total_exec_time::NUMERIC, 2)            AS total_ms,
    ROUND((total_exec_time / calls)::NUMERIC, 2)  AS avg_ms,
    LEFT(query, 150)                              AS query_preview
FROM pg_stat_statements
WHERE calls > 100
ORDER BY calls DESC
LIMIT 15;


-- =============================================================================
-- SECTION 3: LOCK MONITORING  [Run: On alert / when queries seem stuck]
-- =============================================================================

-- 3a. Active locks and their waiters
SELECT
    blocked.pid                             AS blocked_pid,
    blocked.usename                         AS blocked_user,
    blocked.application_name               AS blocked_app,
    LEFT(blocked.query, 120)               AS blocked_query,
    blocker.pid                             AS blocking_pid,
    blocker.usename                         AS blocking_user,
    LEFT(blocker.query, 120)               AS blocking_query,
    EXTRACT(EPOCH FROM (now() - blocked.query_start))::INT AS blocked_for_seconds
FROM pg_stat_activity AS blocked
JOIN pg_stat_activity AS blocker
  ON blocker.pid = ANY(pg_blocking_pids(blocked.pid))
WHERE blocked.datname = current_database()
ORDER BY blocked_for_seconds DESC;

-- 3b. Lock wait summary
SELECT
    wait_event_type,
    wait_event,
    COUNT(*) AS waiter_count
FROM pg_stat_activity
WHERE datname = current_database()
  AND wait_event IS NOT NULL
GROUP BY wait_event_type, wait_event
ORDER BY waiter_count DESC;


-- =============================================================================
-- SECTION 4: CACHE HIT RATIO  [Run: Daily — alert if < 95%]
-- =============================================================================

-- 4a. Database-level cache hit ratio
-- Target: > 99% (our shared_buffers=2GB should achieve this)
-- Below 95%: data is too large for shared_buffers or indexes are missing
SELECT
    datname,
    blks_read,
    blks_hit,
    ROUND(100.0 * blks_hit / NULLIF(blks_hit + blks_read, 0), 2) AS cache_hit_pct,
    CASE
        WHEN 100.0 * blks_hit / NULLIF(blks_hit + blks_read, 0) < 95
        THEN '⚠ ALERT: low cache hit — increase shared_buffers or add indexes'
        ELSE 'OK'
    END AS status
FROM pg_stat_database
WHERE datname = current_database();

-- 4b. Per-table cache hit ratio (identify hot tables not fitting in cache)
SELECT
    schemaname,
    relname                           AS table_name,
    heap_blks_read,
    heap_blks_hit,
    ROUND(100.0 * heap_blks_hit / NULLIF(heap_blks_hit + heap_blks_read, 0), 1)
                                      AS table_cache_hit_pct,
    idx_blks_read,
    idx_blks_hit,
    ROUND(100.0 * idx_blks_hit / NULLIF(idx_blks_hit + idx_blks_read, 0), 1)
                                      AS index_cache_hit_pct
FROM pg_statio_user_tables
ORDER BY heap_blks_read + idx_blks_read DESC
LIMIT 20;


-- =============================================================================
-- SECTION 5: TABLE SIZES & BLOAT  [Run: Weekly]
-- =============================================================================

-- 5a. Table sizes including indexes
SELECT
    schemaname,
    relname                           AS table_name,
    pg_size_pretty(pg_table_size(c.oid))            AS table_size,
    pg_size_pretty(pg_indexes_size(c.oid))          AS indexes_size,
    pg_size_pretty(pg_total_relation_size(c.oid))   AS total_size,
    pg_total_relation_size(c.oid)                   AS total_bytes
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE c.relkind = 'r'
  AND n.nspname = 'public'
ORDER BY pg_total_relation_size(c.oid) DESC;

-- 5b. Row counts (approximate — uses pg_class stats, updated by ANALYZE)
SELECT
    schemaname,
    relname                           AS table_name,
    reltuples::BIGINT                 AS estimated_row_count
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE c.relkind = 'r'
  AND n.nspname = 'public'
ORDER BY reltuples DESC;

-- 5c. Table bloat estimate (dead tuples vs live tuples)
-- Alert if dead_pct > 20% — table needs VACUUM
SELECT
    schemaname,
    relname                           AS table_name,
    n_live_tup,
    n_dead_tup,
    ROUND(100.0 * n_dead_tup / NULLIF(n_live_tup + n_dead_tup, 0), 1) AS dead_pct,
    last_vacuum,
    last_autovacuum,
    last_analyze,
    last_autoanalyze,
    CASE
        WHEN 100.0 * n_dead_tup / NULLIF(n_live_tup + n_dead_tup, 0) > 20
        THEN '⚠ VACUUM needed'
        WHEN last_autovacuum < now() - INTERVAL '7 days'
        THEN '⚠ Autovacuum may be falling behind'
        ELSE 'OK'
    END AS status
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC;


-- =============================================================================
-- SECTION 6: INDEX HEALTH  [Run: Weekly]
-- =============================================================================

-- 6a. Index usage — find unused indexes (candidates for removal)
-- Unused indexes waste disk space and slow down writes (index must be updated on INSERT/UPDATE).
-- Note: Stats reset after server restart. Wait at least 2 weeks of normal traffic before removing.
SELECT
    schemaname,
    relname                          AS table_name,
    indexrelname                     AS index_name,
    pg_size_pretty(pg_relation_size(i.indexrelid)) AS index_size,
    idx_scan                         AS scans_since_reset,
    idx_tup_read,
    idx_tup_fetch,
    CASE
        WHEN idx_scan = 0 THEN '⚠ UNUSED — consider dropping'
        WHEN idx_scan < 10 THEN '⚠ RARELY USED'
        ELSE 'OK'
    END AS status
FROM pg_stat_user_indexes i
JOIN pg_index x ON i.indexrelid = x.indexrelid
WHERE NOT x.indisunique              -- exclude unique/PK constraints (can't remove)
  AND NOT x.indisprimary
ORDER BY idx_scan ASC, pg_relation_size(i.indexrelid) DESC;

-- 6b. Index scan efficiency per table
SELECT
    relname                          AS table_name,
    seq_scan,
    seq_tup_read,
    idx_scan,
    idx_tup_fetch,
    ROUND(100.0 * idx_scan / NULLIF(seq_scan + idx_scan, 0), 1) AS idx_scan_pct,
    CASE
        WHEN seq_scan > idx_scan * 10
         AND n_live_tup > 1000
        THEN '⚠ Many sequential scans on large table — add index?'
        ELSE 'OK'
    END AS status
FROM pg_stat_user_tables
ORDER BY seq_scan DESC
LIMIT 20;

-- 6c. Duplicate / redundant indexes
-- If two indexes share the same leading column(s), one may be redundant.
SELECT
    a.schemaname,
    a.relname     AS table_name,
    a.indexrelname AS index_a,
    b.indexrelname AS index_b,
    a.idx_scan    AS scans_a,
    b.idx_scan    AS scans_b
FROM pg_stat_user_indexes a
JOIN pg_stat_user_indexes b
  ON a.relid = b.relid
 AND a.indexrelid < b.indexrelid
JOIN pg_index ia ON ia.indexrelid = a.indexrelid
JOIN pg_index ib ON ib.indexrelid = b.indexrelid
WHERE ia.indkey[0] = ib.indkey[0]   -- same leading column
ORDER BY a.relname, a.indexrelname;


-- =============================================================================
-- SECTION 7: VACUUM & ANALYZE STATUS  [Run: Daily]
-- =============================================================================

-- 7a. Tables approaching autovacuum threshold (needs VACUUM soon)
SELECT
    schemaname,
    relname                         AS table_name,
    n_live_tup,
    n_dead_tup,
    -- Calculate when autovacuum will trigger (mirrors autovacuum_vacuum_threshold logic)
    (current_setting('autovacuum_vacuum_threshold')::INT
     + current_setting('autovacuum_vacuum_scale_factor')::FLOAT * n_live_tup)::BIGINT
                                    AS vacuum_threshold,
    n_dead_tup > (
        current_setting('autovacuum_vacuum_threshold')::INT
        + current_setting('autovacuum_vacuum_scale_factor')::FLOAT * n_live_tup
    ) AS vacuum_needed,
    last_autovacuum,
    last_autoanalyze
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC;

-- 7b. Transaction ID wraparound risk
-- PostgreSQL uses 32-bit transaction IDs. Wraparound causes data corruption!
-- ALERT: If age_pct > 50%, trigger manual VACUUM FREEZE on the table.
SELECT
    schemaname,
    relname                         AS table_name,
    greatest(age(relfrozenxid), 0)  AS xid_age,
    2147483647                       AS wraparound_limit,
    ROUND(100.0 * greatest(age(relfrozenxid), 0) / 2147483647, 2) AS age_pct,
    CASE
        WHEN greatest(age(relfrozenxid), 0) > 1500000000
        THEN '🚨 CRITICAL: VACUUM FREEZE immediately'
        WHEN greatest(age(relfrozenxid), 0) > 750000000
        THEN '⚠ WARNING: schedule VACUUM FREEZE'
        ELSE 'OK'
    END AS status
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE c.relkind = 'r'
  AND n.nspname = 'public'
ORDER BY age(relfrozenxid) DESC;


-- =============================================================================
-- SECTION 8: REPLICATION LAG  [Run: Every 5 minutes if read replicas exist]
-- =============================================================================

-- 8a. WAL sender status (primary side)
SELECT
    application_name,
    state,
    sent_lsn,
    write_lsn,
    flush_lsn,
    replay_lsn,
    pg_wal_lsn_diff(sent_lsn, replay_lsn) AS replication_lag_bytes,
    pg_size_pretty(pg_wal_lsn_diff(sent_lsn, replay_lsn)) AS replication_lag_pretty,
    sync_state
FROM pg_stat_replication
ORDER BY replication_lag_bytes DESC;

-- 8b. WAL archive status (for PITR)
SELECT
    archived_count,
    last_archived_wal,
    last_archived_time,
    failed_count,
    last_failed_wal,
    last_failed_time,
    CASE
        WHEN failed_count > 0  THEN '🚨 WAL archive failures detected'
        WHEN last_archived_time < now() - INTERVAL '30 minutes' THEN '⚠ WAL archiving may be stalled'
        ELSE 'OK'
    END AS status
FROM pg_stat_archiver;


-- =============================================================================
-- SECTION 9: BACKUP AGE MONITORING  [Run: Hourly]
-- =============================================================================
-- This query checks our backup metadata table (populated by backup.sh).
-- If the table doesn't exist yet, the backup script will create it on first run.

-- 9a. Check if backup_history table exists
SELECT EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'public'
      AND table_name = 'backup_history'
) AS backup_history_exists;

-- 9b. Latest backup age (run if backup_history exists)
-- ALERT: If latest_backup_age_hours > 25, the nightly backup may have failed.
/*
SELECT
    backup_type,
    file_name,
    file_size_mb,
    started_at,
    completed_at,
    EXTRACT(EPOCH FROM (now() - completed_at)) / 3600 AS age_hours,
    CASE
        WHEN EXTRACT(EPOCH FROM (now() - completed_at)) / 3600 > 25
        THEN '🚨 ALERT: backup is > 25 hours old'
        ELSE 'OK'
    END AS status
FROM backup_history
ORDER BY completed_at DESC
LIMIT 5;
*/


-- =============================================================================
-- SECTION 10: KAASB-SPECIFIC BUSINESS HEALTH  [Run: Daily]
-- =============================================================================

-- 10a. Financial integrity check: escrow amounts must balance
-- Any row here = data inconsistency (platform_fee + freelancer_amount ≠ amount)
SELECT
    id,
    amount,
    platform_fee,
    freelancer_amount,
    platform_fee + freelancer_amount AS sum_parts,
    amount - (platform_fee + freelancer_amount) AS discrepancy
FROM escrows
WHERE ABS(amount - (platform_fee + freelancer_amount)) > 0.0001
ORDER BY discrepancy DESC;

-- 10b. Contracts with amount_paid exceeding total_amount (should be 0)
SELECT id, total_amount, amount_paid, amount_paid - total_amount AS overpaid
FROM contracts
WHERE amount_paid > total_amount;

-- 10c. Orphaned escrows (escrow exists but milestone was deleted — should not happen with CASCADE)
SELECT e.id AS escrow_id, e.milestone_id, e.status, e.amount
FROM escrows e
LEFT JOIN milestones m ON m.id = e.milestone_id
WHERE m.id IS NULL;

-- 10d. Stale PENDING escrows (pending for > 2 hours — Qi Card payment likely abandoned)
SELECT
    id, amount, currency, created_at,
    EXTRACT(EPOCH FROM (now() - created_at)) / 3600 AS age_hours
FROM escrows
WHERE status = 'pending'
  AND created_at < now() - INTERVAL '2 hours'
ORDER BY created_at;

-- 10e. Connection pool utilization by application name (kaasb_api vs others)
SELECT
    application_name,
    COUNT(*)  AS connections,
    COUNT(*) FILTER (WHERE state = 'active')   AS active,
    COUNT(*) FILTER (WHERE state = 'idle')     AS idle,
    COUNT(*) FILTER (WHERE state LIKE 'idle in transaction%') AS idle_in_txn
FROM pg_stat_activity
WHERE datname = current_database()
GROUP BY application_name
ORDER BY connections DESC;

-- 10f. Recent failed login attempts (potential brute force)
-- Users with > 3 failed attempts in the last hour
SELECT
    email,
    username,
    failed_login_attempts,
    locked_until,
    last_login,
    created_at
FROM users
WHERE failed_login_attempts > 3
   OR locked_until > now()
ORDER BY failed_login_attempts DESC;

-- 10g. Platform financial summary (quick dashboard)
SELECT
    (SELECT COUNT(*)                FROM users       WHERE deleted_at IS NULL) AS total_users,
    (SELECT COUNT(*)                FROM jobs        WHERE status = 'open')    AS open_jobs,
    (SELECT COUNT(*)                FROM contracts   WHERE status = 'active')  AS active_contracts,
    (SELECT COALESCE(SUM(amount), 0) FROM escrows    WHERE status = 'funded')  AS escrow_held_usd,
    (SELECT COALESCE(SUM(amount), 0)
     FROM transactions
     WHERE transaction_type = 'platform_fee'
       AND status = 'completed'
       AND created_at > date_trunc('month', now())
    )                                                                          AS mtd_platform_fees;
