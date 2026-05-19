import logging
import os
import re
from datetime import datetime, timezone

import psycopg2.extras
from netmiko import ConnectHandler

from Database.db import get_db_connection
from dashboard_api import _SUMMARY_CACHE

logger = logging.getLogger(__name__)

SSH_TIMEOUT = int(os.getenv("NETMIKO_TIMEOUT", "12"))
SSH_AUTH_TIMEOUT = int(os.getenv("NETMIKO_AUTH_TIMEOUT", "10"))
SSH_BANNER_TIMEOUT = int(os.getenv("NETMIKO_BANNER_TIMEOUT", "8"))
INTERFACE_STATUS_VALUES = {
    "connected",
    "notconnect",
    "disabled",
    "err-disabled",
    "inactive",
    "monitoring",
    "sfpabsent",
    "xcvrabsent",
    "up",
    "down",
}


def _get_row_value(row, key, index=0):
    if hasattr(row, "get"):
        return row.get(key)
    return row[index]


def invalidate_dashboard_cache():
    _SUMMARY_CACHE["data"] = None
    _SUMMARY_CACHE["expires_at"] = 0


def ensure_switch_sync_schema(cur):
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS switchs (
            id_switch SERIAL PRIMARY KEY,
            reference_id VARCHAR(100),
            nom VARCHAR(100) UNIQUE NOT NULL,
            ip VARCHAR(50) UNIQUE NOT NULL,
            masque VARCHAR(50),
            username VARCHAR(100) NOT NULL,
            password TEXT NOT NULL,
            nb_ports INT DEFAULT 24,
            status VARCHAR(20) DEFAULT 'UNKNOWN'
        )
        """
    )

    cur.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'switchs'
        """
    )
    switch_columns = {_get_row_value(row, "column_name") for row in cur.fetchall()}

    if "status" not in switch_columns and "statut" in switch_columns:
        cur.execute("ALTER TABLE switchs RENAME COLUMN statut TO status")
        switch_columns.discard("statut")
        switch_columns.add("status")
    if "status" not in switch_columns:
        cur.execute("ALTER TABLE switchs ADD COLUMN status VARCHAR(20) DEFAULT 'UNKNOWN'")
    if "reference_id" not in switch_columns:
        cur.execute("ALTER TABLE switchs ADD COLUMN reference_id VARCHAR(100)")
    if "masque" not in switch_columns:
        cur.execute("ALTER TABLE switchs ADD COLUMN masque VARCHAR(50)")
    if "nb_ports" not in switch_columns:
        cur.execute("ALTER TABLE switchs ADD COLUMN nb_ports INT DEFAULT 24")
    if "last_sync_at" not in switch_columns:
        cur.execute("ALTER TABLE switchs ADD COLUMN last_sync_at TIMESTAMPTZ")
    if "last_sync_error" not in switch_columns:
        cur.execute("ALTER TABLE switchs ADD COLUMN last_sync_error TEXT")

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS utilisateurs_ssh (
            id_ssh_user SERIAL PRIMARY KEY,
            id_switch INT NOT NULL REFERENCES switchs(id_switch) ON DELETE CASCADE,
            username VARCHAR(100) NOT NULL,
            password BYTEA NOT NULL,
            privilege INT DEFAULT 15,
            UNIQUE(id_switch, username)
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS vlan (
            id_vlan INT PRIMARY KEY,
            nom VARCHAR(100),
            reseau VARCHAR(100),
            gateway VARCHAR(100),
            type VARCHAR(50) DEFAULT 'Data',
            ports TEXT,
            status VARCHAR(50) DEFAULT 'Active',
            switch_name VARCHAR(100),
            switch_ip VARCHAR(50)
        )
        """
    )

    cur.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'vlan'
        """
    )
    vlan_columns = {_get_row_value(row, "column_name") for row in cur.fetchall()}
    for column_name, column_type in {
        "nom": "VARCHAR(100)",
        "reseau": "VARCHAR(100)",
        "gateway": "VARCHAR(100)",
        "type": "VARCHAR(50) DEFAULT 'Data'",
        "ports": "TEXT",
        "status": "VARCHAR(50) DEFAULT 'Active'",
        "switch_name": "VARCHAR(100)",
        "switch_ip": "VARCHAR(50)",
    }.items():
        if column_name not in vlan_columns:
            cur.execute(f"ALTER TABLE vlan ADD COLUMN {column_name} {column_type}")

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS interface (
            id_interface SERIAL PRIMARY KEY,
            nom VARCHAR(100) NOT NULL,
            ip VARCHAR(100),
            vlan_id INT,
            id_switch INT REFERENCES switchs(id_switch) ON DELETE CASCADE,
            equipement_id INT,
            status VARCHAR(20) DEFAULT 'DOWN',
            mode VARCHAR(20) DEFAULT 'access',
            type VARCHAR(20) DEFAULT 'access',
            speed VARCHAR(50),
            allowed_vlans TEXT,
            port_security BOOLEAN DEFAULT FALSE,
            max_mac INT DEFAULT 1,
            violation_mode VARCHAR(50) DEFAULT 'shutdown',
            bpdu_guard BOOLEAN DEFAULT FALSE,
            static_mac VARCHAR(17),
            description TEXT,
            duplex VARCHAR(32)
        )
        """
    )

    cur.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'interface'
        """
    )
    interface_columns = {_get_row_value(row, "column_name") for row in cur.fetchall()}

    if "bpd_u_guard" in interface_columns and "bpdu_guard" not in interface_columns:
        cur.execute("ALTER TABLE interface RENAME COLUMN bpd_u_guard TO bpdu_guard")
        interface_columns.discard("bpd_u_guard")
        interface_columns.add("bpdu_guard")

    for column_name, column_type in {
        "ip": "VARCHAR(100)",
        "vlan_id": "INT",
        "id_switch": "INT REFERENCES switchs(id_switch) ON DELETE CASCADE",
        "equipement_id": "INT",
        "status": "VARCHAR(20) DEFAULT 'DOWN'",
        "mode": "VARCHAR(20) DEFAULT 'access'",
        "type": "VARCHAR(20) DEFAULT 'access'",
        "speed": "VARCHAR(50)",
        "allowed_vlans": "TEXT",
        "port_security": "BOOLEAN DEFAULT FALSE",
        "max_mac": "INT DEFAULT 1",
        "violation_mode": "VARCHAR(50) DEFAULT 'shutdown'",
        "bpdu_guard": "BOOLEAN DEFAULT FALSE",
        "static_mac": "VARCHAR(17)",
        "description": "TEXT",
        "duplex": "VARCHAR(32)",
    }.items():
        if column_name not in interface_columns:
            cur.execute(f"ALTER TABLE interface ADD COLUMN {column_name} {column_type}")

    cur.execute("CREATE INDEX IF NOT EXISTS idx_interface_switch_nom ON interface (id_switch, nom)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_interface_switch_vlan ON interface (id_switch, vlan_id)")


