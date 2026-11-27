"""
tests/test_contra_mermaid.py
Lee cada diagrama_N.mmd y comprueba que las trazas del grafo
coinciden con las flechas ACL del diagrama (performativa, emisor, receptor).
"""
import os
import re
import unittest
from sma_drones.agentes import Alerta, EstadoDron, EstadoPedido
from sma_drones.grafos import CONSTRUCTORES, _estado_para_variante, ejecutar

DOCS = os.path.join(os.path.dirname(__file__), "..", "docs", "diagramas_secuencia")

# Mapa de alias en los diagramas → nombres reales
ALIAS = {
    "C": "AgenteCliente",
    "G": "AgenteGestorPedidos",
    "F": "AgenteCoordinadorFlota",
    "D": "AgenteDron1",
    "D1": "AgenteDron1",
    "D2": "AgenteDron2",
    "D3": "AgenteDron3",
    "T": "AgenteTraficoClima",
}


def _parsear_alias(mmd_text):
    """Extrae alias definidos como 'participant X as ...<br/>NombreAgente'.
    Normaliza 'AgenteDron N' a 'AgenteDronN' y 'AgenteDron' (sin número) a 'AgenteDron1'.
    """
    alias_map = {}
    for m in re.finditer(
        r'participant\s+(\w+)\s+as\s+.*?(?:<br/>|<br>)\s*(.+)',
        mmd_text
    ):
        nombre = m.group(2).strip()
        nombre = nombre.replace(" ", "")  # "AgenteDron 1" -> "AgenteDron1"
        # En diagramas 4,5,6: "AgenteDron" (sin número) = AgenteDron1
        if nombre == "AgenteDron":
            nombre = "AgenteDron1"
        alias_map[m.group(1)] = nombre
    return alias_map


def _parsear_acls_mermaid(mmd_text, alias_map):
    """Extrae firma, contenido y protocolo de las flechas ACL del Mermaid."""
    lineas = mmd_text.strip().split("\n")
    rama_actual = "principal"
    ramas = {"principal": [], "else": []}
    en_alt = False

    for linea in lineas:
        linea = linea.strip()

        if linea.startswith("alt "):
            en_alt = True
            rama_actual = "principal"
            continue
        if linea.startswith("else ") and en_alt:
            rama_actual = "else"
            continue
        if linea == "end" and en_alt:
            en_alt = False
            rama_actual = "principal"
            continue

        # Buscar flecha con ACL
        m = re.match(r'(\w+)\s*-+>+\s*(\w+)\s*:\s*«ACL:([^»]+)»', linea)
        if m:
            emisor_alias = m.group(1)
            receptor_alias = m.group(2)
            performativa = m.group(3)
            emisor = alias_map.get(emisor_alias, ALIAS.get(emisor_alias, emisor_alias))
            receptor = alias_map.get(receptor_alias, ALIAS.get(receptor_alias, receptor_alias))
            # Limpiar posibles espacios en AgenteDron 1 -> AgenteDron1
            emisor = emisor.replace(" ", "")
            receptor = receptor.replace(" ", "")
            if en_alt or rama_actual != "principal":
                destino = (rama_actual,)
            else:
                destino = ("principal", "else")

            partes = linea[m.end():].strip()
            if partes.startswith("<br/>"):
                partes = partes[len("<br/>"):]
            segmentos = partes.split("<br/>") if partes else []
            contenido = segmentos[0].strip() if segmentos else ""
            protocolo = ""
            for segmento in segmentos[1:]:
                segmento = segmento.strip()
                if segmento.startswith(":protocol "):
                    protocolo = segmento[len(":protocol "):].strip()
                    break
            mensaje = (performativa, emisor, receptor, contenido, protocolo)
            for rama in destino:
                ramas[rama].append(mensaje)
    return ramas


