#!/usr/bin/env bash
cd "$(dirname "$0")"
python -m streamlit run app.py --server.port 8502
