-- delete_history.sql
-- 用法说明：
-- 1) 先备份数据库（强烈推荐）。
-- 2) 默认脚本处于 DRY RUN 模式（@DoDelete = 0），仅会输出将被删除的记录计数。
-- 3) 若确认无误，将 @DoDelete 设置为 1 并（可选）设置 @StartDate/@EndDate 限定删除范围，然后运行脚本以执行真正的删除。
-- 注意：此脚本按外键顺序删除，适用于测试环境。正式环境务必先备份。

SET NOCOUNT ON;

-- ==================== 配置项 ====================
DECLARE @DoDelete BIT = 0; -- 0 = 仅预览 (dry-run), 1 = 执行删除
-- 可选按时间范围删除：填写起止日期（包含），留 NULL 表示不限
DECLARE @StartDate DATETIME2 = NULL; -- e.g. '2025-01-01'
DECLARE @EndDate DATETIME2 = NULL;   -- e.g. '2025-12-31'

-- 如果只想按挂号 ID 或记录 ID 删除，请把下面两个变量设置为非 NULL
DECLARE @MinRegId INT = NULL; -- 例如 100
DECLARE @MaxRegId INT = NULL; -- 例如 200

-- =================================================

-- helper: 构造删除记录集（根据 reg->record->prescription 关联）
-- 获取要删除的 registration id 列表
CREATE TABLE #ToDeleteRegs (reg_id INT PRIMARY KEY);

INSERT INTO #ToDeleteRegs (reg_id)
SELECT r.reg_id
FROM dbo.Registration r
LEFT JOIN dbo.MedicalRecord mr ON mr.reg_id = r.reg_id
LEFT JOIN dbo.Prescription p ON p.record_id = mr.record_id
WHERE 1=1
  -- 按时间范围（挂号时间）过滤
  AND (@StartDate IS NULL OR r.reg_date >= @StartDate)
  AND (@EndDate IS NULL OR r.reg_date <= @EndDate)
  -- 按 reg_id 范围过滤
  AND (@MinRegId IS NULL OR r.reg_id >= @MinRegId)
  AND (@MaxRegId IS NULL OR r.reg_id <= @MaxRegId)
;