def _decode_secret(value):
    if value is None:
        return ""
    if isinstance(value, memoryview):
        value = value.tobytes()
    if isinstance(value, bytes):
        return value.decode(errors="ignore")
    return str(value)


def _normalize_port_name(value):
    raw = str(value or "").strip()
    if not raw:
        return ""

    compact = re.sub(r"\s+", "", raw).lower()
    match = re.match(r"^([a-z-]+)(.+)$", compact)
    prefix = match.group(1) if match else ""
    suffix = match.group(2) if match else raw
    replacements = {
        "gigabitethernet": "Gi",
        "gig": "Gi",
        "gi": "Gi",
        "g": "Gi",
        "tengigabitethernet": "Te",
        "tengig": "Te",
        "te": "Te",
        "t": "Te",
        "fastethernet": "Fa",
        "fast": "Fa",
        "fa": "Fa",
        "f": "Fa",
        "ethernet": "Eth",
        "eth": "Eth",
        "port-channel": "Po",
        "portchannel": "Po",
        "po": "Po",
    }
    if prefix in replacements:
        return replacements[prefix] + suffix
    return raw


def _interface_key(value):
    return _normalize_port_name(value).lower()


def _normalize_interface_status(value):
    normalized = str(value or "").strip().lower()
    if normalized in {"connected", "up"}:
        return "UP"
    return "DOWN"


