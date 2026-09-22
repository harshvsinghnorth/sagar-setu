@echo off
cd /d "C:\Users\Asus VivoBook\Downloads\Sagar Setu"
set PYTHONIOENCODING=utf-8
uv run python scripts\daily_log.py --verify >> data\eval\daily_log.txt 2>&1
