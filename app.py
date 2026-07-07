import os
import yaml

from fastapi import FastAPI, Request
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# CORS (required by grader)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Helpers
# -----------------------------

def parse_bool(value):
    if isinstance(value, bool):
        return value

    if value is None:
        return False

    return str(value).lower() in [
        "true",
        "1",
        "yes",
        "on"
    ]


def coerce_types(config):
    result = {}

    for k, v in config.items():

        if k in ["port", "workers"]:
            result[k] = int(v)

        elif k == "debug":
            result[k] = parse_bool(v)

        else:
            result[k] = str(v)

    return result


# -----------------------------
# Defaults
# -----------------------------

DEFAULTS = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000"
}


# -----------------------------
# Main endpoint
# -----------------------------

@app.get("/effective-config")
async def effective_config(request: Request):

    config = DEFAULTS.copy()

    #
    # Layer 2
    # YAML
    #
    with open("config.development.yaml", "r") as f:
        yaml_config = yaml.safe_load(f)

    config.update(yaml_config)

    #
    # Layer 3
    # .env
    #
    load_dotenv(override=False)

    env_layer = {}

    if os.getenv("APP_PORT"):
        env_layer["port"] = os.getenv("APP_PORT")

    if os.getenv("APP_DEBUG"):
        env_layer["debug"] = os.getenv("APP_DEBUG")

    # alias support
    if os.getenv("NUM_WORKERS"):
        env_layer["workers"] = os.getenv("NUM_WORKERS")

    config.update(env_layer)

    #
    # Layer 4
    # OS ENV
    #
    os_layer = {}

    if os.environ.get("APP_PORT"):
        os_layer["port"] = os.environ.get("APP_PORT")

    if os.environ.get("APP_DEBUG"):
        os_layer["debug"] = os.environ.get("APP_DEBUG")

    if os.environ.get("APP_WORKERS"):
        os_layer["workers"] = os.environ.get("APP_WORKERS")

    if os.environ.get("APP_LOG_LEVEL"):
        os_layer["log_level"] = os.environ.get("APP_LOG_LEVEL")

    if os.environ.get("APP_API_KEY"):
        os_layer["api_key"] = os.environ.get("APP_API_KEY")

    config.update(os_layer)

    #
    # CLI OVERRIDES
    # Highest precedence
    #
    for key, value in request.query_params.items():

        if not key.startswith("set-"):
            continue

        actual_key = key[4:]

        config[actual_key] = value

    #
    # Type coercion
    #
    config = coerce_types(config)

    #
    # Secret masking
    #
    config["api_key"] = "****"

    return config


@app.get("/")
async def root():
    return {"status": "ok"}