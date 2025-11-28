# run_delete_history.ps1
# 用法示例：
# 1) 预览（dry-run）：直接运行（脚本默认 DoDelete=0）
#    .\run_delete_history.ps1 -ServerInstance "localhost" -Database "HMS" -User "sa" -Password "YourPassword"
# 2) 执行删除：请先编辑 scripts\delete_history.sql 将 @DoDelete 设置为 1，或用交互方式传入参数并在服务器上直接修改

param(
    [string]$ServerInstance = "localhost",
    [string]$Database = "HMS",
    [string]$User = "sa",
    [string]$Password = "YourPassword",
    [string]$SqlFile = "scripts\delete_history.sql"
)

if (-not (Test-Path $SqlFile)) {
    Write-Error "找不到 SQL 文件： $SqlFile"; exit 1
}

$escapedPassword = $Password -replace '"','\"'
$sqlcmd = "sqlcmd -S $ServerInstance -U $User -P \"$escapedPassword\" -d $Database -i $SqlFile"
Write-Host "将执行： $sqlcmd"
Invoke-Expression $sqlcmd

# 说明：脚本会在 SQL Server 上以指定用户执行 SQL 文件。确保该用户有充分权限（BACKUP/DELETE 等）。
