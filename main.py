"""
main.py — Demo por consola del Sistema Multiagente de Entrega con Drones.

Uso:
  python main.py              # ejecuta todos los grafos (variante principal)
  python main.py 3            # ejecuta solo el grafo 3
  python main.py 3 --variante sin_propuestas
  python main.py completo     # flujo encadenado 1->2->3->4
  python main.py --acl        # formato FIPA ACL en s-expression
  python main.py --mermaid    # imprime el grafo de LangGraph
"""
import sys
from sma_drones.grafos import ejecutar, flujo_completo, CONSTRUCTORES, VARIANTE_PRINCIPAL
from sma_drones.mensajes import formatear, a_sexpr


NOMBRES_GRAFO = {
    1: "Solicitud y validación del pedido",
    2: "Envío de orden y consulta de condiciones",
    3: "Asignación del dron (Contract-Net)",
    4: "Ejecución de la entrega y confirmación PIN",
    5: "Alertas de clima y zonas peligrosas",
    6: "Falla durante la entrega y reasignación",
}


def imprimir_trazas(trazas, modo_acl=False):
    """Imprime la lista de trazas numeradas."""
    for i, msg in enumerate(trazas, 1):
        if modo_acl:
            print(a_sexpr(msg))
            print()
        else:
            print(formatear(msg, i))


def imprimir_mermaid(n):
    """Imprime la representación del grafo de LangGraph."""
    grafo = CONSTRUCTORES[n]()
    try:
        print(grafo.get_graph().draw_mermaid())
    except Exception:
        print(f"  (no se pudo generar el diagrama Mermaid del grafo {n})")


def main():
    args = sys.argv[1:]
    modo_acl = "--acl" in args
    modo_mermaid = "--mermaid" in args

    # Limpiar flags de los args
    args = [a for a in args if a not in ("--acl", "--mermaid")]

    # Parsear variante
    variante = None
    if "--variante" in args:
        idx = args.index("--variante")
        if idx + 1 < len(args):
            variante = args[idx + 1]
        args = [a for a in args if a != "--variante" and a != variante]

    # Determinar qué ejecutar
    if not args or args == []:
        # Todos los grafos
        for n in range(1, 7):
            v = variante or VARIANTE_PRINCIPAL[n]
            print(f"\n{'='*60}")
            print(f"  GRAFO {n}: {NOMBRES_GRAFO[n]} (variante: {v})")
            print(f"{'='*60}")
            if modo_mermaid:
                imprimir_mermaid(n)
            trazas = ejecutar(n, v)
            imprimir_trazas(trazas, modo_acl)

    elif args[0] == "completo":
        print(f"\n{'='*60}")
        print(f"  FLUJO COMPLETO: Grafos 1 -> 2 -> 3 -> 4")
        print(f"{'='*60}")
        trazas = flujo_completo()
        imprimir_trazas(trazas, modo_acl)

    else:
        try:
            n = int(args[0])
        except ValueError:
            print(f"Error: argumento '{args[0]}' no reconocido.")
            print("Uso: python main.py [N | completo] [--variante X] [--acl] [--mermaid]")
            sys.exit(1)
        if n < 1 or n > 6:
            print(f"Error: el grafo debe ser entre 1 y 6.")
            sys.exit(1)
        v = variante or VARIANTE_PRINCIPAL[n]
        print(f"\n{'='*60}")
        print(f"  GRAFO {n}: {NOMBRES_GRAFO[n]} (variante: {v})")
        print(f"{'='*60}")
        if modo_mermaid:
            imprimir_mermaid(n)
        trazas = ejecutar(n, v)
        imprimir_trazas(trazas, modo_acl)


if __name__ == "__main__":
    main()
