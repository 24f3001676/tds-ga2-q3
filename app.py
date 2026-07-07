import os
import yaml

from fastapi import FastAPI, Request
from dotenv import dotenv_values
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# --------------------------------
# CORS
# --------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------
# Helpers
# --------------------------------

def parse_bool(value):
    if isinstance(value, bool):
        return value

    if value is None:
        return False

    return str(value).strip().lower() in {
        "true",
        "1",
        "yes",
        "on"
    }


def coerce_types(config):
    result = {}

    for k, v in config.items():

        if k in ("port", "workers"):
            result[k] = int(v)

        elif k == "debug":
            result[k] = parse_bool(v)

        else:
            result[k] = str(v)

    return result


# --------------------------------
# Defaults
# --------------------------------

DEFAULTS = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000"
}


# --------------------------------
# Endpoint
# --------------------------------

@app.get("/effective-config")
async def effective_config(request: Request):

    config = DEFAULTS.copy()

    # -----------------------------
    # Layer 2: YAML
    # -----------------------------
    try:
        with open("config.development.yaml", "r") as f:
            yaml_config = yaml.safe_load(f) or {}
            config.update(yaml_config)
    except FileNotFoundError:
        pass

    # -----------------------------
    # Layer 3: .env
    # -----------------------------
    dotenv_data = dotenv_values(".env")

    env_layer = {}

    if "APP_PORT" in dotenv_data:
        env_layer["port"] = dotenv_data["APP_PORT"]

    if "APP_DEBUG" in dotenv_data:
        env_layer["debug"] = dotenv_data["APP_DEBUG"]

    # alias required by assignment
    if "NUM_WORKERS" in dotenv_data:
        env_layer["workers"] = dotenv_data["NUM_WORKERS"]

    config.update(env_layer)

    # -----------------------------
    # Layer 4: OS Environment
    # -----------------------------
    os_layer = {}

    if "APP_PORT" in os.environ:
        os_layer["port"] = os.environ["APP_PORT"]

    if "APP_DEBUG" in os.environ:
        os_layer["debug"] = os.environ["APP_DEBUG"]

    if "APP_WORKERS" in os.environ:
        os_layer["workers"] = os.environ["APP_WORKERS"]

    if "APP_LOG_LEVEL" in os.environ:
        os_layer["log_level"] = os.environ["APP_LOG_LEVEL"]

    if "APP_API_KEY" in os.environ:
        os_layer["api_key"] = os.environ["APP_API_KEY"]

    config.update(os_layer)

    # -----------------------------
    # Layer 5: CLI Overrides
    # Highest precedence
    # -----------------------------

    # Format:
    # ?set-port=9000
    # ?set-debug=true

    for key, value in request.query_params.items():

        if key.startswith("set-"):
            actual_key = key[4:]
            config[actual_key] = value

    # Format:
    # ?set=workers=10
    # ?set=log_level=error

    set_values = request.query_params.getlist("set")

    for item in set_values:

        if "=" not in item:
            continue

        k, v = item.split("=", 1)
        config[k] = v

    # -----------------------------
    # Type coercion
    # -----------------------------
    config = coerce_types(config)

    # -----------------------------
    # Mask secret
    # -----------------------------
    config["api_key"] = "****"

    return config


@app.get("/")
async def root():
    return {"status": "ok"}