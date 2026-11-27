"""
sma_drones/grafos.py
Un grafo LangGraph por cada diagrama de secuencia (6 grafos).
Cada nodo es el turno de un agente; cada arista sigue el diagrama.
"""
import operator
from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, END

from sma_drones.agentes import (
    AgenteDron, Alerta, EstadoDron, EstadoPedido, Pedido, SistemaEntregaDrones,
)
from sma_drones.mensajes import acl, nota


# ---------------------------------------------------------------------------
#  Estado compartido por todos los grafos
# ---------------------------------------------------------------------------

class Estado(TypedDict):
    trazas: Annotated[list, operator.add]
    # Datos que viajan entre nodos
    sistema: SistemaEntregaDrones
    pedido: dict
    orden: Pedido | None
    condiciones_vuelo: dict
    zona_restringida: bool
    clima_favorable: bool
    drones_info: list
    pedido_valido: bool
    dron_seleccionado: AgenteDron | None
    propuestas: list
    propuesta_seleccionada: dict | None
    variante: str
    distancia_km: float
    pin_cliente: str
    pin_valido: bool
    severidad: str
    alerta_clima: Alerta | None
    suscriptores_alertas: list[str]
    dron_fallado: AgenteDron | None


def estado_inicial(variante="ok", sistema=None, **extra):
    """Crea un estado inicial con valores por defecto."""
    sistema = sistema if sistema is not None else SistemaEntregaDrones()
    base = {
        "trazas": [],
        "sistema": sistema,
        "pedido": {"paquete": "Paquete-001", "ubicacion": "Bocagrande"},
        "orden": None,
        "condiciones_vuelo": {},
        "zona_restringida": False,
        "clima_favorable": True,
        "drones_info": sistema.drones,
        "pedido_valido": False,
        "dron_seleccionado": None,
        "propuestas": [],
        "propuesta_seleccionada": None,
        "variante": variante,
        "distancia_km": 3.0,
        "pin_cliente": "4821",
        "pin_valido": False,
        "severidad": "critica",
        "alerta_clima": None,
        "suscriptores_alertas": [],
        "dron_fallado": None,
    }
    base.update(extra)
    return base


# ===================================================================
#  GRAFO 1 — Solicitud y validación del pedido (FIPA-Request)
# ===================================================================

def _g1_cliente_solicita(state):
    """AgenteCliente envía REQUEST a AgenteGestorPedidos."""
    pedido = state["sistema"].cliente.solicitarPedido(**state["pedido"])
    contenido = f"solicitarPedido({pedido.get('paquete','')}, {pedido.get('ubicacion','')})"
    return {
        "pedido": pedido,
        "trazas": [
            acl("REQUEST", "AgenteCliente", "AgenteGestorPedidos",
                contenido, "FIPA-Request"),
        ],
    }


def _g1_gestor_valida(state):
    """AgenteGestorPedidos valida el pedido."""
    return {
        "pedido_valido": state["sistema"].gestor.validarPedido(state["pedido"]),
        "trazas": [
            nota("AgenteGestorPedidos", "validarPedido()"),
        ],
    }


def _g1_decidir(state):
    """Rama: datos válidos o inválidos."""
    return "ok" if state["pedido_valido"] else "datos_invalidos"


def _g1_ok(state):
    """Rama ok: AGREE + generarOrden + INFORM."""
    orden = state["sistema"].gestor.generarOrden(state["pedido"])
    return {
        "orden": orden,
        "trazas": [
            acl("AGREE", "AgenteGestorPedidos", "AgenteCliente", "pedido_aceptado"),
            nota("AgenteGestorPedidos", "generarOrden()"),
            acl("INFORM", "AgenteGestorPedidos", "AgenteCliente",
                f"orden_creada({orden.id_pedido}, estado = {orden.estado})"),
        ],
    }


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
            f"despacharOrden({orden.id_pedido}, {orden.ubicacion})"),
    ]}


