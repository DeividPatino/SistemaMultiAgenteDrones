"""
sma_drones/grafos.py
Un grafo LangGraph por cada diagrama de secuencia (6 grafos).
Cada nodo es el turno de un agente; cada arista sigue el diagrama.
"""
import operator
from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, END

from sma_drones.mensajes import acl, nota


# ---------------------------------------------------------------------------
#  Estado compartido por todos los grafos
# ---------------------------------------------------------------------------

class Estado(TypedDict):
    trazas: Annotated[list, operator.add]
    # Datos que viajan entre nodos
    pedido: dict
    orden: dict
    drones_info: list
    variante: str
    distancia_km: float
    pin_cliente: str
    severidad: str


def estado_inicial(variante="ok", **extra):
    """Crea un estado inicial con valores por defecto."""
    base = {
        "trazas": [],
        "pedido": {"paquete": "Paquete-001", "ubicacion": "Bocagrande"},
        "orden": {"idOrden": "ORD-001", "estado": "en_cola", "ubicacion": "Bocagrande"},
        "drones_info": [
            {"id": "AgenteDron1", "bateria": 85, "velocidad": 22.5},
            {"id": "AgenteDron2", "bateria": 60, "velocidad": 15.0},
            {"id": "AgenteDron3", "bateria": 25, "velocidad": 20.0},
        ],
        "variante": variante,
        "distancia_km": 3.0,
        "pin_cliente": "4821",
        "severidad": "critica",
    }
    base.update(extra)
    return base


# ===================================================================
#  GRAFO 1 — Solicitud y validación del pedido (FIPA-Request)
# ===================================================================

def _g1_cliente_solicita(state):
    """AgenteCliente envía REQUEST a AgenteGestorPedidos."""
    pedido = state["pedido"]
    contenido = f"solicitarPedido({pedido.get('paquete','')}, {pedido.get('ubicacion','')})"
    return {"trazas": [
        acl("REQUEST", "AgenteCliente", "AgenteGestorPedidos",
            contenido, "FIPA-Request"),
    ]}


def _g1_gestor_valida(state):
    """AgenteGestorPedidos valida el pedido."""
    return {"trazas": [
        nota("AgenteGestorPedidos", "validarPedido()"),
    ]}


def _g1_decidir(state):
    """Rama: datos válidos o inválidos."""
    pedido = state["pedido"]
    if not pedido.get("ubicacion"):
        return "datos_invalidos"
    return "ok"


def _g1_ok(state):
    """Rama ok: AGREE + generarOrden + INFORM."""
    return {"trazas": [
        acl("AGREE", "AgenteGestorPedidos", "AgenteCliente", "pedido_aceptado"),
        nota("AgenteGestorPedidos", "generarOrden()"),
        acl("INFORM", "AgenteGestorPedidos", "AgenteCliente",
            "orden_creada(ORD-001, estado = en_cola)"),
    ]}


def _g1_datos_invalidos(state):
    """Rama else: REFUSE."""
    return {"trazas": [
        acl("REFUSE", "AgenteGestorPedidos", "AgenteCliente",
            "pedido_rechazado(datos_invalidos)"),
    ]}


def construir_grafo_1():
    g = StateGraph(Estado)
    g.add_node("cliente_solicita", _g1_cliente_solicita)
    g.add_node("gestor_valida", _g1_gestor_valida)
    g.add_node("g1_ok", _g1_ok)
    g.add_node("g1_datos_invalidos", _g1_datos_invalidos)
    g.set_entry_point("cliente_solicita")
    g.add_edge("cliente_solicita", "gestor_valida")
    g.add_conditional_edges("gestor_valida", _g1_decidir, {
        "ok": "g1_ok",
        "datos_invalidos": "g1_datos_invalidos",
    })
    g.add_edge("g1_ok", END)
    g.add_edge("g1_datos_invalidos", END)
    return g.compile()


# ===================================================================
#  GRAFO 2 — Envío de orden y consulta de condiciones (FIPA-Request/Query)
# ===================================================================

def _g2_gestor_despacha(state):
    """AgenteGestorPedidos envía REQUEST a AgenteCoordinadorFlota."""
    orden = state["orden"]
    return {"trazas": [
        acl("REQUEST", "AgenteGestorPedidos", "AgenteCoordinadorFlota",
            f"despacharOrden({orden['idOrden']}, {orden.get('ubicacion','Bocagrande')})"),
    ]}


