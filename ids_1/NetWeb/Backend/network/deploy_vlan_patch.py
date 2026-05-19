# ─────────────────────────────────────────────────────────────────────────────
# AJOUTEZ ces fonctions dans votre fichier network/deploy_vlan.py
# (à côté de votre fonction run_deploy existante)
#
# CHANGEMENTS vs version précédente :
#   - run_deploy_with_network() : nouveau — déploie le VLAN ET configure le SVI
#     avec l'adresse IP + masque réseau. Valide l'appartenance à 10.10.0.0/16.
#   - run_delete()              : factorisé — utilise _load_device_from_hosts()
#     pour éviter la duplication du parsing hosts.yaml.
#   - _load_device_from_hosts() : helper privé partagé entre les deux fonctions.
# ─────────────────────────────────────────────────────────────────────────────

# Réseau global de référence — tous les VLANs doivent en être des sous-réseaux.
GLOBAL_NETWORK = "10.10.0.0/16"


def _load_device_from_hosts(base_dir):
    """Charge les credentials SSH depuis hosts.yaml (même logique que run_deploy)."""
    import os, yaml

    hosts_path = os.path.join(base_dir, "hosts.yaml")
    if not os.path.exists(hosts_path):
        raise FileNotFoundError(f"hosts.yaml introuvable : {hosts_path}")

    with open(hosts_path, "r") as f:
        hosts_data = yaml.safe_load(f)

    if isinstance(hosts_data, list):
        host_cfg = hosts_data[0]
    elif isinstance(hosts_data, dict):
        first_key = next(iter(hosts_data))
        host_cfg = hosts_data[first_key] if isinstance(hosts_data[first_key], dict) else hosts_data
    else:
        raise ValueError("Format hosts.yaml invalide")

    device = {
        "device_type": host_cfg.get("device_type", "cisco_ios"),
        "host":        host_cfg.get("hostname") or host_cfg.get("host"),
        "username":    host_cfg.get("username"),
        "password":    host_cfg.get("password"),
        "secret":      host_cfg.get("secret", ""),
        "port":        int(host_cfg.get("port", 22)),
    }

    if not device["host"] or not device["username"]:
        raise ValueError("Credentials SSH manquants dans hosts.yaml")

    return device