def _parsear_flechas(mmd_text, alias_map):
    """Extrae la firma ACL por rama, conservando el helper existente."""
    detalladas = _parsear_acls_mermaid(mmd_text, alias_map)
    return {
        rama: [mensaje[:3] for mensaje in mensajes]
        for rama, mensajes in detalladas.items()
    }


def _leer_mmd(n):
    """Lee el archivo diagrama_N.mmd y devuelve el texto."""
    path = os.path.join(DOCS, f"diagrama_{n}.mmd")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _acl_de_trazas(trazas):
    """Filtra solo los mensajes ACL de las trazas y devuelve (perf, emisor, receptor)."""
    return [(t["performativa"], t["emisor"], t["receptor"])
            for t in trazas if t["tipo"] == "acl"]


def _acl_detalladas_de_trazas(trazas):
    """Filtra ACL como (performativa, emisor, receptor, contenido, protocolo)."""
    return [
        (
            mensaje["performativa"],
            mensaje["emisor"],
            mensaje["receptor"],
            mensaje["contenido"],
            mensaje.get("protocolo", ""),
        )
        for mensaje in trazas
        if mensaje["tipo"] == "acl"
    ]


def _normalizar_contenido_acl(contenido):
    """Normaliza solo el formato numérico equivalente, por ejemplo 8.0 -> 8."""
    return re.sub(r"(?<=\d)\.0(?=\s|,|\)|$)", "", contenido)


def _assert_acls_mermaid(
    testcase,
    trazas,
    mmd_text,
    alias_map,
    rama,
    sustituciones=None,
    protocolos_comunes=None,
    performativas=None,
):
    """Compara secuencia, firma, contenido y protocolo contra una rama Mermaid."""
    esperados = _parsear_acls_mermaid(mmd_text, alias_map)[rama]
    if performativas is not None:
        esperados = [
            mensaje for mensaje in esperados
            if mensaje[0] in performativas
        ]
    sustituciones = sustituciones or {}
    protocolos_comunes = protocolos_comunes or {}
    esperados_normalizados = []
    for performativa, emisor, receptor, contenido, protocolo in esperados:
        for marcador, valor in sustituciones.items():
            contenido = contenido.replace(marcador, str(valor))
        if not protocolo:
            protocolo = protocolos_comunes.get(performativa, "")
        esperados_normalizados.append((
            performativa,
            emisor,
            receptor,
            _normalizar_contenido_acl(contenido),
            protocolo,
        ))

    obtenidos = [
        (
            performativa,
            emisor,
            receptor,
            _normalizar_contenido_acl(contenido),
            protocolo,
        )
        for performativa, emisor, receptor, contenido, protocolo
        in _acl_detalladas_de_trazas(trazas)
        if performativas is None or performativa in performativas
    ]
    testcase.assertEqual(obtenidos, esperados_normalizados)


def _assert_alerta_grafo5(testcase, estado, resultado, severidad):
    sistema = estado["sistema"]
    orden = estado["orden"]
    dron = estado["dron_seleccionado"]
    alerta = resultado["alerta_clima"]

    testcase.assertIsInstance(alerta, Alerta)
    testcase.assertIs(alerta, sistema.trafico.mapaAlertas[orden.ubicacion])
    testcase.assertEqual(alerta.sector, orden.ubicacion)
    testcase.assertEqual(alerta.severidad, severidad)
    testcase.assertEqual(resultado["severidad"], severidad)
    testcase.assertEqual(
        resultado["suscriptores_alertas"],
        ["AgenteCoordinadorFlota", dron.idDron],
    )
    testcase.assertEqual(
        sum(alerta_recibida is alerta
            for alerta_recibida in sistema.coordinador.alertasTrafico),
        1,
    )
    testcase.assertEqual(
        sum(alerta_recibida is alerta for alerta_recibida in dron.alertasRecibidas),
        1,
    )