def _normalize_vlan_value(value):
    raw = str(value or "").strip()
    if not raw:
        return None, None
    if raw.isdigit():
        return int(raw), None
    return None, raw


def _guess_interface_type(interface_name):
    name = str(interface_name or "").lower()
    if name.startswith(("te", "po", "fo")):
        return "uplink"
    return "access"


def _guess_speed(interface_name, reported_speed):
    speed = str(reported_speed or "").strip()
    if speed and speed not in {"auto", "a-auto", "-", "--"}:
        return speed
    return "10Gb" if _guess_interface_type(interface_name) == "uplink" else "1Gb"


def _split_status_columns(stripped):
    columns = re.split(r"\s{2,}", stripped)
    if len(columns) >= 6:
        return columns

    tokens = stripped.split()
    if len(tokens) < 6:
        return []

    status_index = next(
        (idx for idx, token in enumerate(tokens[1:], start=1) if token.lower() in INTERFACE_STATUS_VALUES),
        None,
    )
    if status_index is None or len(tokens) - status_index < 5:
        return []

    return [
        tokens[0],
        " ".join(tokens[1:status_index]),
        tokens[status_index],
        tokens[status_index + 1],
        tokens[status_index + 2],
        tokens[status_index + 3],
        " ".join(tokens[status_index + 4:]),
    ]


def parse_show_interfaces_status(output):
    interfaces = []
    seen = set()

    for raw_line in str(output or "").splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            continue
        lowered = stripped.lower()
        if lowered.startswith("port ") or lowered.startswith("name "):
            continue
        if set(stripped) <= {"-"}:
            continue
        if not re.match(r"^[A-Za-z]+\S*", stripped):
            continue

        columns = _split_status_columns(stripped)
        if len(columns) < 6:
            logger.debug("Ligne show interfaces status ignoree (format inconnu): %s", stripped)
            continue

        port = _normalize_port_name(columns[0])
        if not port:
            continue
        port_key = _interface_key(port)
        if port_key in seen:
            logger.debug("Interface dupliquee ignoree dans show interfaces status: %s", port)
            continue
        seen.add(port_key)

        # Cisco "show interfaces status" is more stable when parsed from the right:
        # Port | [optional description...] | Status | Vlan | Duplex | Speed | Type
        fixed_tail = columns[-5:]
        description_parts = columns[1:-5] if len(columns) > 6 else []
        description = " ".join(part.strip() for part in description_parts if part.strip())
        oper_status, vlan_value, duplex, speed, _media_type = fixed_tail

        vlan_id, allowed_vlans = _normalize_vlan_value(vlan_value)
        mode = "trunk" if vlan_id is None and vlan_value.lower() in {"trunk", "routed"} else "access"

        interfaces.append(
            {
                "nom": port,
                "description": description or None,
                "status": _normalize_interface_status(oper_status),
                "vlan_id": vlan_id,
                "mode": mode,
                "allowed_vlans": allowed_vlans,
                "duplex": None if duplex in {"auto", "a-auto", "-", "--"} else duplex,
                "speed": _guess_speed(port, speed),
                "type": _guess_interface_type(port),
            }
        )

    return interfaces


