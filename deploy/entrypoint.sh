#!/bin/bash
# =============================================================================
# Edge Service Entrypoint — dispatches to the correct service based on
# the SERVICE_NAME environment variable.
# =============================================================================

set -e

if [ -z "$SERVICE_NAME" ]; then
    echo "ERROR: SERVICE_NAME env var is required"
    echo "Valid values: session, regime, funding, correlation, alpha, arb,"
    echo "  funding-scanner, narrative, rewards, inventory, hedge, pnl,"
    echo "  lab, alert, swarm, clmm, watchlist, unlock, backtest, migration"
    exit 1
fi

# Map service name → directory and script
case "$SERVICE_NAME" in
    session)          cd /app/session-service          && exec python session_service.py ;;
    regime)           cd /app/regime-service           && exec python regime_classifier.py ;;
    funding)          cd /app/funding-service          && exec python funding_service.py ;;
    correlation)      cd /app/correlation-service      && exec python correlation_service.py ;;
    alpha)            cd /app/alpha-service            && exec python alpha_service.py ;;
    arb)              cd /app/arb-service              && exec python arb_service.py ;;
    funding-scanner)  cd /app/funding-scanner-service  && exec python funding_scanner_service.py ;;
    narrative)        cd /app/narrative-service         && exec python narrative_service.py ;;
    rewards)          cd /app/rewards-service           && exec python rewards_service.py ;;
    inventory)        cd /app/inventory-service         && exec python inventory_service.py ;;
    hedge)            cd /app/hedge-service             && exec python hedge_service.py ;;
    pnl)              cd /app/pnl-service               && exec python pnl_service.py ;;
    lab)              cd /app/lab-service               && exec python lab_service.py ;;
    alert)            cd /app/alert-service             && exec python alert_service.py ;;
    swarm)            cd /app/swarm-service             && exec python swarm_service.py ;;
    clmm)             cd /app/clmm-service              && exec python clmm_service.py ;;
    watchlist)        cd /app/watchlist-service          && exec python watchlist_service.py ;;
    unlock)           cd /app/unlock-service             && exec python unlock_service.py ;;
    backtest)         cd /app/backtest-service            && exec python backtest_service.py ;;
    migration)        cd /app/migration-service           && exec python migration_service.py ;;
    *)
        echo "ERROR: Unknown SERVICE_NAME: $SERVICE_NAME"
        exit 1
        ;;
esac