class TestGrafo1(unittest.TestCase):
    def test_ok(self):
        mmd = _leer_mmd(1)
        alias = _parsear_alias(mmd)
        ramas = _parsear_flechas(mmd, alias)
        trazas = ejecutar(1, "ok")
        esperado = ramas["principal"]
        obtenido = _acl_de_trazas(trazas)
        self.assertEqual(obtenido, esperado,
                        f"Grafo 1/ok:\n  esperado={esperado}\n  obtenido={obtenido}")

    def test_datos_invalidos(self):
        mmd = _leer_mmd(1)
        alias = _parsear_alias(mmd)
        ramas = _parsear_flechas(mmd, alias)
        trazas = ejecutar(1, "datos_invalidos")
        esperado = ramas["else"]
        obtenido = _acl_de_trazas(trazas)
        self.assertEqual(obtenido, esperado,
                        f"Grafo 1/datos_invalidos:\n  esperado={esperado}\n  obtenido={obtenido}")


class TestGrafo2(unittest.TestCase):
    def test_despejado(self):
        mmd = _leer_mmd(2)
        alias = _parsear_alias(mmd)
        ramas = _parsear_flechas(mmd, alias)
        trazas = ejecutar(2, "despejado")
        esperado = ramas["principal"]
        obtenido = _acl_de_trazas(trazas)
        self.assertEqual(obtenido, esperado,
                        f"Grafo 2/despejado:\n  esperado={esperado}\n  obtenido={obtenido}")

    def test_restringida(self):
        mmd = _leer_mmd(2)
        alias = _parsear_alias(mmd)
        ramas = _parsear_flechas(mmd, alias)
        trazas = ejecutar(2, "restringida")
        esperado = ramas["else"]
        obtenido = _acl_de_trazas(trazas)
        self.assertEqual(obtenido, esperado,
                        f"Grafo 2/restringida:\n  esperado={esperado}\n  obtenido={obtenido}")