def parse_show_vlan_brief(output):
    vlans = []
    current = None

    for raw_line in str(output or "").splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            continue
        lowered = stripped.lower()
        if lowered.startswith("vlan ") or lowered.startswith("----"):
            continue

        match = re.match(r"^(?P<id>\d+)\s+(?P<name>\S+)\s+(?P<status>\S+)(?:\s+(?P<ports>.+))?$", stripped)
        if match:
            ports = match.group("ports") or ""
            current = {
                "id_vlan": int(match.group("id")),
                "nom": match.group("name"),
                "status": match.group("status"),
                "ports": ports.strip(),
            }
            vlans.append(current)
            continue

        if current and re.match(
            r"^(?:G|Gi|Gig|GigabitEthernet|F|Fa|FastEthernet|T|Te|TenGig|TenGigabitEthernet|Eth|Ethernet|Po|Port-channel)\S+",
            stripped,
            re.IGNORECASE,
        ):
            current["ports"] = ", ".join(filter(None, [current["ports"], stripped]))

    for vlan in vlans:
        ports = [
            _normalize_port_name(item.strip())
            for item in vlan["ports"].split(",")
            if item.strip()
        ]
        vlan["ports"] = ", ".join(dict.fromkeys(ports))
        vlan["status"] = str(vlan["status"] or "active").upper()

    return vlans


def apply_vlan_memberships_to_interfaces(interfaces, vlans):
    interface_by_key = {_interface_key(item["nom"]): item for item in interfaces}
    vlan_port_map = {}

    for vlan in vlans:
        vlan_id = vlan.get("id_vlan")
        if vlan_id is None:
            continue
        for port_name in [item.strip() for item in str(vlan.get("ports") or "").split(",") if item.strip()]:
            normalized_port = _normalize_port_name(port_name)
            port_key = _interface_key(normalized_port)
            vlan_port_map[port_key] = vlan_id
            if port_key in interface_by_key:
                interface = interface_by_key[port_key]
                interface["vlan_id"] = vlan_id
                if interface.get("mode") != "trunk":
                    interface["mode"] = "access"
                    interface["allowed_vlans"] = None
            else:
                interfaces.append(
                    {
                        "nom": normalized_port,
                        "description": None,
                        "status": "DOWN",
                        "vlan_id": vlan_id,
                        "mode": "access",
                        "allowed_vlans": None,
                        "duplex": None,
                        "speed": _guess_speed(normalized_port, None),
                        "type": _guess_interface_type(normalized_port),
                    }
                )
                interface_by_key[port_key] = interfaces[-1]

    logger.info(
        "Association VLAN/interface: %s port(s) references par show vlan brief, %s interface(s) consolidees",
        len(vlan_port_map),
        len(interfaces),
    )
    return interfaces


def _build_switch_device(switch_row):
    return {
        "device_type": "cisco_ios",
        "host": switch_row["ip"],
        "username": switch_row["username"],
        "password": _decode_secret(switch_row["password"]),
        "session_timeout": SSH_TIMEOUT,
        "auth_timeout": SSH_AUTH_TIMEOUT,
        "banner_timeout": SSH_BANNER_TIMEOUT,
        "fast_cli": False,
    }


def _load_switch_row(cur, switch_id):
    with cur.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as dict_cur:
        dict_cur.execute(
            """
            SELECT id_switch, nom, ip, username, password, nb_ports
            FROM switchs
            WHERE id_switch = %s
            """,
            (switch_id,),
        )
        return dict_cur.fetchone()


def _update_switch_status(cur, switch_id, status, error_message=None):
    cur.execute(
        """
        UPDATE switchs
        SET status = %s,
            last_sync_at = %s,
            last_sync_error = %s
        WHERE id_switch = %s
        """,
        (
            status,
            datetime.now(timezone.utc),
            (str(error_message)[:1000] if error_message else None),
            switch_id,
        ),
    )