def _g2_coordinador_acepta(state):
    """AgenteCoordinadorFlota responde AGREE, luego QUERY-IF al tráfico."""
    condiciones = state["sistema"].coordinador.consultarCondiciones(
        state["orden"].ubicacion
    )
    return {
        "condiciones_vuelo": condiciones,
        "trazas": [
            acl("AGREE", "AgenteCoordinadorFlota", "AgenteGestorPedidos",
                "orden_recibida"),
            acl("QUERY-IF", "AgenteCoordinadorFlota", "AgenteTraficoClima",
                "zona_habilitada(sector_destino)?", "FIPA-Query"),
        ],
    }


def _g2_trafico_verifica(state):
    """AgenteTraficoClima verifica zona."""
    sector = state["condiciones_vuelo"]["sector"]
    return {
        "zona_restringida": state["sistema"].trafico.verificarZona(sector),
        "clima_favorable":
            state["sistema"].entorno.condicionesClimaticas == "favorable",
        "trazas": [
            nota("AgenteTraficoClima", "verificarZona()"),
        ],
    }


def _g2_decidir(state):
    """Rama: despejado o restringida."""
    if state["zona_restringida"] or not state["clima_favorable"]:
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
    motivo = (
        "zona_restringida(sector_destino) = true"
        if state["zona_restringida"]
        else "clima_peligroso(sector_destino) = true"
    )
    return {"trazas": [
        acl("INFORM", "AgenteTraficoClima", "AgenteCoordinadorFlota",
            motivo),
        acl("INFORM", "AgenteCoordinadorFlota", "AgenteGestorPedidos",
            f"orden_en_espera({orden.id_pedido}, motivo)"),
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
    """AgenteCoordinadorFlota envía CFP a los drones disponibles."""
    dist = state["distancia_km"]
    orden = state["orden"]
    coordinador = state["sistema"].coordinador
    disponibles = [
        dron for dron in coordinador.dronesDisponibles
        if dron.estado == EstadoDron.LIBRE
    ]
    if not any(pedido is orden for pedido in coordinador.colaEntregas):
        coordinador.colaEntregas.append(orden)

    nombres = [
        dron.idDron.replace("AgenteDron", "D") for dron in disponibles
    ]
    msgs = [
        nota("AgenteCoordinadorFlota",
             f"dronesDisponibles = [{', '.join(nombres)}]")
    ]
    for d in disponibles:
        msgs.append(acl("CFP", "AgenteCoordinadorFlota", d.idDron,
                        f"entregar({orden.id_pedido}, {dist})",
                        "FIPA-Contract-Net"))
    return {"drones_info": disponibles, "trazas": msgs}


def _g3_drones_responden(state):
    """Cada dron evalúa su batería y responde PROPOSE o REFUSE."""
    dist = state["distancia_km"]
    propuestas = []
    msgs = []
    for d in state["drones_info"]:
        msgs.append(nota(d.idDron, "revisar nivelBateria"))
    for d in state["drones_info"]:
        evaluacion = d.evaluarPropuesta(dist)
        if evaluacion["puede"]:
            propuestas.append({"dron": d, **evaluacion})
            msgs.append(acl(
                "PROPOSE", d.idDron, "AgenteCoordinadorFlota",
                f"bateria = {d.nivelBateria}%, "
                f"ETA = {evaluacion['eta_min']} min",
            ))
        else:
            msgs.append(acl(
                "REFUSE", d.idDron, "AgenteCoordinadorFlota",
                "bateria_insuficiente",
            ))
    return {"propuestas": propuestas, "trazas": msgs}


def _g3_coordinador_evalua(state):
    """El coordinador elige la propuesta de mayor utilidad."""
    mejor = state["sistema"].coordinador.optimizarEntregas(
        state["propuestas"]
    )
    return {
        "propuesta_seleccionada": mejor,
        "dron_seleccionado": mejor["dron"] if mejor else None,
        "trazas": [
            nota("AgenteCoordinadorFlota",
                 "optimizarEntregas() (elige mayor utilidad)"),
        ],
    }


def _g3_decidir(state):
    """Rama: hay propuestas o ningún dron propone."""
    return (
        "normal"
        if state["propuesta_seleccionada"] is not None
        else "sin_propuestas"
    )


def _g3_normal(state):
    """Asigna la propuesta elegida y rechaza las restantes."""
    orden = state["orden"]
    propuestas = state["propuestas"]
    ganador = state["propuesta_seleccionada"]["dron"]
    coordinador = state["sistema"].coordinador
    asignacion = coordinador.asignarDron(ganador.idDron, orden.id_pedido)
    if (
        asignacion != {
            "id_dron": ganador.idDron,
            "id_orden": orden.id_pedido,
        }
        or ganador.estado != EstadoDron.ASIGNADO
    ):
        if ganador.estado == EstadoDron.ASIGNADO:
            ganador.estado = EstadoDron.LIBRE
        raise RuntimeError("La asignación del dron no se completó correctamente")

    orden.estado = EstadoPedido.ASIGNADO
    coordinador.colaEntregas[:] = [
        pedido for pedido in coordinador.colaEntregas if pedido is not orden
    ]
    rechazados = [
        propuesta["dron"] for propuesta in propuestas
        if propuesta["dron"] is not ganador
    ]
    msgs = []
    msgs.append(acl("ACCEPT-PROPOSAL", "AgenteCoordinadorFlota",
                    ganador.idDron,
                    f"asignarDron({orden.id_pedido}, ruta)"))
    for r in rechazados:
        msgs.append(acl("REJECT-PROPOSAL", "AgenteCoordinadorFlota",
                        r.idDron, "propuesta_no_seleccionada"))
    msgs.append(acl("INFORM", ganador.idDron, "AgenteCoordinadorFlota",
                    f"ruta_asignada({orden.id_pedido})"))
    msgs.append(nota(
        "AgenteCoordinadorFlota",
        "ACL de ruta conservado según el diagrama; el modelo no calcula "
        "ni almacena una ruta",
    ))
    return {"dron_seleccionado": ganador, "trazas": msgs}


def _g3_sin_propuestas(state):
    """Rama else: ningún dron propone, orden queda en cola."""
    orden = state["orden"]
    orden.estado = EstadoPedido.EN_COLA
    coordinador = state["sistema"].coordinador
    if not any(pedido is orden for pedido in coordinador.colaEntregas):
        coordinador.colaEntregas.append(orden)
    return {"trazas": [
        nota("AgenteCoordinadorFlota",
             "la orden permanece en colaEntregas; el CFP podrá "
             "reintentarse en una invocación posterior"),
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
    d = _g4_dron_asignado(state)
    eta = _calcular_eta(dist, d.velocidad_kmh)
    return {"trazas": [
        acl("INFORM", d.idDron, "AgenteCliente",
            f"hora_estimada_llegada({orden.id_pedido}, ETA = {eta} min)"),
    ]}

def _g4_dron_asignado(state):
    """Obtiene el dron seleccionado o busca el asignado en la flota."""
    dron = state.get("dron_seleccionado")
    if dron is None:
        dron = next(
            (d for d in state["sistema"].drones
             if d.estado == EstadoDron.ASIGNADO),
            None,
        )
    if dron is None or dron.estado != EstadoDron.ASIGNADO:
        raise ValueError("El escenario 4 requiere un dron asignado")
    return dron


def _g4_dron_navega(state):
    """Loop: navegación del dron."""
    d = _g4_dron_asignado(state)
    d.navegarRuta()
    if d.detectarObstaculo():
        d.evitarColisiones()
    return {"trazas": [
        nota(d.idDron, "navegarRuta() / detectarObstaculo() / evitarColisiones()"),
    ]}


def _g4_dron_solicita_presencia(state):
    """AgenteDron solicita confirmación de presencia al cliente."""
    orden = state["orden"]
    d = _g4_dron_asignado(state)
    return {"trazas": [
        acl("REQUEST", d.idDron, "AgenteCliente",
            f"confirmarPresencia({orden.id_pedido})"),
    ]}

def _g4_cliente_ingresa_pin(state):
    """El cliente ingresa el PIN y el dron lo valida."""
    if state.get("variante") == "reprogramar":
        return {"pin_valido": False, "trazas": []}

    dron = _g4_dron_asignado(state)
    cliente = state["sistema"].cliente
    pin = cliente.ingresarPIN(state["pin_cliente"])
    valido = dron.validarPIN(
        pin, state["sistema"].politicasEntrega["pin_cliente"]
    )
    if not valido:
        return {"pin_valido": False, "trazas": []}

    return {
        "pin_valido": True,
        "trazas": [
            acl("INFORM", "AgenteCliente", dron.idDron, "confirmacionPIN(****)"),
            nota(dron.idDron, "validarPIN()"),
        ],
    }


def _g4_decidir(state):
    """Rama: entrega o reprogramar."""
    if state.get("variante") == "reprogramar" or not state["pin_valido"]:
        return "reprogramar"
    return "entrega"


def _g4_entrega(state):
    """Rama ok: PIN + validación + entrega + confirmación + informe."""
    orden = state["orden"]
    dron = _g4_dron_asignado(state)
    if not state["pin_valido"]:
        raise ValueError("No se puede entregar sin validar el PIN")
    dron.entregarPaquete()
    if dron.estado != EstadoDron.LIBRE:
        raise RuntimeError("El dron no quedó libre después de la entrega")
    if not state["sistema"].cliente.confirmarRecepcion():
        raise RuntimeError("El cliente no confirmó la recepción")
    orden.estado = EstadoPedido.ENTREGADO
    return {"trazas": [
        nota(dron.idDron, "entregarPaquete()"),
        acl("INFORM", dron.idDron, "AgenteCliente",
            f"paquete_entregado({orden.id_pedido})"),
        acl("INFORM", "AgenteCliente", dron.idDron, "recepcion_confirmada"),
        acl("INFORM", dron.idDron, "AgenteCoordinadorFlota",
            f"entrega_exitosa({orden.id_pedido})"),
    ]}


def _g4_reprogramar(state):
    """Rama else: reprogramación."""
    orden = state["orden"]
    dron = _g4_dron_asignado(state)
    reprogramacion = state["sistema"].cliente.reprogramarEntrega(
        orden.id_pedido, "nuevaHora"
    )
    if reprogramacion != {
        "id_orden": orden.id_pedido,
        "nueva_hora": "nuevaHora",
    }:
        raise RuntimeError("El cliente no aceptó la solicitud de reprogramación")
    dron.completarEnvio()
    if dron.estado != EstadoDron.LIBRE:
        raise RuntimeError("El dron no quedó libre tras la reprogramación")
    orden.estado = EstadoPedido.REPROGRAMADO
    return {"trazas": [
        acl("REQUEST", "AgenteCliente", dron.idDron,
            f"reprogramarEntrega({orden.id_pedido}, nuevaHora)"),
        acl("AGREE", dron.idDron, "AgenteCliente",
            "reprogramacion_aceptada"),
        acl("INFORM", dron.idDron, "AgenteCoordinadorFlota",
            f"entrega_reprogramada({orden.id_pedido}, nuevaHora)"),
    ]}


def construir_grafo_4():
    g = StateGraph(Estado)
    g.add_node("dron_notifica_eta", _g4_dron_notifica_eta)
    g.add_node("dron_navega", _g4_dron_navega)
    g.add_node("dron_solicita_presencia", _g4_dron_solicita_presencia)
    g.add_node("cliente_ingresa_pin", _g4_cliente_ingresa_pin)
    g.add_node("g4_entrega", _g4_entrega)
    g.add_node("g4_reprogramar", _g4_reprogramar)
    g.set_entry_point("dron_notifica_eta")
    g.add_edge("dron_notifica_eta", "dron_navega")
    g.add_edge("dron_navega", "dron_solicita_presencia")
    g.add_edge("dron_solicita_presencia", "cliente_ingresa_pin")
    g.add_conditional_edges("cliente_ingresa_pin", _g4_decidir, {
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
    dron = state["dron_seleccionado"]
    return {"trazas": [
        acl("SUBSCRIBE", "AgenteCoordinadorFlota", "AgenteTraficoClima",
            "notificar_alertas(sectores)", "FIPA-Subscribe"),
        acl("SUBSCRIBE", dron.idDron, "AgenteTraficoClima",
            "notificar_alertas(ruta_actual)"),
    ], "suscriptores_alertas": ["AgenteCoordinadorFlota", dron.idDron]}


def _g5_trafico_acepta(state):
    """T acepta suscripciones."""
    dron = state["dron_seleccionado"]
    return {"trazas": [
        acl("AGREE", "AgenteTraficoClima", "AgenteCoordinadorFlota", ""),
        acl("AGREE", "AgenteTraficoClima", dron.idDron, ""),
    ]}


def _g5_trafico_alerta(state):
    """T detecta evento y emite alertas (par)."""
    sistema = state["sistema"]
    orden = state["orden"]
    dron = state["dron_seleccionado"]
    alerta = sistema.trafico.emitirAlerta(
        orden.ubicacion, state.get("variante", "critica")
    )
    alerta_notificada = sistema.trafico.notificarSuscriptores(alerta)
    if alerta_notificada is not alerta:
        raise RuntimeError("La alerta notificada no coincide con la alerta emitida")

    if alerta not in sistema.coordinador.alertasTrafico:
        sistema.coordinador.alertasTrafico.append(alerta)
    if alerta not in dron.alertasRecibidas:
        dron.alertasRecibidas.append(alerta)

    return {"alerta_clima": alerta, "severidad": alerta.severidad, "trazas": [
        nota("AgenteTraficoClima",
             "detectar ráfaga de viento / lluvia, emitirAlerta()"),
        acl("INFORM", "AgenteTraficoClima", "AgenteCoordinadorFlota",
            "alerta_clima(sector, severidad)"),
        acl("INFORM", "AgenteTraficoClima", dron.idDron,
            "alerta_clima(sector, severidad)"),
    ]}


def _g5_decidir(state):
    """Rama: severidad crítica o moderada."""
    return state.get("variante", "critica")


def _g5_critica(state):
    """Rama crítica: F cancela, D aterriza, D informa."""
    orden = state["orden"]
    dron = state["dron_seleccionado"]
    dron.irACargar()
    if dron.estado != EstadoDron.CARGANDO:
        raise RuntimeError("El dron no quedó en estado de carga")
    orden.estado = EstadoPedido.EN_COLA
    cola = state["sistema"].coordinador.colaEntregas
    if not any(pedido is orden for pedido in cola):
        cola.append(orden)
    return {"trazas": [
        acl("CANCEL", "AgenteCoordinadorFlota", dron.idDron,
            f"cancelar_entrega({orden.id_pedido})"),
        nota(dron.idDron, "aterrizar / ir a cargar batería"),
        acl("INFORM", dron.idDron, "AgenteCoordinadorFlota",
            f"entrega_cancelada({orden.id_pedido})"),
    ]}


def _g5_moderada(state):
    """Rama moderada: D solicita nueva ruta, F acepta y envía."""
    orden = state["orden"]
    dron = state["dron_seleccionado"]
    if not dron.solicitarNuevasRutas():
        raise RuntimeError("El dron no pudo solicitar una nueva ruta")
    if not state["sistema"].coordinador.solicitarRutas():
        raise RuntimeError("El coordinador no pudo solicitar rutas")
    return {"trazas": [
        acl("REQUEST", dron.idDron, "AgenteCoordinadorFlota",
            f"solicitarNuevaRuta({orden.id_pedido}, evitar = sector)"),
        acl("AGREE", "AgenteCoordinadorFlota", dron.idDron, ""),
        acl("INFORM", "AgenteCoordinadorFlota", dron.idDron,
            f"nueva_ruta({orden.id_pedido}, ruta)"),
        nota("AgenteCoordinadorFlota",
             "ACL conservado como traza del diagrama; los agentes no calculan "
             "ni almacenan una ruta alternativa"),
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
    dron = state["dron_seleccionado"]
    if not isinstance(orden, Pedido) or not isinstance(dron, AgenteDron):
        raise ValueError("El escenario 6 requiere un Pedido y un AgenteDron reales")
    dron.estado = EstadoDron.FALLA
    return {"trazas": [
        nota("AgenteDron1", "detecta falla mecánica o cambio brusco de clima"),
        acl("FAILURE", "AgenteDron1", "AgenteCoordinadorFlota",
            f"entrega_abortada({orden.id_pedido}, causa)"),
    ], "dron_fallado": dron}


def _g6_coordinador_responde(state):
    """F solicita el retorno; el modelo no simula la maniobra física."""
    orden = state["orden"]
    dron = state["dron_fallado"]
    return {"trazas": [
        acl("REQUEST", "AgenteCoordinadorFlota", "AgenteDron1",
            "aterrizar_y_retornar_a_base"),
        acl("AGREE", "AgenteDron1", "AgenteCoordinadorFlota", ""),
        acl("INFORM", "AgenteDron1", "AgenteCliente",
            f"entrega_demorada({orden.id_pedido})"),
        nota("AgenteDron1",
             "la solicitud de retorno queda en la traza; el modelo no "
             "implementa una maniobra física"),
    ]}


def _g6_coordinador_notifica_gestor(state):
    """F informa al gestor, gestor pone orden en cola, gestor pide despachar."""
    orden = state["orden"]
    orden.estado = EstadoPedido.EN_COLA
    gestor = state["sistema"].gestor
    gestor.estadoOrden = EstadoPedido.EN_COLA
    cola = state["sistema"].coordinador.colaEntregas
    if not any(pedido is orden for pedido in cola):
        cola.append(orden)
    return {"trazas": [
        acl("INFORM", "AgenteCoordinadorFlota", "AgenteGestorPedidos",
            f"orden_pendiente_reasignacion({orden.id_pedido})"),
        nota("AgenteGestorPedidos", "estadoOrden = en_cola"),
        acl("REQUEST", "AgenteGestorPedidos", "AgenteCoordinadorFlota",
            f"despacharOrden({orden.id_pedido})"),
    ]}


def _g6_coordinador_reasigna_nota(state):
    """Evalúa con Contract-Net los drones libres distintos del averiado."""
    coordinador = state["sistema"].coordinador
    dron_fallado = state["dron_fallado"]
    propuestas = []
    for dron in coordinador.dronesDisponibles:
        if dron is dron_fallado or dron.estado != EstadoDron.LIBRE:
            continue
        evaluacion = dron.evaluarPropuesta(state["distancia_km"])
        if evaluacion["puede"]:
            propuestas.append({"dron": dron, **evaluacion})

    propuesta = coordinador.optimizarEntregas(propuestas)
    return {
        "propuestas": propuestas,
        "propuesta_seleccionada": propuesta,
        "trazas": [
            nota("AgenteCoordinadorFlota",
                 "reinicia la asignación de dron (CFP, ver Diagrama 3)"),
        ],
    }


def _g6_decidir(state):
    """Rama: hay dron disponible o sin drones."""
    return (
        "con_dron"
        if state["propuesta_seleccionada"] is not None
        else "sin_drones"
    )


def _g6_con_dron(state):
    """Rama ok: dron reasignado."""
    orden = state["orden"]
    propuesta = state["propuesta_seleccionada"]
    dron = propuesta["dron"]
    if dron is state["dron_fallado"]:
        raise RuntimeError("No se puede reasignar el dron averiado")
    coordinador = state["sistema"].coordinador
    asignacion = coordinador.asignarDron(dron.idDron, orden.id_pedido)
    if (
        asignacion != {
            "id_dron": dron.idDron,
            "id_orden": orden.id_pedido,
        }
        or dron.estado != EstadoDron.ASIGNADO
    ):
        raise RuntimeError("No se pudo completar la reasignación del dron")

    orden.estado = EstadoPedido.ASIGNADO
    state["sistema"].gestor.estadoOrden = EstadoPedido.ASIGNADO
    coordinador.colaEntregas[:] = [
        pedido for pedido in coordinador.colaEntregas
        if pedido is not orden
    ]
    return {"trazas": [
        # LangGraph persistirá la identidad del dron reasignado en el estado.
        acl("INFORM", "AgenteCoordinadorFlota", "AgenteGestorPedidos",
            f"dron_reasignado({orden.id_pedido}, "
            f"{propuesta['eta_min']} min)"),
        acl("INFORM", "AgenteGestorPedidos", "AgenteCliente",
            f"nueva_hora_estimada({orden.id_pedido})"),
    ], "dron_seleccionado": dron}


def _g6_sin_drones(state):
    """Rama else: sin drones disponibles."""
    orden = state["orden"]
    orden.estado = EstadoPedido.EN_COLA
    gestor = state["sistema"].gestor
    gestor.estadoOrden = EstadoPedido.EN_COLA
    cola = state["sistema"].coordinador.colaEntregas
    if not any(pedido is orden for pedido in cola):
        cola.append(orden)
    return {"trazas": [
        acl("FAILURE", "AgenteCoordinadorFlota", "AgenteGestorPedidos",
            f"sin_drones_disponibles({orden.id_pedido})"),
        acl("INFORM", "AgenteGestorPedidos", "AgenteCliente",
            f"entrega_reprogramada({orden.id_pedido})"),
    ], "dron_seleccionado": None}


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
    elif n == 2 and st.get("orden") is None:
        ubicacion = "Base Naval" if variante == "restringida" else "Bocagrande"
        solicitud = st["sistema"].cliente.solicitarPedido(
            "Paquete-001", ubicacion
        )
        if not st["sistema"].gestor.validarPedido(solicitud):
            raise ValueError("No se pudo preparar la orden para el escenario 2")
        st["orden"] = st["sistema"].gestor.generarOrden(solicitud)
    elif n == 3:
        if st["orden"] is None:
            solicitud = st["sistema"].cliente.solicitarPedido(
                "Paquete-001", "Bocagrande"
            )
            if not st["sistema"].gestor.validarPedido(solicitud):
                raise ValueError("No se pudo preparar la orden para el escenario 3")
            st["orden"] = st["sistema"].gestor.generarOrden(solicitud)
        if variante == "sin_propuestas":
            for dron in st["sistema"].drones:
                dron.nivelBateria = 20
    elif n == 4:
        orden_existente = st["orden"] is not None
        if st["orden"] is None:
            solicitud = st["sistema"].cliente.solicitarPedido(
                "Paquete-001", "Bocagrande"
            )
            if not st["sistema"].gestor.validarPedido(solicitud):
                raise ValueError("No se pudo preparar la orden para el escenario 4")
            st["orden"] = st["sistema"].gestor.generarOrden(solicitud)
        if st["dron_seleccionado"] is None:
            asignados = [
                d for d in st["sistema"].drones
                if d.estado == EstadoDron.ASIGNADO
            ]
            if orden_existente and st["orden"].estado == EstadoPedido.ASIGNADO:
                if len(asignados) != 1:
                    raise ValueError(
                        "No se puede identificar de forma inequívoca "
                        "el dron ya asignado"
                    )
                dron = asignados[0]
            else:
                dron = next(
                    (d for d in st["sistema"].drones
                     if d.estado == EstadoDron.LIBRE),
                    None,
                )
                if dron is None:
                    raise ValueError("No hay drones libres para el escenario 4")
                asignacion = st["sistema"].coordinador.asignarDron(
                    dron.idDron, st["orden"].id_pedido
                )
                if (
                    asignacion != {
                        "id_dron": dron.idDron,
                        "id_orden": st["orden"].id_pedido,
                    }
                    or dron.estado != EstadoDron.ASIGNADO
                ):
                    raise RuntimeError("No se pudo asignar el dron al escenario 4")
                st["orden"].estado = EstadoPedido.ASIGNADO
            st["dron_seleccionado"] = dron
    elif n == 5:
        if st["orden"] is None:
            orden_existente = next(
                (orden for orden in st["sistema"].gestor.listaPedidos
                 if isinstance(orden, Pedido)),
                None,
            )
            if orden_existente is not None:
                st["orden"] = orden_existente
            else:
                solicitud = st["sistema"].cliente.solicitarPedido(
                    "Paquete-001", "Bocagrande"
                )
                if not st["sistema"].gestor.validarPedido(solicitud):
                    raise ValueError(
                        "No se pudo preparar la orden para el escenario 5"
                    )
                st["orden"] = st["sistema"].gestor.generarOrden(solicitud)
        if st["dron_seleccionado"] is None:
            drones_asignados = [
                dron for dron in st["sistema"].drones
                if dron.estado == EstadoDron.ASIGNADO
            ]
            if st["orden"].estado == EstadoPedido.ASIGNADO:
                if len(drones_asignados) != 1:
                    raise ValueError(
                        "No se puede identificar de forma inequívoca "
                        "el dron asignado al escenario 5"
                    )
                dron = drones_asignados[0]
            else:
                dron = next(
                    (dron for dron in st["sistema"].drones
                     if dron.estado == EstadoDron.LIBRE),
                    None,
                )
                if dron is None:
                    raise ValueError("No hay drones libres para el escenario 5")
                asignacion = st["sistema"].coordinador.asignarDron(
                    dron.idDron, st["orden"].id_pedido
                )
                if (
                    asignacion != {
                        "id_dron": dron.idDron,
                        "id_orden": st["orden"].id_pedido,
                    }
                    or dron.estado != EstadoDron.ASIGNADO
                ):
                    raise RuntimeError(
                        "No se pudo asignar el dron para el escenario 5"
                    )
                st["orden"].estado = EstadoPedido.ASIGNADO
            st["dron_seleccionado"] = dron
    elif n == 6:
        sistema = st["sistema"]
        if st["orden"] is None:
            orden_existente = next(
                (orden for orden in sistema.gestor.listaPedidos
                 if isinstance(orden, Pedido)),
                None,
            )
            if orden_existente is None:
                solicitud = sistema.cliente.solicitarPedido(
                    "Paquete-001", "Bocagrande"
                )
                if not sistema.gestor.validarPedido(solicitud):
                    raise ValueError(
                        "No se pudo preparar la orden para el escenario 6"
                    )
                orden_existente = sistema.gestor.generarOrden(solicitud)
            st["orden"] = orden_existente

        if st["dron_seleccionado"] is None:
            if st["orden"].estado in (
                EstadoPedido.ASIGNADO,
                EstadoPedido.EN_VUELO,
            ):
                asignados = [
                    dron for dron in sistema.drones
                    if dron.estado in (
                        EstadoDron.ASIGNADO,
                        EstadoDron.EN_VUELO,
                    )
                ]
                if len(asignados) != 1:
                    raise ValueError(
                        "No se puede identificar de forma inequívoca "
                        "el dron del pedido para el escenario 6"
                    )
                dron_fallado = asignados[0]
            else:
                dron_fallado = next(
                    (dron for dron in sistema.drones
                     if dron.estado == EstadoDron.LIBRE),
                    None,
                )
                if dron_fallado is None:
                    raise ValueError(
                        "No hay un dron libre para preparar el escenario 6"
                    )
                asignacion = sistema.coordinador.asignarDron(
                    dron_fallado.idDron, st["orden"].id_pedido
                )
                if (
                    asignacion != {
                        "id_dron": dron_fallado.idDron,
                        "id_orden": st["orden"].id_pedido,
                    }
                    or dron_fallado.estado != EstadoDron.ASIGNADO
                ):
                    raise RuntimeError(
                        "No se pudo asignar el dron inicial del escenario 6"
                    )
                st["orden"].estado = EstadoPedido.ASIGNADO
            st["dron_seleccionado"] = dron_fallado

        if st["dron_seleccionado"] not in sistema.drones:
            raise ValueError("El dron seleccionado no pertenece al sistema")
        if variante == "sin_drones":
            for dron in sistema.drones:
                if dron is not st["dron_seleccionado"]:
                    dron.nivelBateria = 20
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
    """Encadena los grafos 1 -> 2 -> 3 -> 4 sobre un sistema compartido."""
    sistema = SistemaEntregaDrones()
    estado = estado_inicial("ok", sistema=sistema)
    todas = []
    for numero, variante in (
        (1, "ok"),
        (2, "despejado"),
        (3, "normal"),
        (4, "entrega"),
    ):
        estado["variante"] = variante
        estado["trazas"] = []
        estado = CONSTRUCTORES[numero]().invoke(estado)
        todas.extend(estado["trazas"])
    return todas