class TestGrafo3(unittest.TestCase):
    def test_normal(self):
        mmd = _leer_mmd(3)
        alias = _parsear_alias(mmd)
        ramas = _parsear_flechas(mmd, alias)
        estado = _estado_para_variante(3, "normal")
        sistema = estado["sistema"]
        orden = estado["orden"]
        drones = list(sistema.drones)
        resultado = CONSTRUCTORES[3]().invoke(estado)
        trazas = resultado["trazas"]
        esperado = ramas["principal"]
        obtenido = _acl_de_trazas(trazas)
        self.assertEqual(obtenido, esperado,
                        f"Grafo 3/normal:\n  esperado={esperado}\n  obtenido={obtenido}")
        _assert_acls_mermaid(
            self,
            trazas,
            mmd,
            alias,
            "principal",
            sustituciones={
                "idOrden": orden.id_pedido,
                "distancia": estado["distancia_km"],
            },
            # FIPA-Contract-Net está declarado una vez para el grupo de CFP.
            protocolos_comunes={"CFP": "FIPA-Contract-Net"},
        )

        ganador = resultado["dron_seleccionado"]
        propuesta_ganadora = max(
            resultado["propuestas"],
            key=lambda propuesta: propuesta["utilidad"],
        )
        self.assertIs(resultado["orden"], orden)
        self.assertIs(resultado["propuesta_seleccionada"], propuesta_ganadora)
        self.assertIs(ganador, propuesta_ganadora["dron"])
        asignacion_acl = next(
            mensaje for mensaje in trazas
            if mensaje["tipo"] == "acl"
            and mensaje["performativa"] == "ACCEPT-PROPOSAL"
        )
        self.assertEqual(asignacion_acl["receptor"], ganador.idDron)
        self.assertEqual(
            asignacion_acl["contenido"],
            f"asignarDron({orden.id_pedido}, ruta)",
        )
        self.assertEqual(ganador.estado, EstadoDron.ASIGNADO)
        self.assertEqual(orden.estado, EstadoPedido.ASIGNADO)
        self.assertEqual(len(sistema.gestor.listaPedidos), 1)
        self.assertIs(sistema.gestor.listaPedidos[0], orden)
        self.assertEqual(sistema.coordinador.colaEntregas, [])
        for dron in drones:
            if dron is not ganador:
                self.assertEqual(dron.estado, EstadoDron.LIBRE)

    def test_sin_propuestas(self):
        """Los 3 drones rechazan: se comparan los CFP y 3 REFUSE."""
        mmd = _leer_mmd(3)
        alias = _parsear_alias(mmd)
        ramas = _parsear_flechas(mmd, alias)
        estado = _estado_para_variante(3, "sin_propuestas")
        sistema = estado["sistema"]
        orden = estado["orden"]
        drones = list(sistema.drones)
        resultado = CONSTRUCTORES[3]().invoke(estado)
        trazas = resultado["trazas"]
        obtenido = _acl_de_trazas(trazas)
        _assert_acls_mermaid(
            self,
            trazas,
            mmd,
            alias,
            "principal",
            sustituciones={
                "idOrden": orden.id_pedido,
                "distancia": estado["distancia_km"],
            },
            protocolos_comunes={"CFP": "FIPA-Contract-Net"},
            performativas={"CFP"},
        )
        # Esperamos: 3 CFP + 3 REFUSE (no hay propuestas)
        cfps = [(p, e, r) for p, e, r in obtenido if p == "CFP"]
        refuses = [(p, e, r) for p, e, r in obtenido if p == "REFUSE"]
        self.assertEqual(len(cfps), 3, f"Debe haber 3 CFP, hay {len(cfps)}")
        self.assertEqual(len(refuses), 3, f"Debe haber 3 REFUSE, hay {len(refuses)}")
        self.assertEqual(
            _acl_detalladas_de_trazas(trazas)[3:],
            [
                ("REFUSE", dron.idDron, "AgenteCoordinadorFlota",
                 "bateria_insuficiente", "")
                for dron in drones
            ],
        )
        self.assertEqual(resultado["propuestas"], [])
        self.assertIsNone(resultado["propuesta_seleccionada"])
        self.assertIsNone(resultado["dron_seleccionado"])
        self.assertIs(resultado["orden"], orden)
        self.assertEqual(orden.estado, EstadoPedido.EN_COLA)
        self.assertEqual(len(sistema.gestor.listaPedidos), 1)
        self.assertIs(sistema.gestor.listaPedidos[0], orden)
        self.assertEqual(sistema.coordinador.colaEntregas, [orden])
        self.assertIs(sistema.coordinador.colaEntregas[0], orden)
        for dron in drones:
            self.assertEqual(dron.estado, EstadoDron.LIBRE)


class TestGrafo4(unittest.TestCase):
    def test_entrega(self):
        mmd = _leer_mmd(4)
        alias = _parsear_alias(mmd)
        ramas = _parsear_flechas(mmd, alias)
        trazas = ejecutar(4, "entrega")
        esperado = ramas["principal"]
        obtenido = _acl_de_trazas(trazas)
        self.assertEqual(obtenido, esperado,
                        f"Grafo 4/entrega:\n  esperado={esperado}\n  obtenido={obtenido}")

    def test_reprogramar(self):
        mmd = _leer_mmd(4)
        alias = _parsear_alias(mmd)
        ramas = _parsear_flechas(mmd, alias)
        trazas = ejecutar(4, "reprogramar")
        esperado = ramas["else"]
        obtenido = _acl_de_trazas(trazas)
        self.assertEqual(obtenido, esperado,
                        f"Grafo 4/reprogramar:\n  esperado={esperado}\n  obtenido={obtenido}")


