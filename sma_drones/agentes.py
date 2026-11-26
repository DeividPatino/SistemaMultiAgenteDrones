"""
sma_drones/agentes.py
Clases del modelo: organización, entorno, 5 agentes con sus roles.
Implementa exactamente lo descrito en docs/modelo_de_clases.md.
"""


# ---------------------------------------------------------------------------
#  Tipos de apoyo
# ---------------------------------------------------------------------------

class EstadoPedido:
    EN_COLA = "en_cola"
    ASIGNADO = "asignado"
    EN_VUELO = "en_vuelo"
    ENTREGADO = "entregado"
    REPROGRAMADO = "reprogramado"


class EstadoDron:
    LIBRE = "libre"
    ASIGNADO = "asignado"
    EN_VUELO = "en_vuelo"
    CARGANDO = "cargando"
    FALLA = "falla"


class GPSPoint:
    """Coordenada GPS simple."""
    def __init__(self, lat=0.0, lon=0.0, nombre=""):
        self.lat = lat
        self.lon = lon
        self.nombre = nombre


class Pedido:
    def __init__(self, id_pedido="", paquete="", ubicacion=None, estado=EstadoPedido.EN_COLA):
        self.id_pedido = id_pedido
        self.paquete = paquete
        self.ubicacion = ubicacion
        self.estado = estado


class Dron:
    def __init__(self, id_dron="", nivel_bateria=100, velocidad_kmh=20.0,
                 posicion=None, estado=EstadoDron.LIBRE):
        self.id_dron = id_dron
        self.nivel_bateria = nivel_bateria
        self.velocidad_kmh = velocidad_kmh
        self.posicion = posicion or GPSPoint()
        self.estado = estado


class Zona:
    def __init__(self, nombre="", restringida=False):
        self.nombre = nombre
        self.restringida = restringida


class Sector:
    def __init__(self, nombre="", zonas=None):
        self.nombre = nombre
        self.zonas = zonas or []


class Reporte:
    def __init__(self, tipo="", contenido=""):
        self.tipo = tipo
        self.contenido = contenido


class Alerta:
    def __init__(self, sector="", severidad="", descripcion=""):
        self.sector = sector
        self.severidad = severidad
        self.descripcion = descripcion


class DateTime:
    def __init__(self, valor=""):
        self.valor = valor


# ---------------------------------------------------------------------------
#  Entorno
# ---------------------------------------------------------------------------

class CiudadCartagena:
    """«environment» CiudadCartagena"""
    def __init__(self):
        self.sectores = ["Centro Histórico", "Bocagrande", "Manga", "Getsemaní"]
        self.condicionesClimaticas = "favorable"
        self.zonasRestringidas = ["Base Naval", "Aeropuerto"]

    def publicarEventoClima(self, sector="Centro Histórico", severidad="moderada"):
        """Publica un evento climático en un sector."""
        return Alerta(sector=sector, severidad=severidad,
                      descripcion=f"Alerta climática en {sector}")

    def consultarZona(self, nombre_zona):
        """Verifica si una zona está restringida."""
        return nombre_zona in self.zonasRestringidas


# ---------------------------------------------------------------------------
#  Agentes (cada uno con arquitectura, tipo, rol)
# ---------------------------------------------------------------------------

class AgenteCliente:
    """«agent» AgenteCliente — juega el rol «Consumidor»"""
    arquitectura = "Reactiva"
    tipo = "Basado en reglas de usuario"
    rol = "Consumidor"

    def __init__(self, id_cliente="C001"):
        # Atributos del modelo de clases
        self.idCliente = id_cliente
        self.ubicacionGPS = GPSPoint(10.39, -75.51, "Bocagrande")
        self.horaEstimada = ""
        self.solicitudConfirmacion = False
        self.confirmacionPIN = ""

    # --- Métodos (acciones/objetivos) ---
    def recibirEnvio(self):
        """Deber: recibir el envío."""
        return True

    def solicitarPedido(self, paquete, ubicacion):
        """Deber: solicitar un pedido."""
        return {"paquete": paquete, "ubicacion": ubicacion}

    def ingresarPIN(self, pin):
        """Acción: ingresar PIN de confirmación."""
        self.confirmacionPIN = pin
        return pin

    def confirmarRecepcion(self):
        """Acción: confirmar recepción del paquete."""
        return True

    def reprogramarEntrega(self, id_orden, nueva_hora):
        """Derecho: solicitar reprogramación."""
        return {"id_orden": id_orden, "nueva_hora": nueva_hora}

    # Rol Consumidor — deberes
    def proveerUbicacion(self):
        """Deber del rol Consumidor: proveer ubicación GPS."""
        return self.ubicacionGPS

    # Rol Consumidor — derechos
    def registrarQuejas(self):
        """Derecho del rol Consumidor."""
        return True


