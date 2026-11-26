"""
sma_drones/mensajes.py
Funciones para crear y formatear mensajes FIPA ACL y notas internas.
"""


def acl(performativa, emisor, receptor, contenido, protocolo=""):
    """Crea un mensaje ACL como diccionario."""
    msg = {
        "tipo": "acl",
        "performativa": performativa,
        "emisor": emisor,
        "receptor": receptor,
        "contenido": contenido,
    }
    if protocolo:
        msg["protocolo"] = protocolo
    return msg


def nota(agente, texto):
    """Crea una nota interna (acción del agente, no es mensaje ACL)."""
    return {
        "tipo": "nota",
        "agente": agente,
        "texto": texto,
    }


def firma(msg):
    """Devuelve (performativa, emisor, receptor) para comparaciones en tests."""
    return (msg["performativa"], msg["emisor"], msg["receptor"])


def formatear(msg, numero=None):
    """Formatea un mensaje o nota para impresión en consola."""
    prefijo = f"  {numero:>2}. " if numero else "      "
    if msg["tipo"] == "nota":
        return f"{prefijo}· {msg['agente']}: {msg['texto']}"
    linea = f"{prefijo}«ACL:{msg['performativa']}» {msg['emisor']} -> {msg['receptor']}"
    linea += f"  :content {msg['contenido']}"
    if msg.get("protocolo"):
        linea += f"  :protocol {msg['protocolo']}"
    return linea


def a_sexpr(msg):
    """Formatea un mensaje ACL en s-expression FIPA."""
    if msg["tipo"] == "nota":
        return f"(nota :agent {msg['agente']} :text \"{msg['texto']}\")"
    partes = [
        f"(ACL-MESSAGE",
        f"  :performative {msg['performativa']}",
        f"  :sender {msg['emisor']}",
        f"  :receiver {msg['receptor']}",
        f"  :content \"{msg['contenido']}\"",
    ]
    if msg.get("protocolo"):
        partes.append(f"  :protocol {msg['protocolo']}")
    partes.append(")")
    return "\n".join(partes)