class TestGrafo5(unittest.TestCase):
    def test_critica(self):
        mmd = _leer_mmd(5)
        alias = _parsear_alias(mmd)
        ramas = _parsear_flechas(mmd, alias)
        estado = _estado_para_variante(5, "critica")
        sistema = estado["sistema"]
        orden = estado["orden"]
        dron = estado["dron_seleccionado"]
        resultado = CONSTRUCTORES[5]().invoke(estado)
        trazas = resultado["trazas"]
        esperado = ramas["principal"]
        obtenido = _acl_de_trazas(trazas)
        self.assertEqual(obtenido, esperado,
                        f"Grafo 5/critica:\n  esperado={esperado}\n  obtenido={obtenido}")
        _assert_acls_mermaid(
            self,
            trazas,
            mmd,
            alias,
            "principal",
            sustituciones={"idOrden": orden.id_pedido},
        )
        _assert_alerta_grafo5(self, estado, resultado, "critica")
        self.assertIs(resultado["orden"], orden)
        self.assertIs(resultado["dron_seleccionado"], dron)
        self.assertEqual(dron.estado, EstadoDron.CARGANDO)
        self.assertEqual(orden.estado, EstadoPedido.EN_COLA)
        self.assertEqual(sistema.coordinador.colaEntregas, [orden])
        self.assertIs(sistema.coordinador.colaEntregas[0], orden)

    def test_moderada(self):
        """La ruta se inspecciona estructuralmente, no se prueba su no-cálculo universal."""
        mmd = _leer_mmd(5)
        alias = _parsear_alias(mmd)
        ramas = _parsear_flechas(mmd, alias)
        estado = _estado_para_variante(5, "moderada")
        sistema = estado["sistema"]
        orden = estado["orden"]
        dron = estado["dron_seleccionado"]
        resultado = CONSTRUCTORES[5]().invoke(estado)
        trazas = resultado["trazas"]
        esperado = ramas["else"]
        obtenido = _acl_de_trazas(trazas)
        self.assertEqual(obtenido, esperado,
                        f"Grafo 5/moderada:\n  esperado={esperado}\n  obtenido={obtenido}")
        _assert_acls_mermaid(
            self,
            trazas,
            mmd,
            alias,
            "else",
            sustituciones={"idOrden": orden.id_pedido},
        )
        _assert_alerta_grafo5(self, estado, resultado, "moderada")
        self.assertIs(resultado["orden"], orden)
        self.assertIs(resultado["dron_seleccionado"], dron)
        self.assertEqual(orden.estado, EstadoPedido.ASIGNADO)
        self.assertEqual(dron.estado, EstadoDron.ASIGNADO)
        self.assertEqual(sistema.coordinador.colaEntregas, [])
        # La rama solo invoca solicitarNuevasRutas() y solicitarRutas();
        # ambas devuelven True. Este barrido se limita a estos objetos/atributos:
        # no garantiza que no hubiera cálculo temporal, almacenamiento indirecto
        # u otra representación de ruta fuera de los objetos inspeccionados.
        self.assertFalse(any("ruta" in clave.lower() for clave in resultado))
        for objeto in (
            sistema,
            sistema.coordinador,
            sistema.trafico,
            orden,
            dron,
        ):
            self.assertFalse(any(
                "ruta" in atributo.lower() for atributo in vars(objeto)
            ))
        self.assertTrue(any(
            mensaje["tipo"] == "nota"
            and "no calculan" in mensaje["texto"]
            for mensaje in trazas
        ))


