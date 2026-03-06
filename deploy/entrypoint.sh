#!/bin/bash

set -e

if [ -z "$SERVICE_NAME" ]; then
    echo "ERROR: SERVICE_NAME env var is required"
    echo "Valid values: session, alpha, arb, narrative, rewards,"
    echo "  inventory, hedge, pnl,"
    echo "  alert, clmm, watchlist"
    exit 1
fi

case "$SERVICE_NAME" in
    session)          cd /app/session-service          && exec python session_service.py ;;
    alpha)            cd /app/alpha-service            && exec python alpha_service.py ;;
    arb)              cd /app/arb-service              && exec python arb_service.py ;;
    narrative)        cd /app/narrative-service         && exec python narrative_service.py ;;
    rewards)          cd /app/rewards-service           && exec python rewards_service.py ;;
    inventory)        cd /app/inventory-service         && exec python inventory_service.py ;;
    hedge)            cd /app/hedge-service             && exec python hedge_service.py ;;
    pnl)              cd /app/pnl-service               && exec python pnl_service.py ;;
    alert)            cd /app/alert-service             && exec python alert_service.py ;;
    clmm)             cd /app/clmm-service              && exec python clmm_service.py ;;
    watchlist)        cd /app/watchlist-service          && exec python watchlist_service.py ;;
    *)
        echo "ERROR: Unknown SERVICE_NAME: $SERVICE_NAME"
        exit 1
        ;;
esac
