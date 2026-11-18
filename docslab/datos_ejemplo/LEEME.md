# Datos de ejemplo de las plantillas de gráficos

Se copian a la carpeta del cuaderno con «Usar datos de ejemplo». «Probar con los datos de ejemplo» los usa todos.
Salvo `ejemplo.csv`, se regeneran con `python herramientas/datos_ejemplo.py <ne_110m_admin_0_countries.geojson>` (semilla fija).

| Archivo | Columnas | Origen | Lo usan |
|---|---|---|---|
| `ejemplo.csv` | grupo, tratamiento, tiempo, valor, peso, altura | Sintético | Barras, líneas, dispersión, cajas, violín, densidad, enjambre, mapa de calor, correlograma, burbujas… |
| `ejemplo_series.csv` | fecha, serie, valor (104 semanas × 5 series) | Sintético | Serie temporal, área, áreas apiladas, flujo, crestas |
| `ejemplo_paises.csv` | iso3, pais, continente, poblacion, pib_musd, pib_per_capita, lat, lon | **Natural Earth** (población y PIB estimados, años 2014–2020 según el país); lat/lon = centroide del polígono mayor | Coropletas, mapa de burbujas, cartograma, piruleta |
| `ejemplo_puntos.csv` | lat, lon, ciudad | Sintético, alrededor de 16 ciudades | Mapa con puntos, mapa de hexágonos, densidad 2D |
| `ejemplo_conexiones.csv` | origen, destino, lat/lon de cada uno, valor | Coordenadas aproximadas de ciudades; valor sintético | Mapa de conexiones |
| `ejemplo_red.csv` | origen, destino, valor, grupo_origen, grupo_destino | Sintético (30 nodos en 5 grupos) | Red, arcos, agrupamiento de aristas |
| `ejemplo_flujos.csv` | origen, destino, valor | Sintético (fuentes → transformación → uso) | Sankey, cuerdas |
| `ejemplo_jerarquia.csv` | area, subarea, publicaciones | Sintético | Treemap, empaquetado circular, dona, pastel, gofre, barras circulares |
| `ejemplo_puntuaciones.csv` | muestra, grupo, 6 variables | Sintético | Radar, coordenadas paralelas, dendrograma, tabla |
| `ejemplo_palabras.csv` | palabra, frecuencia | Sintético | Nube de palabras |
| `mundo.geojson` | iso3, nombre, continente + polígonos | **Natural Earth** 1:110m Admin 0 – Countries, coordenadas a 2 decimales | Todos los mapas |

**Natural Earth** es de dominio público ([naturalearthdata.com](https://www.naturalearthdata.com/about/terms-of-use/)): «Made with Natural Earth». Las fronteras y los nombres siguen su criterio, que no refleja ninguna postura sobre disputas territoriales.

Los datos sintéticos sirven solo para probar las plantillas: no describen nada real.