-- 统计将要删除的项
SELECT
  (SELECT COUNT(*) FROM #ToDeleteRegs) AS RegistrationsToDelete,
  (SELECT COUNT(*) FROM Prescription p JOIN MedicalRecord mr ON p.record_id = mr.record_id JOIN #ToDeleteRegs t ON mr.reg_id = t.reg_id) AS PrescriptionsToDelete,
  (SELECT COUNT(*) FROM PrescriptionDetail pd JOIN Prescription p ON pd.pres_id = p.pres_id JOIN MedicalRecord mr ON p.record_id = mr.record_id JOIN #ToDeleteRegs t ON mr.reg_id = t.reg_id) AS PrescriptionDetailsToDelete,
  (SELECT COUNT(*) FROM Examination e JOIN MedicalRecord mr ON e.record_id = mr.record_id JOIN #ToDeleteRegs t ON mr.reg_id = t.reg_id) AS ExaminationsToDelete,
  (SELECT COUNT(*) FROM MedicalRecord mr JOIN #ToDeleteRegs t ON mr.reg_id = t.reg_id) AS MedicalRecordsToDelete
;

IF @DoDelete = 0
BEGIN
    PRINT 'DRY RUN: 未执行删除。若确认，请将 @DoDelete 设置为 1 到脚本中并重新运行。';
    DROP TABLE #ToDeleteRegs;
    RETURN;
END

-- 执行删除（在事务中）
BEGIN TRANSACTION;
BEGIN TRY

    -- 保存被删除主键备份到临时表（便于审计/回滚时参考）
    CREATE TABLE #DeletedPrescriptions (pres_id INT PRIMARY KEY);
    CREATE TABLE #DeletedPrescriptionDetails (detail_id INT PRIMARY KEY);
    CREATE TABLE #DeletedExams (exam_id INT PRIMARY KEY);
    CREATE TABLE #DeletedRecords (record_id INT PRIMARY KEY);
    CREATE TABLE #DeletedRegistrations (reg_id INT PRIMARY KEY);

    -- 1) 处方明细
    INSERT INTO #DeletedPrescriptionDetails (detail_id)
    SELECT pd.detail_id
    FROM dbo.PrescriptionDetail pd
    JOIN dbo.Prescription p ON pd.pres_id = p.pres_id
    JOIN dbo.MedicalRecord mr ON p.record_id = mr.record_id
    JOIN #ToDeleteRegs t ON mr.reg_id = t.reg_id;

    DELETE pd
    FROM dbo.PrescriptionDetail pd
    JOIN dbo.Prescription p ON pd.pres_id = p.pres_id
    JOIN dbo.MedicalRecord mr ON p.record_id = mr.record_id
    JOIN #ToDeleteRegs t ON mr.reg_id = t.reg_id;

    -- 2) 处方头
    INSERT INTO #DeletedPrescriptions (pres_id)
    SELECT p.pres_id
    FROM dbo.Prescription p
    JOIN dbo.MedicalRecord mr ON p.record_id = mr.record_id
    JOIN #ToDeleteRegs t ON mr.reg_id = t.reg_id;

    DELETE p
    FROM dbo.Prescription p
    JOIN dbo.MedicalRecord mr ON p.record_id = mr.record_id
    JOIN #ToDeleteRegs t ON mr.reg_id = t.reg_id;

    -- 3) 检查
    INSERT INTO #DeletedExams (exam_id)
    SELECT e.exam_id
    FROM dbo.Examination e
    JOIN dbo.MedicalRecord mr ON e.record_id = mr.record_id
    JOIN #ToDeleteRegs t ON mr.reg_id = t.reg_id;

    DELETE e
    FROM dbo.Examination e
    JOIN dbo.MedicalRecord mr ON e.record_id = mr.record_id
    JOIN #ToDeleteRegs t ON mr.reg_id = t.reg_id;

    -- 4) 病历
    INSERT INTO #DeletedRecords (record_id)
    SELECT mr.record_id
    FROM dbo.MedicalRecord mr
    JOIN #ToDeleteRegs t ON mr.reg_id = t.reg_id;

    DELETE mr
    FROM dbo.MedicalRecord mr
    JOIN #ToDeleteRegs t ON mr.reg_id = t.reg_id;

    -- 5) 挂号（如果你也要删除挂号）
    INSERT INTO #DeletedRegistrations (reg_id)
    SELECT r.reg_id FROM dbo.Registration r JOIN #ToDeleteRegs t ON r.reg_id = t.reg_id;

    DELETE r
    FROM dbo.Registration r
    JOIN #ToDeleteRegs t ON r.reg_id = t.reg_id;

    -- 若存在 Payment 表并希望同时删除与处方/检查/住院相关的付款记录，可在此处扩展

    COMMIT TRANSACTION;

    PRINT '删除成功。已提交事务。';

    -- 可选：将删除清单输出到表或文件
    SELECT * FROM #DeletedRegistrations;
    SELECT * FROM #DeletedRecords;
    SELECT * FROM #DeletedPrescriptions;
    SELECT * FROM #DeletedPrescriptionDetails;
    SELECT * FROM #DeletedExams;

    DROP TABLE #ToDeleteRegs;
    DROP TABLE #DeletedPrescriptions;
    DROP TABLE #DeletedPrescriptionDetails;
    DROP TABLE #DeletedExams;
    DROP TABLE #DeletedRecords;
    DROP TABLE #DeletedRegistrations;

END TRY
BEGIN CATCH
    ROLLBACK TRANSACTION;
    DECLARE @ErrMsg NVARCHAR(4000) = ERROR_MESSAGE();
    DECLARE @ErrNo INT = ERROR_NUMBER();
    PRINT '发生错误，已回滚。错误信息：';
    PRINT @ErrNo;
    PRINT @ErrMsg;
    DROP TABLE IF EXISTS #ToDeleteRegs;
    THROW;
END CATCH;

GO