def _refresh_vlan_ports(cur, switch_row, vlan_ids):
    for vlan_id in {value for value in vlan_ids if value is not None}:
        cur.execute(
            """
            SELECT COALESCE(STRING_AGG(nom, ', ' ORDER BY nom), '')
            FROM interface
            WHERE id_switch = %s
              AND vlan_id = %s
              AND COALESCE(mode, 'access') = 'access'
            """,
            (switch_row["id_switch"], vlan_id),
        )
        ports_value = cur.fetchone()[0] or ""
        cur.execute(
            """
            UPDATE vlan
            SET ports = %s,
                switch_name = %s,
                switch_ip = %s
            WHERE id_vlan = %s
            """,
            (ports_value, switch_row["nom"], switch_row["ip"], vlan_id),
        )


def complete_vlans_from_interfaces(vlans, interfaces):
    vlan_by_id = {item.get("id_vlan"): item for item in vlans}
    missing_ports_by_vlan = {}

    for interface in interfaces:
        vlan_id = interface.get("vlan_id")
        if vlan_id is None or vlan_id in vlan_by_id:
            continue
        missing_ports_by_vlan.setdefault(vlan_id, []).append(interface.get("nom") or "")

    added = 0
    for vlan_id, ports in sorted(missing_ports_by_vlan.items()):
        vlans.append(
            {
                "id_vlan": vlan_id,
                "nom": f"VLAN{vlan_id}",
                "status": "ACTIVE",
                "ports": ", ".join(port for port in ports if port),
            }
        )
        added += 1
    if added:
        logger.info("%s VLAN(s) ajoutes depuis show interfaces status car absents de show vlan brief", added)
    return vlans


def _upsert_interfaces(cur, switch_row, interfaces):
    updated_count = 0
    touched_vlans = set()
    received_keys = set()
    existing_by_key = {}
    duplicate_existing = 0

    cur.execute(
        """
        SELECT id_interface, nom, vlan_id
        FROM interface
        WHERE id_switch = %s
        ORDER BY id_interface ASC
        """,
        (switch_row["id_switch"],),
    )
    for interface_id, interface_name, vlan_id in cur.fetchall():
        key = _interface_key(interface_name)
        if key in existing_by_key:
            duplicate_existing += 1
            logger.warning(
                "Doublon interface conserve sans suppression: switch=%s nom=%s id_interface=%s",
                switch_row["id_switch"],
                interface_name,
                interface_id,
            )
            continue
        existing_by_key[key] = {
            "id_interface": interface_id,
            "nom": interface_name,
            "vlan_id": vlan_id,
        }

    for item in interfaces:
        touched_vlans.add(item.get("vlan_id"))
        key = _interface_key(item["nom"])
        received_keys.add(key)
        existing = existing_by_key.get(key)

        if existing:
            touched_vlans.add(existing.get("vlan_id"))
            cur.execute(
                """
                UPDATE interface
                SET nom = %s,
                    status = %s,
                    vlan_id = %s,
                    mode = %s,
                    allowed_vlans = %s,
                    duplex = %s,
                    speed = %s,
                    description = %s,
                    type = %s
                WHERE id_interface = %s
                """,
                (
                    item["nom"],
                    item["status"],
                    item["vlan_id"],
                    item["mode"],
                    item["allowed_vlans"],
                    item["duplex"],
                    item["speed"],
                    item["description"],
                    item["type"],
                    existing["id_interface"],
                ),
            )
            logger.debug(
                "Interface maj: switch=%s nom=%s vlan=%s status=%s mode=%s",
                switch_row["id_switch"],
                item["nom"],
                item["vlan_id"],
                item["status"],
                item["mode"],
            )
        else:
            cur.execute(
                """
                INSERT INTO interface (
                    nom, ip, vlan_id, id_switch, equipement_id, status, mode, type,
                    speed, allowed_vlans, port_security, max_mac, violation_mode,
                    bpdu_guard, description, duplex
                )
                VALUES (%s, NULL, %s, %s, NULL, %s, %s, %s, %s, %s, FALSE, 1, 'shutdown', FALSE, %s, %s)
                """,
                (
                    item["nom"],
                    item["vlan_id"],
                    switch_row["id_switch"],
                    item["status"],
                    item["mode"],
                    item["type"],
                    item["speed"],
                    item["allowed_vlans"],
                    item["description"],
                    item["duplex"],
                ),
            )
            logger.debug(
                "Interface creee: switch=%s nom=%s vlan=%s status=%s mode=%s",
                switch_row["id_switch"],
                item["nom"],
                item["vlan_id"],
                item["status"],
                item["mode"],
            )
        updated_count += 1

    stale_count = len(set(existing_by_key) - received_keys)
    if stale_count:
        logger.info(
            "%s interface(s) existantes non vues pendant le scan; conservees en base pour eviter une suppression incorrecte",
            stale_count,
        )
    if duplicate_existing:
        logger.warning("%s doublon(s) d'interfaces detectes et conserves", duplicate_existing)

    _refresh_vlan_ports(cur, switch_row, touched_vlans)
    return updated_count, stale_count


