"""
tests/test_modelo_de_clases.py
Comprueba que cada clase, atributo, método, rol, arquitectura y tipo
de docs/modelo_de_clases.md existe en el código.
"""
import unittest
from sma_drones.agentes import (
    AgenteCliente, AgenteGestorPedidos, AgenteCoordinadorFlota,
    AgenteDron, AgenteTraficoClima, SistemaEntregaDrones, CiudadCartagena,
    EstadoPedido, EstadoDron, Pedido, Dron, Zona, Sector, Reporte,
    Alerta, GPSPoint, DateTime,
)


class TestTiposDeApoyo(unittest.TestCase):
    """Verifica que existen los tipos de apoyo."""

    def test_estado_pedido(self):
        self.assertEqual(EstadoPedido.EN_COLA, "en_cola")
        self.assertEqual(EstadoPedido.ASIGNADO, "asignado")
        self.assertEqual(EstadoPedido.EN_VUELO, "en_vuelo")
        self.assertEqual(EstadoPedido.ENTREGADO, "entregado")
        self.assertEqual(EstadoPedido.REPROGRAMADO, "reprogramado")

    def test_estado_dron(self):
        self.assertEqual(EstadoDron.LIBRE, "libre")
        self.assertEqual(EstadoDron.ASIGNADO, "asignado")
        self.assertEqual(EstadoDron.EN_VUELO, "en_vuelo")
        self.assertEqual(EstadoDron.CARGANDO, "cargando")
        self.assertEqual(EstadoDron.FALLA, "falla")

    def test_clases_auxiliares_existen(self):
        for cls in [Pedido, Dron, Zona, Sector, Reporte, Alerta, GPSPoint, DateTime]:
            self.assertTrue(callable(cls), f"{cls.__name__} debe existir")


class TestOrganizacion(unittest.TestCase):
    """SistemaEntregaDrones y CiudadCartagena."""

    def test_sistema_atributos(self):
        s = SistemaEntregaDrones()
        self.assertTrue(hasattr(s, "nombre"))
        self.assertTrue(hasattr(s, "politicasEntrega"))

    def test_sistema_metodos(self):
        s = SistemaEntregaDrones()
        self.assertTrue(callable(getattr(s, "orquestarEntregas", None)))
        self.assertTrue(callable(getattr(s, "monitorearFlota", None)))

    def test_ciudad_atributos(self):
        c = CiudadCartagena()
        self.assertTrue(hasattr(c, "sectores"))
        self.assertTrue(hasattr(c, "condicionesClimaticas"))
        self.assertTrue(hasattr(c, "zonasRestringidas"))

    def test_ciudad_metodos(self):
        c = CiudadCartagena()
        self.assertTrue(callable(getattr(c, "publicarEventoClima", None)))
        self.assertTrue(callable(getattr(c, "consultarZona", None)))


class TestAgenteCliente(unittest.TestCase):
    def test_arquitectura_tipo_rol(self):
        self.assertEqual(AgenteCliente.arquitectura, "Reactiva")
        self.assertEqual(AgenteCliente.tipo, "Basado en reglas de usuario")
        self.assertEqual(AgenteCliente.rol, "Consumidor")

    def test_atributos(self):
        a = AgenteCliente()
        for attr in ["idCliente", "ubicacionGPS", "horaEstimada",
                      "solicitudConfirmacion", "confirmacionPIN"]:
            self.assertTrue(hasattr(a, attr), f"Falta atributo {attr}")

    def test_metodos_agente(self):
        a = AgenteCliente()
        for met in ["recibirEnvio", "solicitarPedido", "ingresarPIN",
                     "confirmarRecepcion", "reprogramarEntrega"]:
            self.assertTrue(callable(getattr(a, met, None)), f"Falta método {met}")

    def test_metodos_rol(self):
        """Deberes y derechos del rol Consumidor."""
        a = AgenteCliente()
        for met in ["solicitarPedido", "recibirEnvio", "proveerUbicacion",
                     "registrarQuejas", "reprogramarEntrega"]:
            self.assertTrue(callable(getattr(a, met, None)), f"Falta método de rol {met}")


class TestAgenteGestorPedidos(unittest.TestCase):
    def test_arquitectura_tipo_rol(self):
        self.assertEqual(AgenteGestorPedidos.arquitectura, "Deliberativa")
        self.assertEqual(AgenteGestorPedidos.tipo, "Basado en metas")
        self.assertEqual(AgenteGestorPedidos.rol, "Despachador")

    def test_atributos(self):
        a = AgenteGestorPedidos()
        for attr in ["datosUsuario", "listaPedidos", "estadoOrden"]:
            self.assertTrue(hasattr(a, attr), f"Falta atributo {attr}")

    def test_metodos(self):
        a = AgenteGestorPedidos()
        for met in ["procesarPedidos", "validarPedido", "generarOrden", "enviarACola"]:
            self.assertTrue(callable(getattr(a, met, None)), f"Falta método {met}")

    def test_metodos_rol(self):
        a = AgenteGestorPedidos()
        for met in ["validarPedido", "generarOrden", "prepararDespacho", "registrarOrdenes"]:
            self.assertTrue(callable(getattr(a, met, None)), f"Falta método de rol {met}")