def _g2_coordinador_acepta(state):
    """AgenteCoordinadorFlota responde AGREE, luego QUERY-IF al tráfico."""
    return {"trazas": [
        acl("AGREE", "AgenteCoordinadorFlota", "AgenteGestorPedidos",
            "orden_recibida"),
        acl("QUERY-IF", "AgenteCoordinadorFlota", "AgenteTraficoClima",
            "zona_habilitada(sector_destino)?", "FIPA-Query"),
    ]}


def _g2_trafico_verifica(state):
    """AgenteTraficoClima verifica zona."""
    return {"trazas": [
        nota("AgenteTraficoClima", "verificarZona()"),
    ]}


def _g2_decidir(state):
    """Rama: despejado o restringida."""
    ubicacion = state["orden"].get("ubicacion", "")
    if ubicacion in ("Base Naval", "Aeropuerto"):
        return "restringida"
    return "despejado"


def _g2_despejado(state):
    """Rama ok: INFORM zona habilitada."""
    return {"trazas": [
        acl("INFORM", "AgenteTraficoClima", "AgenteCoordinadorFlota",
            "zona_habilitada(sector_destino) = true, clima = favorable"),
        nota("AgenteCoordinadorFlota",
             "continúa con la asignación del dron (Diagrama 3)"),
    ]}


def _g2_restringida(state):
    """Rama else: INFORM zona restringida + INFORM orden en espera."""
    orden = state["orden"]
    return {"trazas": [
        acl("INFORM", "AgenteTraficoClima", "AgenteCoordinadorFlota",
            "zona_restringida(sector_destino) = true"),
        acl("INFORM", "AgenteCoordinadorFlota", "AgenteGestorPedidos",
            f"orden_en_espera({orden['idOrden']}, motivo)"),
    ]}


def construir_grafo_2():
    g = StateGraph(Estado)
    g.add_node("gestor_despacha", _g2_gestor_despacha)
    g.add_node("coordinador_acepta", _g2_coordinador_acepta)
    g.add_node("trafico_verifica", _g2_trafico_verifica)
    g.add_node("g2_despejado", _g2_despejado)
    g.add_node("g2_restringida", _g2_restringida)
    g.set_entry_point("gestor_despacha")
    g.add_edge("gestor_despacha", "coordinador_acepta")
    g.add_edge("coordinador_acepta", "trafico_verifica")
    g.add_conditional_edges("trafico_verifica", _g2_decidir, {
        "despejado": "g2_despejado",
        "restringida": "g2_restringida",
    })
    g.add_edge("g2_despejado", END)
    g.add_edge("g2_restringida", END)
    return g.compile()


# ===================================================================
#  GRAFO 3 — Asignación del dron (FIPA-Contract-Net)
# ===================================================================

def _calcular_eta(distancia_km, velocidad_kmh):
    """ETA en minutos."""
    return round((distancia_km / velocidad_kmh) * 60, 1)


def _g3_coordinador_cfp(state):
    """AgenteCoordinadorFlota envía CFP a los 3 drones (par)."""
    dist = state["distancia_km"]
    orden = state["orden"]
    msgs = [nota("AgenteCoordinadorFlota", "dronesDisponibles = [D1, D2, D3]")]
    for d in state["drones_info"]:
        msgs.append(acl("CFP", "AgenteCoordinadorFlota", d["id"],
                        f"entregar({orden['idOrden']}, {dist})",
                        "FIPA-Contract-Net"))
    return {"trazas": msgs}


def _g3_drones_responden(state):
    """Cada dron evalúa su batería y responde PROPOSE o REFUSE."""
    dist = state["distancia_km"]
    msgs = []
    for d in state["drones_info"]:
        msgs.append(nota(d["id"], "revisar nivelBateria"))
    for d in state["drones_info"]:
        eta = _calcular_eta(dist, d["velocidad"])
        bat_req = eta * 2 + 10
        if d["bateria"] >= bat_req:
            utilidad = (d["bateria"] - bat_req) - 2 * eta
            msgs.append(acl("PROPOSE", d["id"], "AgenteCoordinadorFlota",
                           f"bateria = {d['bateria']}%, ETA = {eta} min"))
        else:
            msgs.append(acl("REFUSE", d["id"], "AgenteCoordinadorFlota",
                           "bateria_insuficiente"))
    return {"trazas": msgs}