class AgenteGestorPedidos:
    """«agent» AgenteGestorPedidos — juega el rol «Despachador»"""
    arquitectura = "Deliberativa"
    tipo = "Basado en metas"
    rol = "Despachador"

    def __init__(self):
        self.datosUsuario = {}
        self.listaPedidos = []
        self.estadoOrden = EstadoPedido.EN_COLA

    # --- Métodos ---
    def procesarPedidos(self):
        """Procesa la cola de pedidos."""
        return self.listaPedidos

    def validarPedido(self, datos):
        """Valida que el pedido tenga los datos requeridos."""
        return bool(datos.get("paquete") and datos.get("ubicacion"))

    def generarOrden(self, datos):
        """Genera una orden a partir de los datos validados."""
        orden = Pedido(id_pedido="ORD-001", paquete=datos["paquete"],
                       ubicacion=datos["ubicacion"], estado=EstadoPedido.EN_COLA)
        self.listaPedidos.append(orden)
        self.estadoOrden = EstadoPedido.EN_COLA
        return orden

    def enviarACola(self, orden):
        """Envía la orden a la cola de entregas."""
        return orden

    # Rol Despachador — deberes
    def prepararDespacho(self):
        """Deber del rol Despachador."""
        return True

    # Rol Despachador — derechos
    def registrarOrdenes(self):
        """Derecho del rol Despachador."""
        return True


class AgenteCoordinadorFlota:
    """«agent» AgenteCoordinadorFlota — juega el rol «Monitor»"""
    arquitectura = "Deliberativa"
    tipo = "Basado en utilidad"
    rol = "Monitor"

    def __init__(self):
        self.dronesDisponibles = []
        self.colaEntregas = []
        self.alertasTrafico = []

    # --- Métodos ---
    def optimizarEntregas(self, propuestas):
        """Elige la propuesta con mayor utilidad = (batería - requerida) - 2*ETA."""
        if not propuestas:
            return None
        mejor = max(propuestas, key=lambda p: p["utilidad"])
        return mejor

    def consultarCondiciones(self, sector):
        """Consulta condiciones de un sector."""
        return {"sector": sector}

    def asignarDron(self, id_dron, id_orden):
        """Asigna un dron a una orden."""
        return {"id_dron": id_dron, "id_orden": id_orden}

    def monitorearBateria(self):
        """Monitorea baterías de la flota."""
        return self.dronesDisponibles

    def reasignarOrden(self, id_orden):
        """Reasigna una orden a otro dron."""
        return id_orden

    # Rol Monitor — deberes
    def supervisarEntrega(self):
        """Deber del rol Monitor."""
        return True

    def coordinarDespacho(self):
        """Deber del rol Monitor."""
        return True

    # Rol Monitor — derechos
    def asignarRecursos(self):
        """Derecho del rol Monitor."""
        return True

    def solicitarRutas(self):
        """Derecho del rol Monitor."""
        return True