def run_deploy_with_network(id_vlan: int, nom_vlan: str,
                             gateway: str = "", subnet_mask: str = "",
                             reseau_cidr: str = "") -> dict:
    """
    Déploie un VLAN sur le switch via SSH avec configuration réseau complète.

    Valide que le sous-réseau appartient à 10.10.0.0/16 avant d'envoyer les
    commandes. Configure le SVI (interface vlan) avec l'adresse IP de passerelle
    et le masque réseau si fournis.

    Commandes envoyées :
        conf t
        vlan <id>
          name <nom>
        !
        interface vlan <id>
          description SVI-VLAN-<id>
          ip address <gateway> <subnet_mask>   <- si gateway + mask fournis
          no shutdown
        !
        end
        write memory

    Paramètres
    ----------
    id_vlan      : numéro du VLAN (1-4094)
    nom_vlan     : nom du VLAN
    gateway      : adresse IP de la passerelle SVI (optionnel)
    subnet_mask  : masque réseau au format décimal pointé, ex: 255.255.255.0
    reseau_cidr  : adresse réseau CIDR, ex: 10.10.1.0/24 (utilisé pour
                   dériver le masque si subnet_mask absent)
    """
    import os, ipaddress
    from netmiko import ConnectHandler

    base_dir = os.path.dirname(os.path.abspath(__file__))

    # ── Dériver subnet_mask depuis reseau_cidr si nécessaire ─────────────────
    if not subnet_mask and reseau_cidr and "/" in reseau_cidr:
        try:
            net = ipaddress.ip_network(reseau_cidr, strict=False)
            subnet_mask = str(net.netmask)
        except ValueError:
            pass

    # ── Valider appartenance au réseau global 10.10.0.0/16 ───────────────────
    if reseau_cidr:
        try:
            vlan_net = ipaddress.ip_network(reseau_cidr, strict=False)
            global_net = ipaddress.ip_network(GLOBAL_NETWORK, strict=False)
            if not vlan_net.subnet_of(global_net):
                return {
                    "success": False,
                    "error": (
                        f"Le sous-réseau {reseau_cidr} n'appartient pas au réseau "
                        f"global {GLOBAL_NETWORK}. Déploiement annulé."
                    ),
                }
        except ValueError as e:
            return {"success": False, "error": f"Réseau VLAN invalide : {e}"}

    # ── Valider cohérence gateway / sous-réseau VLAN ──────────────────────────
    if gateway and reseau_cidr:
        try:
            gw_addr = ipaddress.ip_address(gateway)
            vlan_net = ipaddress.ip_network(reseau_cidr, strict=False)
            if gw_addr not in vlan_net:
                return {
                    "success": False,
                    "error": (
                        f"La passerelle {gateway} n'appartient pas au sous-réseau "
                        f"VLAN {reseau_cidr}. Déploiement annulé."
                    ),
                }
        except ValueError as e:
            return {"success": False, "error": f"Adresse gateway invalide : {e}"}

    # ── Charger credentials SSH ───────────────────────────────────────────────
    try:
        device = _load_device_from_hosts(base_dir)
    except Exception as e:
        return {"success": False, "error": str(e)}

    # ── Construire les commandes Cisco IOS ────────────────────────────────────
    commands = [
        f"vlan {id_vlan}",
        f" name {nom_vlan}",
        "!",
        f"interface vlan {id_vlan}",
        f" description SVI-VLAN-{id_vlan}",
    ]

    if gateway and subnet_mask:
        commands.append(f" ip address {gateway} {subnet_mask}")
    elif gateway:
        # Fallback : masque /16 si le masque n'a pas pu etre derive
        commands.append(f" ip address {gateway} 255.255.0.0")

    commands.append(" no shutdown")
    commands.append("!")

    try:
        net_connect = ConnectHandler(**device)
        if device["secret"]:
            net_connect.enable()

        output = net_connect.send_config_set(commands)
        net_connect.send_command("end")
        net_connect.send_command("write memory")
        net_connect.disconnect()

        svi_msg = f"avec SVI {gateway}/{subnet_mask}" if gateway else "sans SVI configure"
        return {
            "success":  True,
            "message":  f"VLAN {id_vlan} '{nom_vlan}' deploye sur le switch {svi_msg}.",
            "commands": ["conf t"] + commands + ["end", "write memory"],
            "output":   output,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def run_delete(id_vlan: int) -> dict:
    """
    Supprime un VLAN du switch via SSH.
    Lit les credentials depuis hosts.yaml (meme logique que run_deploy).

    Commandes envoyees :
        conf t
        no vlan <id>
        no interface vlan <id>    (supprime le SVI / gateway)
        end
        write memory
    """
    import os
    from netmiko import ConnectHandler

    base_dir = os.path.dirname(os.path.abspath(__file__))

    try:
        device = _load_device_from_hosts(base_dir)
    except Exception as e:
        return {"success": False, "error": str(e)}

    # ── Commandes de suppression ───────────────────────────────────────────────
    commands = [
        f"no vlan {id_vlan}",
        f"no interface vlan {id_vlan}",
    ]

    try:
        net_connect = ConnectHandler(**device)
        if device["secret"]:
            net_connect.enable()

        output = net_connect.send_config_set(commands)
        net_connect.send_command("end")
        net_connect.send_command("write memory")
        net_connect.disconnect()

        return {
            "success":  True,
            "message":  f"VLAN {id_vlan} supprime du switch.",
            "commands": ["conf t"] + commands + ["end", "write memory"],
            "output":   output,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}