def _g3_coordinador_evalua(state):
    """Nota interna: optimizarEntregas()."""
    return {"trazas": [
        nota("AgenteCoordinadorFlota", "optimizarEntregas() (elige mayor utilidad)"),
    ]}


def _g3_decidir(state):
    """Rama: hay propuestas o ningún dron propone."""
    dist = state["distancia_km"]
    for d in state["drones_info"]:
        eta = _calcular_eta(dist, d["velocidad"])
        bat_req = eta * 2 + 10
        if d["bateria"] >= bat_req:
            return "normal"
    return "sin_propuestas"


def _g3_normal(state):
    """Rama ok: ACCEPT-PROPOSAL al mejor, REJECT al resto, INFORM ruta."""
    dist = state["distancia_km"]
    orden = state["orden"]
    propuestas = []
    for d in state["drones_info"]:
        eta = _calcular_eta(dist, d["velocidad"])
        bat_req = eta * 2 + 10
        if d["bateria"] >= bat_req:
            utilidad = (d["bateria"] - bat_req) - 2 * eta
            propuestas.append({"id": d["id"], "utilidad": utilidad, "eta": eta})
    propuestas.sort(key=lambda p: p["utilidad"], reverse=True)
    ganador = propuestas[0]["id"]
    rechazados = [p["id"] for p in propuestas[1:]]
    msgs = []
    msgs.append(acl("ACCEPT-PROPOSAL", "AgenteCoordinadorFlota", ganador,
                     f"asignarDron({orden['idOrden']}, ruta)"))
    for r in rechazados:
        msgs.append(acl("REJECT-PROPOSAL", "AgenteCoordinadorFlota", r,
                        "propuesta_no_seleccionada"))
    msgs.append(acl("INFORM", ganador, "AgenteCoordinadorFlota",
                     f"ruta_asignada({orden['idOrden']})"))
    return {"trazas": msgs}


def _g3_sin_propuestas(state):
    """Rama else: ningún dron propone, orden queda en cola."""
    return {"trazas": [
        nota("AgenteCoordinadorFlota",
             "la orden permanece en colaEntregas y se reintenta el CFP"),
    ]}


def construir_grafo_3():
    g = StateGraph(Estado)
    g.add_node("coordinador_cfp", _g3_coordinador_cfp)
    g.add_node("drones_responden", _g3_drones_responden)
    g.add_node("coordinador_evalua", _g3_coordinador_evalua)
    g.add_node("g3_normal", _g3_normal)
    g.add_node("g3_sin_propuestas", _g3_sin_propuestas)
    g.set_entry_point("coordinador_cfp")
    g.add_edge("coordinador_cfp", "drones_responden")
    g.add_edge("drones_responden", "coordinador_evalua")
    g.add_conditional_edges("coordinador_evalua", _g3_decidir, {
        "normal": "g3_normal",
        "sin_propuestas": "g3_sin_propuestas",
    })
    g.add_edge("g3_normal", END)
    g.add_edge("g3_sin_propuestas", END)
    return g.compile()


# ===================================================================
#  GRAFO 4 — Ejecución de la entrega y confirmación PIN (FIPA-Request)
# ===================================================================

def _g4_dron_notifica_eta(state):
    """AgenteDron informa ETA al cliente."""
    orden = state["orden"]
    dist = state["distancia_km"]
    # Dron 1 ya asignado
    d = state["drones_info"][0]
    eta = _calcular_eta(dist, d["velocidad"])
    return {"trazas": [
        acl("INFORM", "AgenteDron1", "AgenteCliente",
            f"hora_estimada_llegada({orden['idOrden']}, ETA = {eta} min)"),
    ]}


def _g4_dron_navega(state):
    """Loop: navegación del dron."""
    return {"trazas": [
        nota("AgenteDron1", "navegarRuta() / detectarObstaculo() / evitarColisiones()"),
    ]}


def _g4_dron_solicita_presencia(state):
    """AgenteDron solicita confirmación de presencia al cliente."""
    orden = state["orden"]
    return {"trazas": [
        acl("REQUEST", "AgenteDron1", "AgenteCliente",
            f"confirmarPresencia({orden['idOrden']})"),
    ]}