def _upsert_vlans(cur, switch_row, vlans):
    updated_count = 0
    received_vlan_ids = set()

    for item in vlans:
        received_vlan_ids.add(item["id_vlan"])
        cur.execute(
            """
            SELECT COALESCE(STRING_AGG(nom, ', ' ORDER BY nom), '')
            FROM interface
            WHERE id_switch = %s
              AND vlan_id = %s
              AND COALESCE(mode, 'access') = 'access'
            """,
            (switch_row["id_switch"], item["id_vlan"]),
        )
        interface_ports = cur.fetchone()[0] or ""
        ports_value = interface_ports or item.get("ports") or ""

        cur.execute(
            """
            SELECT id_vlan
            FROM vlan
            WHERE id_vlan = %s
            LIMIT 1
            """,
            (item["id_vlan"],),
        )
        existing = cur.fetchone()

        if existing:
            cur.execute(
                """
                UPDATE vlan
                SET nom = %s,
                    status = %s,
                    ports = %s,
                    switch_name = %s,
                    switch_ip = %s
                WHERE id_vlan = %s
                """,
                (
                    item["nom"],
                    item["status"],
                    ports_value,
                    switch_row["nom"],
                    switch_row["ip"],
                    item["id_vlan"],
                ),
            )
            logger.debug(
                "VLAN maj: switch=%s vlan=%s nom=%s ports=%s",
                switch_row["id_switch"],
                item["id_vlan"],
                item["nom"],
                ports_value,
            )
        else:
            cur.execute(
                """
                INSERT INTO vlan (id_vlan, nom, reseau, gateway, type, ports, status, switch_name, switch_ip)
                VALUES (%s, %s, NULL, NULL, 'Data', %s, %s, %s, %s)
                """,
                (
                    item["id_vlan"],
                    item["nom"],
                    ports_value,
                    item["status"],
                    switch_row["nom"],
                    switch_row["ip"],
                ),
            )
            logger.debug(
                "VLAN cree: switch=%s vlan=%s nom=%s ports=%s",
                switch_row["id_switch"],
                item["id_vlan"],
                item["nom"],
                ports_value,
            )
        updated_count += 1

    cur.execute(
        """
        SELECT id_vlan
        FROM vlan
        WHERE switch_ip = %s
          AND COALESCE(TRIM(switch_ip), '') <> ''
        """,
        (switch_row["ip"],),
    )
    stale_count = len({row[0] for row in cur.fetchall()} - received_vlan_ids)
    if stale_count:
        logger.info(
            "%s VLAN(s) existants non vus pendant le scan; conserves en base pour eviter une suppression incorrecte",
            stale_count,
        )

    return updated_count, stale_count


