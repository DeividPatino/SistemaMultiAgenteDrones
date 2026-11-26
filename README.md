# Sistema Multiagente de Entrega de Paquetes con Drones — Cartagena de Indias

Proyecto universitario de **Sistemas Multiagente** que simula la entrega de paquetes con drones
en Cartagena de Indias usando 5 agentes FIPA ACL y LangGraph.

## Requisitos

- Python 3.10+
- Dependencias: `langgraph`

## Instalación

```bash
pip install -r requirements.txt
```

## Uso

```bash
# Ejecutar todos los grafos (variante principal)
python main.py

# Ejecutar un grafo específico
python main.py 3

# Ejecutar con variante alternativa (rama else)
python main.py 3 --variante sin_propuestas

# Flujo completo encadenado (grafos 1 → 2 → 3 → 4)
python main.py completo

# Formato FIPA ACL en s-expression
python main.py --acl

# Imprimir grafo de LangGraph en Mermaid
python main.py --mermaid
```

## Tests

```bash
python -m unittest discover -s tests -v
```

## Diagrama de secuencia → Grafo → Variantes

| Diagrama | Nombre                                     | Grafo   | Variante principal | Variante else    |
|----------|--------------------------------------------|---------|--------------------|------------------|
| 1        | Solicitud y validación del pedido          | grafo_1 | `ok`               | `datos_invalidos`|
| 2        | Envío de orden y consulta de condiciones   | grafo_2 | `despejado`        | `restringida`    |
| 3        | Asignación del dron (Contract-Net)         | grafo_3 | `normal`           | `sin_propuestas` |
| 4        | Ejecución de entrega y confirmación PIN    | grafo_4 | `entrega`          | `reprogramar`    |
| 5        | Alertas de clima y zonas peligrosas        | grafo_5 | `critica`          | `moderada`       |
| 6        | Falla durante la entrega y reasignación    | grafo_6 | `con_dron`         | `sin_drones`     |

## Estructura de carpetas

```
main.py                          # Demo por consola
requirements.txt                 # langgraph
README.md                        # Este archivo
sma_drones/
  __init__.py
  mensajes.py                    # acl(), nota(), firma(), formatear(), a_sexpr()
  agentes.py                    # 5 agentes, organización, entorno, roles
  grafos.py                     # grafo_1..6, ejecutar(), flujo_completo()
tests/
  test_contra_mermaid.py         # Verifica trazas vs diagramas .mmd
  test_modelo_de_clases.py       # Verifica clases, atributos, métodos, roles
docs/
  modelo_de_clases.md            # Modelo de clases (fuente de verdad)
  diagrama_de_clases.png
  diagramas_secuencia/
    diagrama_1..6.mmd            # Diagramas de secuencia en Mermaid
    diagrama_1..6.png
```

## Guion de presentación (5 pasos)

1. **Contexto**: "Construimos un sistema multiagente que simula la entrega de paquetes con
   drones en Cartagena de Indias. Hay 5 agentes que se comunican con mensajes FIPA ACL."

2. **Arquitectura**: "Cada agente tiene una arquitectura (Reactiva, Deliberativa o Híbrida),
   un tipo de razonamiento (reglas, metas o utilidad) y un rol con deberes y derechos. La
   organización `SistemaEntregaDrones` es dueña de los 5 agentes y habita en el entorno
   `CiudadCartagena`."

3. **Diagramas → Grafos**: "Cada diagrama de secuencia del documento se convirtió en un
   grafo de LangGraph. Las flechas `ACL:PERFORMATIVA` son mensajes FIPA. Los bloques `alt/else`
   se implementaron como aristas condicionales (`add_conditional_edges`). Cada nodo representa
   el turno de un agente."

4. **Demo en vivo**: Ejecutar `python main.py completo` para mostrar el flujo principal
   (solicitud → validación → asignación → entrega). Luego mostrar una variante alternativa
   como `python main.py 3 --variante sin_propuestas`.

5. **Verificación**: Ejecutar los tests `python -m unittest discover -s tests -v` para
   demostrar que las trazas del código coinciden exactamente con los diagramas de secuencia.

## Decisiones de diseño

1. **Un grafo por diagrama**: Cada diagrama de secuencia (.mmd) se traduce a exactamente un
   grafo de LangGraph. Esto mantiene una correspondencia 1:1 clara y fácil de explicar.

2. **Estado con trazas aditivas**: El estado usa `Annotated[list, operator.add]` para que cada
   nodo agregue sus mensajes sin perder los anteriores. Esto permite reconstruir la traza
   completa al final.

3. **Notas vs mensajes**: Los cuadros amarillos ("Note over") del diagrama de secuencia son
   acciones internas del agente, no mensajes ACL. Se guardan como "nota" en la traza para
   distinguirlos.

4. **Bloques par como secuencia**: Los bloques `par` del diagrama (mensajes paralelos) se
   ejecutan secuencialmente dentro de un nodo, ya que LangGraph ejecuta un nodo a la vez. El
   resultado es equivalente porque todos los mensajes se producen en el mismo turno.

5. **AgenteDron genérico = AgenteDron1**: En los diagramas 4, 5 y 6 el participante "AgenteDron"
   (sin número) se mapea a AgenteDron1, que es el dron asignado en el flujo principal.

6. **Fórmula de propuesta**: Un dron propone si `batería >= ETA(min)*2 + 10`. La utilidad
   es `(batería - requerida) - 2*ETA`. El Coordinador elige la mayor utilidad.

7. **Variante sin_drones (Grafo 6)**: Se usa baterías (85, 20, 20) donde el dron 1 falló.
   Los drones restantes (2 y 3) con batería 20% no pueden proponer, así que no hay drones
   disponibles.

8. **Flujo completo**: Encadena los grafos 1→2→3→4 con la variante principal de cada uno,
   simulando un pedido exitoso de principio a fin.