class AgenteDron:
    """«agent» AgenteDron — juega el rol «Navegador»"""
    arquitectura = "Híbrida"
    tipo = "Basado en metas y reglas de seguridad"
    rol = "Navegador"

    def __init__(self, id_dron="D001", nivel_bateria=100, velocidad_kmh=20.0):
        self.idDron = id_dron
        self.nivelBateria = nivel_bateria
        self.posicionGPS = GPSPoint()
        self.estado = EstadoDron.LIBRE
        self.proximidadObstaculos = False
        self.alertasRecibidas = []
        self.velocidad_kmh = velocidad_kmh

    # --- Métodos ---
    def navegacionSegura(self):
        """Navegación con reglas de seguridad."""
        return True

    def completarEnvio(self):
        """Completa el envío actual."""
        self.estado = EstadoDron.LIBRE
        return True

    def evaluarPropuesta(self, distancia_km):
        """Evalúa si puede aceptar una propuesta de entrega.
        ETA = distancia / velocidad * 60 (minutos).
        Propone si batería >= ETA*2 + 10, rechaza si no.
        """
        eta_min = (distancia_km / self.velocidad_kmh) * 60
        bateria_requerida = eta_min * 2 + 10
        puede = self.nivelBateria >= bateria_requerida
        utilidad = (self.nivelBateria - bateria_requerida) - 2 * eta_min
        return {
            "puede": puede,
            "eta_min": round(eta_min, 1),
            "bateria_requerida": round(bateria_requerida, 1),
            "utilidad": round(utilidad, 2),
        }

    def navegarRuta(self):
        """Deber del rol Navegador: navegar la ruta asignada."""
        return True

    def detectarObstaculo(self):
        """Detecta obstáculos en la ruta."""
        return self.proximidadObstaculos

    def evitarColisiones(self):
        """Deber del rol Navegador: evitar colisiones."""
        return True

    def validarPIN(self, pin, pin_correcto):
        """Valida el PIN del cliente."""
        return str(pin) == str(pin_correcto)

    def entregarPaquete(self):
        """Entrega el paquete al cliente."""
        self.estado = EstadoDron.LIBRE
        return True

    def reportarEstado(self):
        """Deber del rol Navegador: reportar estado."""
        return {"id_dron": self.idDron, "bateria": self.nivelBateria,
                "estado": self.estado}

    def irACargar(self):
        """Va a la estación de carga."""
        self.estado = EstadoDron.CARGANDO
        return True

    # Rol Navegador — derechos
    def accederEspacioAereo(self):
        """Derecho del rol Navegador."""
        return True

    def solicitarNuevasRutas(self):
        """Derecho del rol Navegador."""
        return True


class AgenteTraficoClima:
    """«agent» AgenteTraficoClima — juega el rol «AnalistaClimatico»"""
    arquitectura = "Reactiva"
    tipo = "Basado en reglas"
    rol = "AnalistaClimatico"

    def __init__(self):
        self.reportesClima = []
        self.mapaAlertas = {}
        self.zonasRestringidas = ["Base Naval", "Aeropuerto"]

    # --- Métodos ---
    def garantizarSeguridadVuelo(self):
        """Garantiza la seguridad del vuelo."""
        return True

    def emitirAlerta(self, sector, severidad):
        """Emite una alerta climática."""
        alerta = Alerta(sector=sector, severidad=severidad)
        self.mapaAlertas[sector] = alerta
        return alerta

    def verificarZona(self, sector):
        """Verifica si un sector es zona restringida."""
        return sector in self.zonasRestringidas

    def bloquearSector(self, sector):
        """Bloquea un sector por peligro."""
        return True

    def notificarSuscriptores(self, alerta):
        """Notifica a los suscriptores de alertas."""
        return alerta

    # Rol AnalistaClimatico — deberes
    def emitirAlertasClima(self):
        """Deber del rol AnalistaClimatico."""
        return True

    def verificarZonasInseguras(self):
        """Deber del rol AnalistaClimatico."""
        return self.zonasRestringidas

    # Rol AnalistaClimatico — derechos
    def accederDatosMeteorologicos(self):
        """Derecho del rol AnalistaClimatico."""
        return True


# ---------------------------------------------------------------------------
#  Organización
# ---------------------------------------------------------------------------

class SistemaEntregaDrones:
    """«organization» SistemaEntregaDrones — dueña de los 5 agentes."""

    def __init__(self):
        self.nombre = "SistemaEntregaDrones"
        self.politicasEntrega = {
            "bateria_minima_cfp": 15,
            "pin_cliente": "4821",
            "distancia_km": 3,
        }
        # Entorno
        self.entorno = CiudadCartagena()
        # Agentes
        self.cliente = AgenteCliente()
        self.gestor = AgenteGestorPedidos()
        self.coordinador = AgenteCoordinadorFlota()
        self.trafico = AgenteTraficoClima()
        # 3 drones con datos de la demo
        self.drones = [
            AgenteDron("AgenteDron1", nivel_bateria=85, velocidad_kmh=22.5),
            AgenteDron("AgenteDron2", nivel_bateria=60, velocidad_kmh=15.0),
            AgenteDron("AgenteDron3", nivel_bateria=25, velocidad_kmh=20.0),
        ]
        self.coordinador.dronesDisponibles = self.drones

    def orquestarEntregas(self):
        """Orquesta las entregas de la organización."""
        return True

    def monitorearFlota(self):
        """Monitorea el estado de toda la flota."""
        return [d.reportarEstado() for d in self.drones]
