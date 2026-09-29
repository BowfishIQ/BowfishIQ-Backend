from fastapi import FastAPI
import os
from fastapi.staticfiles import StaticFiles
from os import getcwd
from config import APP_NAME
from cors_config import setup_cors

from Routes import locationRoute, userRoute

app = FastAPI(title=APP_NAME)
os.makedirs(getcwd() + "/uploads/", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# ==================================================================================
# ============= Allow requests from localhost during development start =============
# ==================================================================================
# Setup CORS using the configuration from cors_config.py
setup_cors(app)


# USER ROUTE START
app.include_router(userRoute.router)

# LOCATION ROUTE START
app.include_router(locationRoute.router)
