"""
tests/test_contra_mermaid.py
Lee cada diagrama_N.mmd y comprueba que las trazas del grafo
coinciden con las flechas ACL del diagrama (performativa, emisor, receptor).
"""
import os
import re
import unittest
from sma_drones.agentes import EstadoDron, EstadoPedido
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


def _parsear_flechas(mmd_text, alias_map):
    """Extrae las flechas ACL del mermaid, separando ramas alt/else.
    Devuelve un dict con las claves 'principal' y 'else'.
    """
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
                ramas[rama_actual].append((performativa, emisor, receptor))
            else:
                # Fuera de alt: va en ambas ramas
                ramas["principal"].append((performativa, emisor, receptor))
                ramas["else"].append((performativa, emisor, receptor))

    return ramas


def _leer_mmd(n):
    """Lee el archivo diagrama_N.mmd y devuelve el texto."""
    path = os.path.join(DOCS, f"diagrama_{n}.mmd")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _acl_de_trazas(trazas):
    """Filtra solo los mensajes ACL de las trazas y devuelve (perf, emisor, receptor)."""
    return [(t["performativa"], t["emisor"], t["receptor"])
            for t in trazas if t["tipo"] == "acl"]


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
        trazas = ejecutar(3, "normal")
        esperado = ramas["principal"]
        obtenido = _acl_de_trazas(trazas)
        self.assertEqual(obtenido, esperado,
                        f"Grafo 3/normal:\n  esperado={esperado}\n  obtenido={obtenido}")

    def test_sin_propuestas(self):
        """Los 3 drones rechazan: se comparan los CFP y 3 REFUSE."""
        mmd = _leer_mmd(3)
        alias = _parsear_alias(mmd)
        ramas = _parsear_flechas(mmd, alias)
        trazas = ejecutar(3, "sin_propuestas")
        obtenido = _acl_de_trazas(trazas)
        # Esperamos: 3 CFP + 3 REFUSE (no hay propuestas)
        cfps = [(p, e, r) for p, e, r in obtenido if p == "CFP"]
        refuses = [(p, e, r) for p, e, r in obtenido if p == "REFUSE"]
        self.assertEqual(len(cfps), 3, f"Debe haber 3 CFP, hay {len(cfps)}")
        self.assertEqual(len(refuses), 3, f"Debe haber 3 REFUSE, hay {len(refuses)}")


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
        orden = estado["orden"]
        dron = estado["dron_seleccionado"]
        resultado = CONSTRUCTORES[5]().invoke(estado)
        trazas = resultado["trazas"]
        esperado = ramas["principal"]
        obtenido = _acl_de_trazas(trazas)
        self.assertEqual(obtenido, esperado,
                        f"Grafo 5/critica:\n  esperado={esperado}\n  obtenido={obtenido}")
        self.assertEqual(dron.estado, EstadoDron.CARGANDO)
        self.assertEqual(orden.estado, EstadoPedido.EN_COLA)
        self.assertEqual(
            sum(pedido is orden
                for pedido in estado["sistema"].coordinador.colaEntregas),
            1,
        )

    def test_moderada(self):
        mmd = _leer_mmd(5)
        alias = _parsear_alias(mmd)
        ramas = _parsear_flechas(mmd, alias)
        trazas = ejecutar(5, "moderada")
        esperado = ramas["else"]
        obtenido = _acl_de_trazas(trazas)
        self.assertEqual(obtenido, esperado,
                        f"Grafo 5/moderada:\n  esperado={esperado}\n  obtenido={obtenido}")


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


if __name__ == "__main__":
    unittest.main()
