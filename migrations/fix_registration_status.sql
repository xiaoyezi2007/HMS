-- migrations/fix_registration_status.sql
-- Data-only migration: normalize registration.status values to three canonical values:
--   '排队中' (was '待就诊')
--   '就诊中' (was '办理中')
--   '已完成' (was '已就诊' or '已结束')
-- This script contains sections for MySQL, PostgreSQL, and SQLite. Run only the section that matches your DB.

-- =====================
-- MYSQL / MariaDB
-- =====================
-- Backup first: mysqldump -u <user> -p <db> > hms_db_backup.sql
-- Then run (example using mysql client): mysql -u <user> -p <db> < migrations/fix_registration_status.sql

-- MySQL section
UPDATE registration SET status = '排队中' WHERE status = '待就诊';
UPDATE registration SET status = '就诊中' WHERE status = '办理中';
UPDATE registration SET status = '已完成' WHERE status IN ('已就诊','已结束');
-- Also accept enum-name values that may be stored as English identifiers
UPDATE registration SET status = '排队中' WHERE status IN ('WAITING','waiting');
UPDATE registration SET status = '就诊中' WHERE status IN ('IN_PROGRESS','in_progress','inprogress');
UPDATE registration SET status = '已完成' WHERE status IN ('COMPLETED','FINISHED','completed','finished');
UPDATE registration SET status = '已取消' WHERE status IN ('CANCELLED','cancelled');

-- Optionally set column default (uncomment and edit if you want):
-- ALTER TABLE registration MODIFY status VARCHAR(64) NOT NULL DEFAULT '排队中';

-- =====================
-- POSTGRESQL
-- =====================
-- Backup first: pg_dump -U <user> -h <host> -d <db> -F p > hms_db_backup.sql
-- Then run using psql: psql -U <user> -d <db> -f migrations/fix_registration_status.sql

-- PostgreSQL section (same SQL works)
-- Note: if you paste the file into psql, you can run the same UPDATE statements:
-- UPDATE registration SET status = '排队中' WHERE status = '待就诊';
-- UPDATE registration SET status = '就诊中' WHERE status = '办理中';
-- UPDATE registration SET status = '已完成' WHERE status IN ('已就诊','已结束');
-- Also accept enum-name values that may be stored as English identifiers
-- UPDATE registration SET status = '排队中' WHERE status IN ('WAITING','waiting');
-- UPDATE registration SET status = '就诊中' WHERE status IN ('IN_PROGRESS','in_progress','inprogress');
-- UPDATE registration SET status = '已完成' WHERE status IN ('COMPLETED','FINISHED','completed','finished');
-- UPDATE registration SET status = '已取消' WHERE status IN ('CANCELLED','cancelled');

-- Optionally set default:
-- ALTER TABLE registration ALTER COLUMN status SET DEFAULT '排队中';

-- =====================
-- SQLITE
-- =====================
-- Backup first: copy .\<dbfile> .\<dbfile>.bak
-- Then run using sqlite3: sqlite3 <dbfile> ".read migrations/fix_registration_status.sql"

-- SQLite section (same UPDATEs):
-- UPDATE registration SET status = '排队中' WHERE status = '待就诊';
-- UPDATE registration SET status = '就诊中' WHERE status = '办理中';
-- UPDATE registration SET status = '已完成' WHERE status IN ('已就诊','已结束');
-- Also accept enum-name values that may be stored as English identifiers
-- UPDATE registration SET status = '排队中' WHERE status IN ('WAITING','waiting');
-- UPDATE registration SET status = '就诊中' WHERE status IN ('IN_PROGRESS','in_progress','inprogress');
-- UPDATE registration SET status = '已完成' WHERE status IN ('COMPLETED','FINISHED','completed','finished');
-- UPDATE registration SET status = '已取消' WHERE status IN ('CANCELLED','cancelled');

-- =====================
-- Rollback guidance
-- =====================
-- If you need to revert, restore from the backup created in step 1.
-- Alternatively, if you want a reverse script, you can change values back, but
-- a restore from backup is the safest rollback.

-- End of file