class TestGrafo6(unittest.TestCase):
    def test_con_dron(self):
        mmd = _leer_mmd(6)
        alias = _parsear_alias(mmd)
        ramas = _parsear_flechas(mmd, alias)
        estado = _estado_para_variante(6, "con_dron")
        orden = estado["orden"]
        sistema = estado["sistema"]
        dron_fallado = estado["dron_seleccionado"]
        resultado = CONSTRUCTORES[6]().invoke(estado)
        trazas = resultado["trazas"]
        esperado = ramas["principal"]
        obtenido = _acl_de_trazas(trazas)
        self.assertEqual(obtenido, esperado,
                        f"Grafo 6/con_dron:\n  esperado={esperado}\n  obtenido={obtenido}")
        dron_sustituto = resultado["dron_seleccionado"]
        self.assertIs(resultado["orden"], orden)
        self.assertIs(resultado["dron_fallado"], dron_fallado)
        self.assertEqual(dron_fallado.estado, EstadoDron.FALLA)
        self.assertIsNot(dron_sustituto, dron_fallado)
        self.assertIn(dron_sustituto, sistema.drones)
        self.assertEqual(dron_sustituto.estado, EstadoDron.ASIGNADO)
        self.assertEqual(orden.estado, EstadoPedido.ASIGNADO)
        self.assertEqual(
            sum(pedido is orden for pedido in sistema.gestor.listaPedidos), 1
        )
        self.assertFalse(any(
            pedido is orden for pedido in sistema.coordinador.colaEntregas
        ))
        self.assertTrue(any(
            mensaje["tipo"] == "acl"
            and mensaje["contenido"].startswith("dron_reasignado(")
            for mensaje in trazas
        ))

    def test_sin_drones(self):
        mmd = _leer_mmd(6)
        alias = _parsear_alias(mmd)
        ramas = _parsear_flechas(mmd, alias)
        estado = _estado_para_variante(6, "sin_drones")
        orden = estado["orden"]
        sistema = estado["sistema"]
        dron_fallado = estado["dron_seleccionado"]
        resultado = CONSTRUCTORES[6]().invoke(estado)
        trazas = resultado["trazas"]
        esperado = ramas["else"]
        obtenido = _acl_de_trazas(trazas)
        self.assertEqual(obtenido, esperado,
                        f"Grafo 6/sin_drones:\n  esperado={esperado}\n  obtenido={obtenido}")
        self.assertIs(resultado["orden"], orden)
        self.assertIs(resultado["dron_fallado"], dron_fallado)
        self.assertIsNone(resultado["dron_seleccionado"])
        self.assertEqual(dron_fallado.estado, EstadoDron.FALLA)
        self.assertEqual(orden.estado, EstadoPedido.EN_COLA)
        self.assertEqual(
            sum(pedido is orden for pedido in sistema.gestor.listaPedidos), 1
        )
        self.assertEqual(
            sum(
                pedido is orden
                for pedido in sistema.coordinador.colaEntregas
            ),
            1,
        )
        self.assertFalse(any(
            dron.estado == EstadoDron.ASIGNADO
            for dron in sistema.drones
            if dron is not dron_fallado
        ))
        mensajes_al_cliente = [
            mensaje for mensaje in trazas
            if mensaje["tipo"] == "acl"
            and mensaje["emisor"] == "AgenteGestorPedidos"
            and mensaje["receptor"] == "AgenteCliente"
            and mensaje["performativa"] == "INFORM"
        ]
        self.assertEqual(len(mensajes_al_cliente), 1)
        self.assertIn(
            "orden_pendiente_reasignacion",
            mensajes_al_cliente[0]["contenido"],
        )
        self.assertNotIn("reprogramada", mensajes_al_cliente[0]["contenido"])
        self.assertNotIn("dron_reasignado", mensajes_al_cliente[0]["contenido"])
        self.assertFalse(any(
            mensaje["tipo"] == "acl"
            and "dron_reasignado(" in mensaje["contenido"]
            for mensaje in trazas
        ))
        self.assertIs(
            mensajes_al_cliente[0],
            next(
                mensaje for mensaje in reversed(trazas)
                if mensaje["tipo"] == "acl"
            ),
        )
        bloque_sin_drones = mmd.split(
            "else sin drones disponibles", 1
        )[1].split("\n    end", 1)[0]
        contenido_diagrama = next(
            linea.strip().split("<br/>", 1)[1]
            for linea in bloque_sin_drones.splitlines()
            if linea.strip().startswith("G->>C: «ACL:INFORM»")
        )
        self.assertEqual(
            mensajes_al_cliente[0]["contenido"],
            contenido_diagrama.replace("idOrden", orden.id_pedido),
        )


if __name__ == "__main__":
    unittest.main()