def _g4_decidir(state):
    """Rama: entrega o reprogramar."""
    return state.get("variante", "entrega")


def _g4_entrega(state):
    """Rama ok: PIN + validación + entrega + confirmación + informe."""
    orden = state["orden"]
    return {"trazas": [
        acl("INFORM", "AgenteCliente", "AgenteDron1", "confirmacionPIN(****)"),
        nota("AgenteDron1", "validarPIN()"),
        nota("AgenteDron1", "entregarPaquete()"),
        acl("INFORM", "AgenteDron1", "AgenteCliente",
            f"paquete_entregado({orden['idOrden']})"),
        acl("INFORM", "AgenteCliente", "AgenteDron1", "recepcion_confirmada"),
        acl("INFORM", "AgenteDron1", "AgenteCoordinadorFlota",
            f"entrega_exitosa({orden['idOrden']})"),
    ]}


def _g4_reprogramar(state):
    """Rama else: reprogramación."""
    orden = state["orden"]
    return {"trazas": [
        acl("REQUEST", "AgenteCliente", "AgenteDron1",
            f"reprogramarEntrega({orden['idOrden']}, nuevaHora)"),
        acl("AGREE", "AgenteDron1", "AgenteCliente",
            "reprogramacion_aceptada"),
        acl("INFORM", "AgenteDron1", "AgenteCoordinadorFlota",
            f"entrega_reprogramada({orden['idOrden']}, nuevaHora)"),
    ]}


def construir_grafo_4():
    g = StateGraph(Estado)
    g.add_node("dron_notifica_eta", _g4_dron_notifica_eta)
    g.add_node("dron_navega", _g4_dron_navega)
    g.add_node("dron_solicita_presencia", _g4_dron_solicita_presencia)
    g.add_node("g4_entrega", _g4_entrega)
    g.add_node("g4_reprogramar", _g4_reprogramar)
    g.set_entry_point("dron_notifica_eta")
    g.add_edge("dron_notifica_eta", "dron_navega")
    g.add_edge("dron_navega", "dron_solicita_presencia")
    g.add_conditional_edges("dron_solicita_presencia", _g4_decidir, {
        "entrega": "g4_entrega",
        "reprogramar": "g4_reprogramar",
    })
    g.add_edge("g4_entrega", END)
    g.add_edge("g4_reprogramar", END)
    return g.compile()


# ===================================================================
#  GRAFO 5 — Alertas de clima y zonas peligrosas (FIPA-Subscribe)
# ===================================================================

def _g5_suscripciones(state):
    """F y D se suscriben a alertas de T."""
    return {"trazas": [
        acl("SUBSCRIBE", "AgenteCoordinadorFlota", "AgenteTraficoClima",
            "notificar_alertas(sectores)", "FIPA-Subscribe"),
        acl("SUBSCRIBE", "AgenteDron1", "AgenteTraficoClima",
            "notificar_alertas(ruta_actual)"),
    ]}


def _g5_trafico_acepta(state):
    """T acepta suscripciones."""
    return {"trazas": [
        acl("AGREE", "AgenteTraficoClima", "AgenteCoordinadorFlota", ""),
        acl("AGREE", "AgenteTraficoClima", "AgenteDron1", ""),
    ]}


def _g5_trafico_alerta(state):
    """T detecta evento y emite alertas (par)."""
    return {"trazas": [
        nota("AgenteTraficoClima",
             "detectar ráfaga de viento / lluvia, emitirAlerta()"),
        acl("INFORM", "AgenteTraficoClima", "AgenteCoordinadorFlota",
            "alerta_clima(sector, severidad)"),
        acl("INFORM", "AgenteTraficoClima", "AgenteDron1",
            "alerta_clima(sector, severidad)"),
    ]}


def _g5_decidir(state):
    """Rama: severidad crítica o moderada."""
    return state.get("variante", "critica")


def _g5_critica(state):
    """Rama crítica: F cancela, D aterriza, D informa."""
    orden = state["orden"]
    return {"trazas": [
        acl("CANCEL", "AgenteCoordinadorFlota", "AgenteDron1",
            f"cancelar_entrega({orden['idOrden']})"),
        nota("AgenteDron1", "aterrizar / ir a cargar batería"),
        acl("INFORM", "AgenteDron1", "AgenteCoordinadorFlota",
            f"entrega_cancelada({orden['idOrden']})"),
    ]}


