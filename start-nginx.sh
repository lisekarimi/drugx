#!/bin/bash

# Start Streamlit in background
streamlit run src/frontend/app.py --server.address 0.0.0.0 --server.port 7860 &

# Wait for Streamlit to fully start
sleep 8

# Start nginx in foreground
nginx -g "daemon off;"
