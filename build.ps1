# Pet Reminder v10.2 — Сборка exe
# Запуск: правой кнопкой на файл -> "Выполнить с помощью PowerShell"
# Или из терминала: powershell -ExecutionPolicy Bypass -File build.ps1

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Pet Reminder v10.2 — Сборка exe" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Проверяем что запущены из папки с проектом
if (-not (Test-Path "pet.py")) {
    Write-Host "[ОШИБКА] Запусти скрипт из папки с проектом (рядом с pet.py)" -ForegroundColor Red
    Read-Host "Нажми Enter для выхода"
    exit 1
}

# Проверяем Python
try {
    $pyVersion = python --version 2>&1
    Write-Host "[OK] $pyVersion" -ForegroundColor Green
} catch {
    Write-Host "[ОШИБКА] Python не найден. Установи с https://python.org" -ForegroundColor Red
    Read-Host "Нажми Enter для выхода"
    exit 1
}

# Проверяем папки анимаций
foreach ($folder in @("idle_clean", "click_clean", "sleeping_clean")) {
    if (-not (Test-Path $folder)) {
        Write-Host "[ПРЕДУПРЕЖДЕНИЕ] Папка $folder не найдена — анимации не войдут в exe" -ForegroundColor Yellow
    } else {
        Write-Host "[OK] Папка $folder найдена" -ForegroundColor Green
    }
}

# Иконка — предпочитаем icon.ico, фолбэк на Icon.png
if (-not (Test-Path "icon.ico")) {
    if (Test-Path "Icon.png") {
        Copy-Item "Icon.png" "icon.ico"
        Write-Host "[ИНФО] icon.ico не найден — скопирован из Icon.png" -ForegroundColor Yellow
    } else {
        Write-Host "[ПРЕДУПРЕЖДЕНИЕ] Ни icon.ico ни Icon.png не найдены — exe будет без иконки" -ForegroundColor Yellow
    }
} else {
    Write-Host "[OK] icon.ico найден" -ForegroundColor Green
}

Write-Host ""

# Устанавливаем PyInstaller если нет
$piInstalled = pip show pyinstaller 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Устанавливаю PyInstaller..." -ForegroundColor Cyan
    pip install pyinstaller
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ОШИБКА] Не удалось установить PyInstaller" -ForegroundColor Red
        Read-Host "Нажми Enter для выхода"
        exit 1
    }
} else {
    Write-Host "[OK] PyInstaller установлен" -ForegroundColor Green
}

# Устанавливаем PyQt5 если нет
$qt5Installed = pip show PyQt5 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Устанавливаю PyQt5..." -ForegroundColor Cyan
    pip install PyQt5
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ОШИБКА] Не удалось установить PyQt5" -ForegroundColor Red
        Read-Host "Нажми Enter для выхода"
        exit 1
    }
} else {
    Write-Host "[OK] PyQt5 установлен" -ForegroundColor Green
}

Write-Host ""
Write-Host "Запускаю сборку..." -ForegroundColor Cyan
Write-Host ""

# Сборка через spec или напрямую
if (Test-Path "pet.spec") {
    Write-Host "[ИНФО] Использую pet.spec" -ForegroundColor Cyan
    pyinstaller pet.spec --clean --noconfirm
} else {
    Write-Host "[ИНФО] pet.spec не найден, собираю напрямую" -ForegroundColor Yellow
    pyinstaller `
        --noconfirm --clean --onefile --windowed `
        --icon=icon.ico `
        --version-file=version.txt `
        --add-data "idle_clean;idle_clean" `
        --add-data "click_clean;click_clean" `
        --add-data "sleeping_clean;sleeping_clean" `
        --add-data "Icon.png;." `
        --hidden-import=PyQt5 `
        --hidden-import=PyQt5.sip `
        --hidden-import=winreg `
        --exclude-module=matplotlib `
        --exclude-module=numpy `
        --exclude-module=tkinter `
        --name=pet `
        pet.py
}

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "[ОШИБКА] Сборка не удалась." -ForegroundColor Red
    Write-Host "Если видишь ModuleNotFoundError — добавь модуль в hiddenimports в pet.spec" -ForegroundColor Yellow
    Read-Host "Нажми Enter для выхода"
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Готово!  dist\pet.exe" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# Открываем папку с результатом
if (Test-Path "dist\pet.exe") {
    Start-Process explorer.exe -ArgumentList "dist"
} else {
    Write-Host "[ВНИМАНИЕ] dist\pet.exe не найден — проверь вывод выше" -ForegroundColor Yellow
}

Read-Host "Нажми Enter для выхода"