def _g5_moderada(state):
    """Rama moderada: D solicita nueva ruta, F acepta y envía."""
    orden = state["orden"]
    return {"trazas": [
        acl("REQUEST", "AgenteDron1", "AgenteCoordinadorFlota",
            f"solicitarNuevaRuta({orden['idOrden']}, evitar = sector)"),
        acl("AGREE", "AgenteCoordinadorFlota", "AgenteDron1", ""),
        acl("INFORM", "AgenteCoordinadorFlota", "AgenteDron1",
            f"nueva_ruta({orden['idOrden']}, ruta)"),
    ]}


def construir_grafo_5():
    g = StateGraph(Estado)
    g.add_node("g5_suscripciones", _g5_suscripciones)
    g.add_node("trafico_acepta", _g5_trafico_acepta)
    g.add_node("trafico_alerta", _g5_trafico_alerta)
    g.add_node("g5_critica", _g5_critica)
    g.add_node("g5_moderada", _g5_moderada)
    g.set_entry_point("g5_suscripciones")
    g.add_edge("g5_suscripciones", "trafico_acepta")
    g.add_edge("trafico_acepta", "trafico_alerta")
    g.add_conditional_edges("trafico_alerta", _g5_decidir, {
        "critica": "g5_critica",
        "moderada": "g5_moderada",
    })
    g.add_edge("g5_critica", END)
    g.add_edge("g5_moderada", END)
    return g.compile()


# ===================================================================
#  GRAFO 6 — Falla durante la entrega y reasignación (FIPA-Request)
# ===================================================================

def _g6_dron_falla(state):
    """AgenteDron detecta falla y notifica."""
    orden = state["orden"]
    return {"trazas": [
        nota("AgenteDron1", "detecta falla mecánica o cambio brusco de clima"),
        acl("FAILURE", "AgenteDron1", "AgenteCoordinadorFlota",
            f"entrega_abortada({orden['idOrden']}, causa)"),
    ]}


def _g6_coordinador_responde(state):
    """F ordena aterrizar, D acepta, D informa al cliente."""
    orden = state["orden"]
    return {"trazas": [
        acl("REQUEST", "AgenteCoordinadorFlota", "AgenteDron1",
            "aterrizar_y_retornar_a_base"),
        acl("AGREE", "AgenteDron1", "AgenteCoordinadorFlota", ""),
        acl("INFORM", "AgenteDron1", "AgenteCliente",
            f"entrega_demorada({orden['idOrden']})"),
    ]}


def _g6_coordinador_notifica_gestor(state):
    """F informa al gestor, gestor pone orden en cola, gestor pide despachar."""
    orden = state["orden"]
    return {"trazas": [
        acl("INFORM", "AgenteCoordinadorFlota", "AgenteGestorPedidos",
            f"orden_pendiente_reasignacion({orden['idOrden']})"),
        nota("AgenteGestorPedidos", "estadoOrden = en_cola"),
        acl("REQUEST", "AgenteGestorPedidos", "AgenteCoordinadorFlota",
            f"despacharOrden({orden['idOrden']})"),
    ]}


def _g6_coordinador_reasigna_nota(state):
    """Nota: reinicia la asignación de dron."""
    return {"trazas": [
        nota("AgenteCoordinadorFlota",
             "reinicia la asignación de dron (CFP, ver Diagrama 3)"),
    ]}


def _g6_decidir(state):
    """Rama: hay dron disponible o sin drones."""
    dist = state["distancia_km"]
    # Excluimos AgenteDron1 (el que falló)
    for d in state["drones_info"][1:]:
        eta = _calcular_eta(dist, d["velocidad"])
        bat_req = eta * 2 + 10
        if d["bateria"] >= bat_req:
            return "con_dron"
    return "sin_drones"


def _g6_con_dron(state):
    """Rama ok: dron reasignado."""
    orden = state["orden"]
    return {"trazas": [
        acl("INFORM", "AgenteCoordinadorFlota", "AgenteGestorPedidos",
            f"dron_reasignado({orden['idOrden']}, nuevaETA)"),
        acl("INFORM", "AgenteGestorPedidos", "AgenteCliente",
            f"nueva_hora_estimada({orden['idOrden']})"),
    ]}


