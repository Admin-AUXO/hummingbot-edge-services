# =============================================================================
# Hummingbot Edge Services — Shared Dockerfile
# Builds a single image containing all 20 Python edge services + shared module.
# Each service is started by specifying the SERVICE_NAME env var at runtime.
# =============================================================================

FROM python:3.12-bookworm

# Prevent Python from writing .pyc files and enable unbuffered output for logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install Python dependencies (layer cache optimization)
COPY requirements.txt .
RUN pip install --no-cache-dir paho-mqtt requests pydantic pydantic-settings numpy pandas pyyaml numba pandas-ta

# Copy shared module
COPY shared/ ./shared/

# Copy all service directories
COPY alert-service/         ./alert-service/
COPY alpha-service/         ./alpha-service/
COPY arb-service/           ./arb-service/
COPY backtest-service/      ./backtest-service/
COPY clmm-service/          ./clmm-service/
COPY correlation-service/   ./correlation-service/
COPY funding-scanner-service/ ./funding-scanner-service/
COPY funding-service/       ./funding-service/
COPY hedge-service/         ./hedge-service/
COPY inventory-service/     ./inventory-service/
COPY lab-service/           ./lab-service/
COPY migration-service/     ./migration-service/
COPY narrative-service/     ./narrative-service/
COPY pnl-service/           ./pnl-service/
COPY regime-service/        ./regime-service/
COPY rewards-service/       ./rewards-service/
COPY session-service/       ./session-service/
COPY swarm-service/         ./swarm-service/
COPY unlock-service/        ./unlock-service/
COPY watchlist-service/     ./watchlist-service/

# Entrypoint script that dispatches to the correct service
COPY deploy/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
