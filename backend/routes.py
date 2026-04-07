"""
Wake-on-LAN premium tab Flask blueprint.
CSV at premium root (path from config.json). Integrates with DHCP leases for add-from-lease.
"""

from flask import Blueprint, request, jsonify, current_app

from .wol import (
    load_targets,
    wake_targets,
    get_wol_csv_path,
    ensure_csv_with_header,
    append_target,
    remove_target,
    broadcast_from_ip,
)

bp = Blueprint("wakeonlan", __name__, url_prefix="/api/wakeonlan")


@bp.route("/targets", methods=["GET"])
def get_targets():
    """List WoL targets from CSV."""
    try:
        targets = load_targets()
        current_app.logger.info("WoL targets listed", extra={"count": len(targets)})
        return jsonify({
            "success": True,
            "targets": [{"name": t["name"], "mac": t["mac_str"], "broadcast": t["broadcast"]} for t in targets],
        })
    except FileNotFoundError as e:
        current_app.logger.warning("WoL CSV missing", extra={"path": str(get_wol_csv_path())})
        return jsonify({"success": False, "error": str(e), "targets": []}), 404
    except ValueError as e:
        current_app.logger.error("WoL CSV invalid", extra={"error": str(e)})
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        current_app.logger.exception("WoL list failed")
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/wake", methods=["POST"])
def wake():
    """Wake one or more targets by name, or all. JSON: { \"name\": \"workstation\" } or { \"wake_all\": true }."""
    try:
        data = request.get_json(silent=True) or {}
        wake_all = data.get("wake_all") is True
        name = data.get("name")
        names = [name] if isinstance(name, str) and name.strip() else (data.get("names") or [])

        if not wake_all and not names:
            return jsonify({"success": False, "error": "Provide 'name', 'names', or 'wake_all': true"}), 400

        targets = load_targets()
        if not targets:
            return jsonify({"success": False, "error": "No targets in CSV"}), 404

        sent = wake_targets(targets, names=names if not wake_all else None, wake_all=wake_all)
        current_app.logger.info("WoL sent", extra={"count": len(sent), "names": [t["name"] for t in sent]})
        return jsonify({
            "success": True,
            "woke": [{"name": t["name"], "mac": t["mac_str"]} for t in sent],
        })
    except FileNotFoundError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        current_app.logger.exception("WoL wake failed")
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/status", methods=["GET"])
def status():
    """Tab status and CSV path hint."""
    try:
        targets = load_targets()
        return jsonify({
            "success": True,
            "status": "active",
            "csv_path": str(get_wol_csv_path()),
            "target_count": len(targets),
        })
    except FileNotFoundError:
        return jsonify({
            "success": True,
            "status": "active",
            "csv_path": str(get_wol_csv_path()),
            "target_count": 0,
            "message": "CSV not found; add premium/wakeonlan.csv with name,mac,broadcast",
        })
    except Exception as e:
        current_app.logger.exception("WoL status failed")
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/targets", methods=["POST"])
def add_target():
    """Add a WoL target to CSV. Body: { name, mac, broadcast? }. Broadcast derived from IP if omitted."""
    current_app.logger.info("WoL add_target requested", extra={"body_keys": list((request.get_json(silent=True) or {}).keys())})
    try:
        data = request.get_json(silent=True) or {}
        name = (data.get("name") or "").strip()
        mac = (data.get("mac") or "").strip()
        broadcast = (data.get("broadcast") or "").strip()
        ip = (data.get("ip") or "").strip()
        if not name or not mac:
            return jsonify({"success": False, "error": "name and mac required"}), 400
        if not broadcast and ip:
            broadcast = broadcast_from_ip(ip)
        if not broadcast:
            broadcast = "255.255.255.255"
        ensure_csv_with_header()
        append_target(name, mac, broadcast)
        current_app.logger.info("WoL target added", extra={"target_name": name, "mac": mac})
        return jsonify({"success": True, "name": name, "mac": mac, "broadcast": broadcast})
    except ValueError as e:
        current_app.logger.warning("WoL add_target validation failed", extra={"error": str(e)})
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        current_app.logger.exception("WoL add_target failed")
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/targets/<name>", methods=["DELETE"])
def delete_target(name):
    """Remove a WoL target by name from CSV."""
    current_app.logger.info("WoL delete_target requested", extra={"target_name": name})
    try:
        remove_target(name)
        return jsonify({"success": True, "removed": name})
    except FileNotFoundError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except ValueError as e:
        current_app.logger.warning(
            "WoL delete_target not found",
            extra={"target_name": name, "error": str(e)},
        )
        return jsonify({"success": False, "error": str(e)}), 404
    except Exception as e:
        current_app.logger.exception("WoL delete_target failed")
        return jsonify({"success": False, "error": str(e)}), 500
