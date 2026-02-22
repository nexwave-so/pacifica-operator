# Database Recovery & Backup Guide - Nexwave

## Overview

This guide covers database backup, recovery, and crash prevention measures for the Nexwave trading platform.

## Crash Prevention Measures

### PostgreSQL Configuration

The following settings have been enabled to prevent database corruption during unclean shutdowns (power loss, force kill):

**Durability Settings:**
- `fsync=on` - Forces all writes to disk immediately (prevents data loss)
- `synchronous_commit=on` - Waits for WAL writes before confirming transactions  
- `full_page_writes=on` - Writes complete pages after checkpoints (crash safety)
- `wal_level=replica` - Enables Write-Ahead Logging for recovery
- `checkpoint_timeout=15min` - More frequent checkpoints reduce recovery time

**Restart Behavior:**
- `restart: unless-stopped` - Auto-restarts after crashes
- `stop_grace_period: 30s` - Allows clean shutdown (flushes buffers)

## Quick Start

**Setup automated backups:**
```bash
./scripts/backup-cron.sh
```

**Manual backup:**
```bash
./scripts/backup-database.sh
```

**Restore from backup:**
```bash
./scripts/restore-database.sh nexwave_backup_20251114_180000.sql.gz
```

See full documentation below for detailed procedures.