def _g6_sin_drones(state):
    """Rama else: sin drones disponibles."""
    orden = state["orden"]
    return {"trazas": [
        acl("FAILURE", "AgenteCoordinadorFlota", "AgenteGestorPedidos",
            f"sin_drones_disponibles({orden['idOrden']})"),
        acl("INFORM", "AgenteGestorPedidos", "AgenteCliente",
            f"entrega_reprogramada({orden['idOrden']})"),
    ]}


def construir_grafo_6():
    g = StateGraph(Estado)
    g.add_node("dron_falla", _g6_dron_falla)
    g.add_node("coordinador_responde", _g6_coordinador_responde)
    g.add_node("coordinador_notifica_gestor", _g6_coordinador_notifica_gestor)
    g.add_node("coordinador_reasigna_nota", _g6_coordinador_reasigna_nota)
    g.add_node("g6_con_dron", _g6_con_dron)
    g.add_node("g6_sin_drones", _g6_sin_drones)
    g.set_entry_point("dron_falla")
    g.add_edge("dron_falla", "coordinador_responde")
    g.add_edge("coordinador_responde", "coordinador_notifica_gestor")
    g.add_edge("coordinador_notifica_gestor", "coordinador_reasigna_nota")
    g.add_conditional_edges("coordinador_reasigna_nota", _g6_decidir, {
        "con_dron": "g6_con_dron",
        "sin_drones": "g6_sin_drones",
    })
    g.add_edge("g6_con_dron", END)
    g.add_edge("g6_sin_drones", END)
    return g.compile()


# ===================================================================
#  Constructores y ejecución
# ===================================================================

CONSTRUCTORES = {
    1: construir_grafo_1,
    2: construir_grafo_2,
    3: construir_grafo_3,
    4: construir_grafo_4,
    5: construir_grafo_5,
    6: construir_grafo_6,
}

# Variante por defecto (camino principal) de cada grafo
VARIANTE_PRINCIPAL = {
    1: "ok",
    2: "despejado",
    3: "normal",
    4: "entrega",
    5: "critica",
    6: "con_dron",
}


def _estado_para_variante(n, variante):
    """Genera el estado inicial configurado según la variante pedida."""
    st = estado_inicial(variante)

    if n == 1 and variante == "datos_invalidos":
        st["pedido"] = {"paquete": "Paquete-001", "ubicacion": ""}
    elif n == 2 and variante == "restringida":
        st["orden"]["ubicacion"] = "Base Naval"
    elif n == 3 and variante == "sin_propuestas":
        st["drones_info"] = [
            {"id": "AgenteDron1", "bateria": 20, "velocidad": 22.5},
            {"id": "AgenteDron2", "bateria": 20, "velocidad": 15.0},
            {"id": "AgenteDron3", "bateria": 20, "velocidad": 20.0},
        ]
    elif n == 4 and variante == "reprogramar":
        st["variante"] = "reprogramar"
    elif n == 5 and variante == "moderada":
        st["variante"] = "moderada"
    elif n == 6 and variante == "sin_drones":
        st["drones_info"] = [
            {"id": "AgenteDron1", "bateria": 85, "velocidad": 22.5},
            {"id": "AgenteDron2", "bateria": 20, "velocidad": 15.0},
            {"id": "AgenteDron3", "bateria": 20, "velocidad": 20.0},
        ]
    return st


def ejecutar(n, variante=None):
    """Ejecuta el grafo n con la variante indicada. Devuelve la lista de trazas."""
    if variante is None:
        variante = VARIANTE_PRINCIPAL[n]
    grafo = CONSTRUCTORES[n]()
    st = _estado_para_variante(n, variante)
    resultado = grafo.invoke(st)
    return resultado["trazas"]


def flujo_completo():
    """Encadena grafos 1 -> 2 -> 3 -> 4 con el camino principal."""
    todas = []
    # Grafo 1: solicitud ok
    t1 = ejecutar(1, "ok")
    todas.extend(t1)
    # Grafo 2: despejado
    t2 = ejecutar(2, "despejado")
    todas.extend(t2)
    # Grafo 3: normal (con drones por defecto)
    t3 = ejecutar(3, "normal")
    todas.extend(t3)
    # Grafo 4: entrega exitosa
    t4 = ejecutar(4, "entrega")
    todas.extend(t4)
    return todas
