@echo off
cd /d "C:\Users\Asus VivoBook\Downloads\Sagar Setu"
set PYTHONIOENCODING=utf-8
uv run python scripts\daily_log.py --log >> data\eval\daily_log.txt 2>&1