def sync_switch_state(switch_id):
    conn = get_db_connection()
    net_connect = None

    try:
        cur = conn.cursor()
        ensure_switch_sync_schema(cur)
        switch_row = _load_switch_row(cur, switch_id)
        if not switch_row:
            conn.rollback()
            return {"success": False, "error": "Switch introuvable", "status_code": 404}

        device = _build_switch_device(
            {
                "ip": switch_row["ip"],
                "username": switch_row["username"],
                "password": switch_row["password"],
            }
        )

        try:
            logger.info("Debut test/synchronisation switch id=%s ip=%s", switch_id, switch_row["ip"])
            net_connect = ConnectHandler(**device)
            try:
                prompt = net_connect.find_prompt()
                logger.info("Connexion SSH OK switch id=%s prompt=%s", switch_id, prompt)
                net_connect.send_command("terminal length 0", read_timeout=10)
            except Exception:
                logger.debug("Preparation session SSH ignoree pour switch %s", switch_id, exc_info=True)
            interface_output = net_connect.send_command("show interfaces status", read_timeout=20)
            vlan_output = net_connect.send_command("show vlan brief", read_timeout=20)
        except Exception as exc:
            logger.warning("Synchronisation SSH impossible pour switch %s: %s", switch_id, exc)
            _update_switch_status(cur, switch_id, "DOWN", str(exc))
            conn.commit()
            invalidate_dashboard_cache()
            return {
                "success": False,
                "switch_status": "offline",
                "status": "offline",
                "error": str(exc),
                "interfaces_updated": 0,
                "interfaces_deleted": 0,
                "vlans_updated": 0,
                "vlans_deleted": 0,
                "status_code": 200,
            }

        parsed_interfaces = parse_show_interfaces_status(interface_output)
        parsed_vlans = parse_show_vlan_brief(vlan_output)
        logger.info(
            "Parsing switch %s: %s interface(s), %s VLAN(s)",
            switch_id,
            len(parsed_interfaces),
            len(parsed_vlans),
        )
        parsed_vlans = complete_vlans_from_interfaces(parsed_vlans, parsed_interfaces)
        parsed_interfaces = apply_vlan_memberships_to_interfaces(parsed_interfaces, parsed_vlans)

        switch_info = {
            "id_switch": switch_row["id_switch"],
            "nom": switch_row["nom"],
            "ip": switch_row["ip"],
            "nb_ports": switch_row["nb_ports"],
        }

        interfaces_updated, interfaces_stale = _upsert_interfaces(cur, switch_info, parsed_interfaces)
        vlans_updated, vlans_stale = _upsert_vlans(cur, switch_info, parsed_vlans)
        _update_switch_status(cur, switch_id, "UP", None)
        conn.commit()
        invalidate_dashboard_cache()
        logger.info(
            "Synchronisation OK switch %s: interfaces_updated=%s interfaces_stale=%s vlans_updated=%s vlans_stale=%s",
            switch_id,
            interfaces_updated,
            interfaces_stale,
            vlans_updated,
            vlans_stale,
        )

        return {
            "success": True,
            "switch_status": "online",
            "status": "online",
            "interfaces_updated": interfaces_updated,
            "interfaces_deleted": 0,
            "interfaces_stale": interfaces_stale,
            "vlans_updated": vlans_updated,
            "vlans_deleted": 0,
            "vlans_stale": vlans_stale,
            "interfaces_count": len(parsed_interfaces),
            "vlans_count": len(parsed_vlans),
        }
    except Exception as exc:
        conn.rollback()
        logger.exception("Erreur de synchronisation pour switch %s", switch_id)
        return {
            "success": False,
            "switch_status": "offline",
            "status": "offline",
            "error": str(exc),
            "interfaces_updated": 0,
            "interfaces_deleted": 0,
            "vlans_updated": 0,
            "vlans_deleted": 0,
            "status_code": 500,
        }
    finally:
        if net_connect is not None:
            try:
                net_connect.disconnect()
            except Exception:
                logger.debug("Fermeture Netmiko ignorée", exc_info=True)
        conn.close()
