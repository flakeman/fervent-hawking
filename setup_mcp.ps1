# PowerShell script to automatically configure the 1C MCP server paths in AI Agent configuration files.
# Run this script from the workspace directory.

$ErrorActionPreference = "Stop"

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host " Настройка 1C MCP Server для AI Ассистента" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

# 1. Определение путей
$WorkspacePath = $PSScriptRoot
if (-not $WorkspacePath) {
    $WorkspacePath = Get-Location
}
$WorkspacePath = $WorkspacePath.ToString().Replace('\', '/')

$McpScriptPath = "$WorkspacePath/mcp/mcp_1c_helper.py"
$IndexPath = "$WorkspacePath/data/1c_compact_index.json"

# Проверка существования файлов
if (-not (Test-Path $McpScriptPath)) {
    Write-Error "Файл сервера не найден по пути: $McpScriptPath. Убедитесь, что запускаете скрипт из корня репозитория."
}
if (-not (Test-Path $IndexPath)) {
    Write-Host "Внимание: Компактный индекс не найден по пути $IndexPath. Не забудьте пересобрать его при необходимости." -ForegroundColor Yellow
}

# 2. Поиск файлов конфигурации ассистентов
$HomeDir = [System.Environment]::GetFolderPath("UserProfile")
$AppDataDir = [System.Environment]::GetFolderPath("ApplicationData")

$ConfigsToUpdate = @()

# Настройки для Gemini Agent / Antigravity
$GeminiConfig = Join-Path $HomeDir ".gemini\antigravity\mcp_config.json"
if (Test-Path $GeminiConfig) { $ConfigsToUpdate += ,@($GeminiConfig, "Gemini Agent") }

# Настройки для Claude Desktop
$ClaudeConfig = Join-Path $AppDataDir "Claude\claude_desktop_config.json"
if (Test-Path $ClaudeConfig) { $ConfigsToUpdate += ,@($ClaudeConfig, "Claude Desktop") }

if ($ConfigsToUpdate.Count -eq 0) {
    Write-Host "Файлы конфигураций ассистентов (Gemini, Claude Desktop) не найдены в стандартных путях." -ForegroundColor Yellow
    Write-Host "Создаем локальный шаблон настроек mcp_config.json в папке проекта..." -ForegroundColor Yellow
    
    $LocalConfigPath = Join-Path $PSScriptRoot "mcp_config.json"
} else {
    foreach ($configInfo in $ConfigsToUpdate) {
        $path = $configInfo[0]
        $name = $configInfo[1]
        
        Write-Host "Обнаружена конфигурация для $name: $path" -ForegroundColor Green
        
        try {
            $json = Get-Content -Path $path -Raw | ConvertFrom-Json
            
            # Инициализация структуры, если отсутствует
            if (-not $json.mcpServers) {
                $json | Add-Member -MemberType NoteProperty -Name "mcpServers" -Value (New-Object PSObject)
            }
            
            # Подготовка настроек 1c-helper
            $helperConfig = [ordered]@{
                "command" = "python"
                "args"    = @($McpScriptPath)
                "env"     = [ordered]@{
                    "1C_ODATA_URL"      = "http://localhost/1c_db/odata/standard.odata/"
                    "1C_ODATA_USER"     = "Administrator"
                    "1C_ODATA_PASSWORD" = ""
                    "1C_INDEX_FILE"     = $IndexPath
                }
            }
            
            # Добавление или обновление секции
            if ($json.mcpServers.PSObject.Properties["1c-helper"]) {
                $json.mcpServers.PSObject.Properties["1c-helper"].Value = $helperConfig
                Write-Host "  -> Обновляем существующие пути..." -ForegroundColor Cyan
            } else {
                $json.mcpServers | Add-Member -MemberType NoteProperty -Name "1c-helper" -Value $helperConfig
                Write-Host "  -> Добавляем новую конфигурацию..." -ForegroundColor Cyan
            }
            
            # Сохранение файла
            $newJsonStr = $json | ConvertTo-Json -Depth 10
            # Устранение возможных проблем с экранированием слэшей в Windows
            $newJsonStr = $newJsonStr.Replace('\\', '/')
            [System.IO.File]::WriteAllText($path, $newJsonStr, [System.Text.Encoding]::UTF8)
            
            Write-Host "Успешно настроено!" -ForegroundColor Green
        }
        catch {
            Write-Host "Ошибка при обновлении файла $path: $_" -ForegroundColor Red
        }
    }
}

Write-Host "`nКонфигурация завершена!" -ForegroundColor Green
Write-Host "Если ассистент был запущен, перезапустите его или обновите список MCP-серверов." -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