class TestAgenteCoordinadorFlota(unittest.TestCase):
    def test_arquitectura_tipo_rol(self):
        self.assertEqual(AgenteCoordinadorFlota.arquitectura, "Deliberativa")
        self.assertEqual(AgenteCoordinadorFlota.tipo, "Basado en utilidad")
        self.assertEqual(AgenteCoordinadorFlota.rol, "Monitor")

    def test_atributos(self):
        a = AgenteCoordinadorFlota()
        for attr in ["dronesDisponibles", "colaEntregas", "alertasTrafico"]:
            self.assertTrue(hasattr(a, attr), f"Falta atributo {attr}")

    def test_metodos(self):
        a = AgenteCoordinadorFlota()
        for met in ["optimizarEntregas", "consultarCondiciones", "asignarDron",
                     "monitorearBateria", "reasignarOrden"]:
            self.assertTrue(callable(getattr(a, met, None)), f"Falta método {met}")

    def test_metodos_rol(self):
        a = AgenteCoordinadorFlota()
        for met in ["supervisarEntrega", "coordinarDespacho",
                     "asignarRecursos", "solicitarRutas"]:
            self.assertTrue(callable(getattr(a, met, None)), f"Falta método de rol {met}")


class TestAgenteDron(unittest.TestCase):
    def test_arquitectura_tipo_rol(self):
        self.assertEqual(AgenteDron.arquitectura, "Híbrida")
        self.assertEqual(AgenteDron.tipo, "Basado en metas y reglas de seguridad")
        self.assertEqual(AgenteDron.rol, "Navegador")

    def test_atributos(self):
        a = AgenteDron()
        for attr in ["idDron", "nivelBateria", "posicionGPS", "estado",
                      "proximidadObstaculos", "alertasRecibidas"]:
            self.assertTrue(hasattr(a, attr), f"Falta atributo {attr}")

    def test_metodos(self):
        a = AgenteDron()
        for met in ["navegacionSegura", "completarEnvio", "evaluarPropuesta",
                     "navegarRuta", "detectarObstaculo", "evitarColisiones",
                     "validarPIN", "entregarPaquete", "reportarEstado", "irACargar"]:
            self.assertTrue(callable(getattr(a, met, None)), f"Falta método {met}")

    def test_metodos_rol(self):
        a = AgenteDron()
        for met in ["navegarRuta", "reportarEstado", "evitarColisiones",
                     "accederEspacioAereo", "solicitarNuevasRutas"]:
            self.assertTrue(callable(getattr(a, met, None)), f"Falta método de rol {met}")


class TestAgenteTraficoClima(unittest.TestCase):
    def test_arquitectura_tipo_rol(self):
        self.assertEqual(AgenteTraficoClima.arquitectura, "Reactiva")
        self.assertEqual(AgenteTraficoClima.tipo, "Basado en reglas")
        self.assertEqual(AgenteTraficoClima.rol, "AnalistaClimatico")

    def test_atributos(self):
        a = AgenteTraficoClima()
        for attr in ["reportesClima", "mapaAlertas", "zonasRestringidas"]:
            self.assertTrue(hasattr(a, attr), f"Falta atributo {attr}")

    def test_metodos(self):
        a = AgenteTraficoClima()
        for met in ["garantizarSeguridadVuelo", "emitirAlerta", "verificarZona",
                     "bloquearSector", "notificarSuscriptores"]:
            self.assertTrue(callable(getattr(a, met, None)), f"Falta método {met}")

    def test_metodos_rol(self):
        a = AgenteTraficoClima()
        for met in ["emitirAlertasClima", "verificarZonasInseguras",
                     "accederDatosMeteorologicos"]:
            self.assertTrue(callable(getattr(a, met, None)), f"Falta método de rol {met}")


class TestRelaciones(unittest.TestCase):
    """Verifica relaciones ownership e inhabit."""
    def test_ownership(self):
        s = SistemaEntregaDrones()
        self.assertIsNotNone(s.cliente)
        self.assertIsNotNone(s.gestor)
        self.assertIsNotNone(s.coordinador)
        self.assertIsNotNone(s.trafico)
        self.assertTrue(len(s.drones) >= 1, "Debe haber al menos 1 dron")

    def test_inhabit(self):
        s = SistemaEntregaDrones()
        self.assertIsInstance(s.entorno, CiudadCartagena)


if __name__ == "__main__":
    unittest.main()
