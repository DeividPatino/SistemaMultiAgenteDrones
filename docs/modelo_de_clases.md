# Modelo de clases (fuente de verdad en texto)

Este archivo describe el diagrama de clases `docs/diagrama_de_clases.png`. Si la imagen y este texto difieren, manda este texto.

Leyenda: **atributos** = percepciones del agente; **métodos** = acciones y objetivos del agente.

## Organización y entorno

### «organization» SistemaEntregaDrones (dueña de los 5 agentes; habita en CiudadCartagena)
- Atributos: nombre, politicasEntrega
- Métodos: orquestarEntregas(), monitorearFlota()

### «environment» CiudadCartagena
- Atributos: sectores, condicionesClimaticas, zonasRestringidas
- Métodos: publicarEventoClima(), consultarZona()

## Agentes (cada uno juega un rol)

### «agent» AgenteCliente  (juega el rol «Consumidor»)
- Arquitectura: Reactiva
- Tipo: Basado en reglas de usuario
- Atributos: idCliente, ubicacionGPS, horaEstimada, solicitudConfirmacion, confirmacionPIN
- Métodos: recibirEnvio(), solicitarPedido(), ingresarPIN(), confirmarRecepcion(), reprogramarEntrega()

### «agent» AgenteGestorPedidos  (juega el rol «Despachador»)
- Arquitectura: Deliberativa
- Tipo: Basado en metas
- Atributos: datosUsuario, listaPedidos, estadoOrden
- Métodos: procesarPedidos(), validarPedido(), generarOrden(), enviarACola()

### «agent» AgenteCoordinadorFlota  (juega el rol «Monitor»)
- Arquitectura: Deliberativa
- Tipo: Basado en utilidad
- Atributos: dronesDisponibles, colaEntregas, alertasTrafico
- Métodos: optimizarEntregas(), consultarCondiciones(), asignarDron(), monitorearBateria(), reasignarOrden()

### «agent» AgenteDron  (juega el rol «Navegador»)
- Arquitectura: Híbrida
- Tipo: Basado en metas y reglas de seguridad
- Atributos: idDron, nivelBateria, posicionGPS, estado, proximidadObstaculos, alertasRecibidas
- Métodos: navegacionSegura(), completarEnvio(), evaluarPropuesta(), navegarRuta(), detectarObstaculo(), evitarColisiones(), validarPIN(), entregarPaquete(), reportarEstado(), irACargar()

### «agent» AgenteTraficoClima  (juega el rol «AnalistaClimatico»)
- Arquitectura: Reactiva
- Tipo: Basado en reglas
- Atributos: reportesClima, mapaAlertas, zonasRestringidas
- Métodos: garantizarSeguridadVuelo(), emitirAlerta(), verificarZona(), bloquearSector(), notificarSuscriptores()

## Roles (los deberes y derechos son métodos del agente que juega el rol)

### «role» Despachador  (lo juega AgenteGestorPedidos)
- Deberes (duties): validarPedido(), generarOrden(), prepararDespacho()
- Derechos (rights): registrarOrdenes()

### «role» Monitor  (lo juega AgenteCoordinadorFlota)
- Deberes (duties): supervisarEntrega(), coordinarDespacho()
- Derechos (rights): asignarRecursos(), solicitarRutas()

### «role» Navegador  (lo juega AgenteDron)
- Deberes (duties): navegarRuta(), reportarEstado(), evitarColisiones()
- Derechos (rights): accederEspacioAereo(), solicitarNuevasRutas()

### «role» AnalistaClimatico  (lo juega AgenteTraficoClima)
- Deberes (duties): emitirAlertasClima(), verificarZonasInseguras()
- Derechos (rights): accederDatosMeteorologicos()

### «role» Consumidor  (lo juega AgenteCliente)
- Deberes (duties): solicitarPedido(), recibirEnvio(), proveerUbicacion()
- Derechos (rights): registrarQuejas(), reprogramarEntrega()

## Relaciones

- «ownership»: SistemaEntregaDrones es dueña de los 5 agentes (AgenteDron: 1..*).
- «inhabit»: SistemaEntregaDrones habita en CiudadCartagena.
- «play»: cada agente juega su rol (ver arriba).
- «dependency»: Cliente → Gestor, Gestor → Coordinador, Coordinador → Dron, Coordinador → Tráfico, Dron → Tráfico, Dron → Cliente.

## Tipos de apoyo

- Pedido, Dron, Zona, Sector, Reporte, Alerta, GPSPoint, DateTime.
- EstadoPedido = en_cola, asignado, en_vuelo, entregado, reprogramado.
- EstadoDron = libre, asignado, en_vuelo, cargando, falla.
