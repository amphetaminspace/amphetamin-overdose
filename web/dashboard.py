"""
Web Dashboard for amphetamin_Overdose.
Wraps the trading engine for Passenger deployment.
Runs the trading loop in a background thread and provides a monitoring UI.
"""
import os
import sys
import threading
import json
from datetime import datetime
from typing import Dict, Optional

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template, jsonify, request
from loguru import logger

from core.engine import engine
from data.database import db
from config.settings import settings
from learning.learner import learner
from risk.risk_manager import risk_manager


# ── Flask App ──────────────────────────────────────────
app = Flask(__name__,
            template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
            static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.config['SECRET_KEY'] = os.urandom(24)

# ── Global State ───────────────────────────────────────
trading_thread: Optional[threading.Thread] = None
is_engine_running = False
engine_lock = threading.Lock()


def start_trading_engine():
    """Start the trading engine in a background thread."""
    global is_engine_running, trading_thread

    with engine_lock:
        if is_engine_running:
            logger.warning("Trading engine already running")
            return False

        is_engine_running = True

        def run_engine():
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(engine.initialize())
                loop.run_until_complete(engine.run())
            except Exception as e:
                logger.error(f"Engine error: {e}")
            finally:
                loop.close()
                global is_engine_running
                is_engine_running = False

        trading_thread = threading.Thread(target=run_engine, daemon=True)
        trading_thread.start()
        logger.info("Trading engine started in background thread")
        return True


def stop_trading_engine():
    """Stop the trading engine."""
    global is_engine_running
    with engine_lock:
        is_engine_running = False
        engine.is_running = False
        logger.info("Trading engine stop requested")
        return True


# ── Routes ─────────────────────────────────────────────

@app.route('/')
def index():
    """Main dashboard page."""
    return render_template('dashboard.html',
                         paper_trading=settings.paper_trading,
                         max_pairs=settings.max_pairs,
                         max_leverage=settings.max_leverage,
                         risk_per_trade=settings.risk_per_trade * 100,
                         daily_loss_limit=settings.daily_loss_limit * 100,
                         is_running=is_engine_running)


@app.route('/api/status')
def api_status():
    """Get current system status."""
    try:
        status = engine.get_status()
        status['is_running'] = is_engine_running
        status['paper_trading'] = settings.paper_trading
        status['timestamp'] = datetime.utcnow().isoformat()
        return jsonify(status)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/start', methods=['POST'])
def api_start():
    """Start the trading engine."""
    try:
        success = start_trading_engine()
        return jsonify({"success": success, "message": "Trading engine started"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/stop', methods=['POST'])
def api_stop():
    """Stop the trading engine."""
    try:
        success = stop_trading_engine()
        return jsonify({"success": success, "message": "Trading engine stopped"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/pairs')
def api_pairs():
    """Get current watchlist pairs."""
    try:
        session = db.get_session()
        pairs = db.get_active_pairs(session)
        session.close()
        return jsonify([{
            "symbol": p.symbol,
            "score": p.current_score,
            "volume_24h": p.volume_24h,
            "win_rate": p.win_rate,
        } for p in pairs])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/trades')
def api_trades():
    """Get recent trades."""
    try:
        session = db.get_session()
        trades = session.query(db.Trade).order_by(db.Trade.created_at.desc()).limit(50).all()
        session.close()
        return jsonify([{
            "id": t.id,
            "symbol": t.symbol,
            "direction": t.direction.value,
            "status": t.status.value,
            "entry_price": t.entry_price,
            "exit_price": t.exit_price,
            "pnl_pct": t.pnl_pct,
            "pnl_usd": t.pnl_usd,
            "strategy": t.strategy_used,
            "entry_time": t.entry_time.isoformat() if t.entry_time else None,
            "exit_time": t.exit_time.isoformat() if t.exit_time else None,
        } for t in trades])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/learning')
def api_learning():
    """Get learning model stats."""
    try:
        return jsonify(learner.get_performance_summary())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/risk')
def api_risk():
    """Get risk management stats."""
    try:
        return jsonify(risk_manager.get_daily_stats())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/scan', methods=['POST'])
def api_scan():
    """Trigger market scan."""
    try:
        import asyncio
        loop = asyncio.new_event_loop()
        pairs = loop.run_until_complete(portfolio_manager.scan_and_rank_pairs())
        loop.close()
        return jsonify({"success": True, "pairs_found": len(pairs)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/health')
def health():
    """Health check for Passenger."""
    return jsonify({"status": "ok", "running": is_engine_running})


# ── Passenger WSGI Entry Point ──────────────────────────
# Passenger looks for 'application' by default
application = app

# For development
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
