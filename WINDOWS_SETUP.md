#!/bin/bash
# Windows Setup Guide for City_Mood
# Run this on Windows PowerShell to verify setup

echo "🔍 City_Mood Windows Setup Verification"
echo "========================================"
echo ""

# Check Python
echo "✓ Checking Python..."
python --version
if ($LASTEXITCODE -ne 0) {
    echo "❌ Python not installed or not in PATH"
    exit 1
}

# Check MySQL
echo ""
echo "✓ Checking MySQL..."
mysql --version
if ($LASTEXITCODE -ne 0) {
    echo "❌ MySQL not installed or not in PATH"
    exit 1
}

# Check .env file
echo ""
echo "✓ Checking .env file..."
if (Test-Path ".env") {
    echo "✅ .env file exists"
    Write-Host "   DB_HOST: $(grep 'DB_HOST=' .env)"
    Write-Host "   DB_PORT: $(grep 'DB_PORT=' .env)"
} else {
    echo "❌ .env file not found"
    exit 1
}

# Check requirements
echo ""
echo "✓ Checking Python packages..."
pip list | findstr /R "mysql-connector requests apscheduler python-dotenv"

echo ""
echo "✅ Setup verification complete!"
echo ""
echo "Next steps:"
echo "1. python init_db.py          # Initialize database"
echo "2. python aggregator.py       # Start aggregator"
