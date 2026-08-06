# LiquiVerde API

API de retail inteligente para analizar la sostenibilidad de productos y optimizar listas de compra bajo un presupuesto.

## Índice

- [Requisitos](#requisitos)
- [Instrucciones para ejecutar localmente](#instrucciones-para-ejecutar-localmente)
  - [Windows con PowerShell](#windows-con-powershell)
  - [Linux y macOS](#linux-y-macos)
  - [Ejecuciones posteriores](#ejecuciones-posteriores)
- [Configuración de APIs y variables de entorno](#configuración-de-apis-y-variables-de-entorno)
- [SQLite, seed y reconstrucción](#sqlite-seed-y-reconstrucción)
- [APIs externas](#apis-externas)
- [Dataset](#dataset)
- [Supuestos y limitaciones](#supuestos-y-limitaciones)
- [Algoritmos implementados](#algoritmos-implementados)
- [Uso de IA](#uso-de-ia)

## Requisitos

- Windows 10 u 11, una distribución Linux o macOS.
- Python 3.14.x con `pip` y el módulo `venv` disponibles.
- Acceso a internet durante la instalación inicial de dependencias.
- Git, únicamente si se clonará el repositorio en lugar de recibir el código fuente directamente.

El proyecto fue desarrollado inicialmente en Windows con PowerShell y Python 3.14. La API y sus dependencias son multiplataforma; las diferencias de ejecución se limitan principalmente a la creación y activación del entorno virtual y a la copia del archivo de configuración.

Antes de comenzar, abre una terminal en el directorio `liquiverde-api` y confirma que la versión requerida de Python está instalada. En Windows usa `py -3.14 --version`; en Linux y macOS usa `python3.14 --version`. El resultado debe indicar Python 3.14.x.

Si el comando correspondiente no existe, instala Python 3.14 desde [python.org](https://www.python.org/downloads/) o mediante el gestor de versiones o paquetes del sistema. En algunas distribuciones Linux también será necesario instalar por separado el paquete correspondiente a `venv`.

## Instrucciones para ejecutar localmente

### Windows con PowerShell

1. Crea un entorno virtual aislado dentro de `.venv` usando Python 3.14:

```powershell
py -3.14 -m venv .venv
```

2. Activa el entorno virtual para que `python` y `pip` utilicen las dependencias locales del proyecto:

```powershell
.\.venv\Scripts\Activate.ps1
```

Si PowerShell bloquea la activación por su política de ejecución, permite scripts únicamente para la sesión actual con `Set-ExecutionPolicy -Scope Process Bypass` y repite la activación. Este cambio desaparece al cerrar la terminal.

3. Instala las versiones de las dependencias registradas en `requirements.txt`:

```powershell
python -m pip install -r requirements.txt
```

4. Crea el archivo de configuración local a partir de los valores públicos de ejemplo:

```powershell
Copy-Item .env.example .env
```

5. Inicia Uvicorn, carga las variables de `.env` y activa la recarga automática cuando cambie el código:

```powershell
python -m uvicorn app.main:app --reload --env-file .env
```

### Linux y macOS

1. Crea el entorno virtual con Python 3.14:

```bash
python3.14 -m venv .venv
```

2. Activa el entorno para utilizar su intérprete y sus dependencias:

```bash
source .venv/bin/activate
```

3. Instala las dependencias fijadas por el proyecto:

```bash
python -m pip install -r requirements.txt
```

4. Copia la configuración de ejemplo como configuración local:

```bash
cp .env.example .env
```

5. Inicia la API con las variables de `.env` y recarga automática durante el desarrollo:

```bash
python -m uvicorn app.main:app --reload --env-file .env
```

En macOS, si Python se instaló con Homebrew, puede ser necesario usar la ruta o el alias mostrado al finalizar la instalación. En Linux, el nombre del ejecutable puede variar según la distribución o el gestor de versiones utilizado; al crear `.venv` debe apuntar siempre a Python 3.14.

La API queda disponible en `http://localhost:8000` y su documentación interactiva en `http://localhost:8000/docs`. Para detener el servidor, presiona `Ctrl+C`.

### Ejecuciones posteriores

No es necesario volver a crear el entorno, reinstalar dependencias ni copiar `.env` mientras esos archivos sigan presentes.

En Windows, activa el entorno con:

```powershell
.\.venv\Scripts\Activate.ps1
```

En Linux o macOS, actívalo con:

```bash
source .venv/bin/activate
```

Después, en cualquiera de los sistemas, inicia nuevamente el servidor:

```bash
python -m uvicorn app.main:app --reload --env-file .env
```

El comando `deactivate` permite salir del entorno virtual cuando termines de trabajar.

## Configuración de APIs y variables de entorno

`.env.example` contiene valores públicos listos para copiar:

| Variable                       | Propósito                  | Valor predeterminado                       |
| ------------------------------ | -------------------------- | ------------------------------------------ |
| `DATABASE_URL`                 | Base SQLite                | `sqlite:///./liquiverde.db`                |
| `CORS_ORIGINS`                 | Orígenes web permitidos    | `http://localhost:5173`                    |
| `OPEN_FOOD_FACTS_BASE_URL`     | API de productos           | `https://world.openfoodfacts.org/api/v3.6` |
| `OPEN_PRICES_BASE_URL`         | API de precios por GTIN    | `https://prices.openfoodfacts.org/api/v1`  |
| `AGRIBALYSE_BASE_URL`          | Dataset ambiental de ADEME | API pública Data Fair                      |
| `EXTERNAL_API_TIMEOUT_SECONDS` | Timeout por consulta       | `5`                                        |
| `EXTERNAL_API_USER_AGENT`      | Identificación del cliente | Valor público de LiquiVerde                |

No se requieren credenciales privadas. Uvicorn carga los valores predeterminados definidos en `app/config.py`.

## SQLite, seed y reconstrucción

El archivo `liquiverde.db` es local y no se versiona. Al arrancar la API:

1. SQLAlchemy crea `products` y `environmental_factors` si no existen.
2. Si `products` está vacía, carga `data/products.json`.
3. Si `environmental_factors` está vacía, carga `data/environmental_factors.json`.

Para reconstruir desde cero, detén la API, elimina `liquiverde.db` y vuelve a iniciarla.

El seed explícito es idempotente:

```bash
python -m app.commands.seed_catalog
```

Este comando usa el intérprete del entorno virtual activo, actualiza por clave estable y no duplica productos.

### APIs externas

#### Open Food Facts

Se consulta exclusivamente cuando el usuario ingresa un GTIN válido que no existe en SQLite. Antes de usar red, el dominio valida:

- 8, 12 o 13 dígitos ASCII;
- checksum GS1 módulo 10;
- rechazo de códigos formados solo por ceros;
- normalización de GTIN-12 a 13 dígitos para la consulta.

Un producto encontrado se normaliza y persiste. Búsqueda textual, análisis, optimización, arranque y `/health` nunca consultan Open Food Facts. `404` significa que el producto no existe; timeout, `429` o errores del proveedor se traducen a un error controlado.

#### Open Prices

Después de obtener un producto externo, la API consulta su precio más reciente en Open Prices cuando todavía no existe un precio local. También reintenta el enriquecimiento si el usuario vuelve a consultar el mismo GTIN mientras el producto sigue sin precio.

La consulta usa el GTIN original y los filtros `currency=CLP` y `order_by=-date`. Solo se acepta un valor positivo asociado a una ubicación chilena. Si no hay observaciones compatibles o el proveedor falla, el producto se conserva sin precio y el usuario puede completarlo desde la pantalla de análisis. Búsqueda textual, análisis, optimización, arranque y `/health` nunca consultan Open Prices.

Cuando se obtiene un valor, el producto registra `open_food_facts` y `open_prices` como fuentes. Open Prices reúne observaciones comunitarias: el valor representa el precio publicado para ese producto, moneda, lugar y fecha, pero no garantiza disponibilidad ni vigencia en todos los comercios.

#### AGRIBALYSE

No se consulta durante el flujo web. Su única entrada es:

```bash
python -m app.commands.refresh_environmental_factors
```

El comando usa el entorno virtual activo, consulta seis términos alimentarios en el dataset público de ADEME, obtiene la mediana de `Changement_climatique` y actualiza cada categoría independientemente.

#### Respaldo ambiental

`data/environmental_factors.json` contiene seis factores normalizados con fuente y versión. No copia la respuesta completa de ADEME. Permite crear una base funcional sin internet y conserva el valor anterior cuando una categoría no puede refrescarse.

## Dataset

`data/products.json` contiene 18 productos ficticios, tres por categoría:

- arroz;
- pastas;
- leches y bebidas vegetales;
- legumbres;
- café;
- chocolate.

Todos usan GTIN-13 sintéticos con checksum válido. Los precios en CLP son valores de demostración creados para comparar alternativas y no representan precios vigentes de comercios reales.

## Supuestos y limitaciones

- AGRIBALYSE modela producción y consumo francés; el mapeo hacia categorías usadas en Chile es una aproximación documentada.
- La huella climática se expresa en kg CO₂e/kg y se multiplica por el peso del envase.
- Origen y reciclabilidad afectan el score ambiental, pero no se convierten artificialmente en CO₂e.
- Fairtrade, Rainforest Alliance y UTZ se reconocen como indicadores sociales. Ausencia de certificación no significa desempeño negativo.
- Open Food Facts es comunitario y puede contener campos incompletos.
- Open Prices tiene cobertura limitada en Chile y sus observaciones pueden quedar desactualizadas; por eso su ausencia nunca bloquea el flujo manual.
- Un producto externo necesita precio, peso y categoría válida antes de participar en la optimización.
- No se modelan inventario, tiendas, fechas, rutas ni disponibilidad.

## Algoritmos implementados

### Algoritmo 1: scoring de sostenibilidad

Cada componente está limitado a `[0, 100]`.

#### Económico

Se compara el precio por 100 g dentro de la categoría:

```text
economic_score = 100 × (max_price - product_price) / (max_price - min_price)
```

Si todos cuestan lo mismo o falta el dato, se usa 50.

#### Ambiental

```text
environmental_score =
    0.70 × climate_score
  + 0.15 × local_origin_score
  + 0.15 × recyclable_packaging_score
```

`climate_score` es una normalización inversa de la huella del envase. Origen y reciclabilidad reciben 100, 0 o 50 cuando el dato es positivo, negativo o desconocido.

#### Social

- certificación reconocida: 100;
- indicador responsable documentado: 75;
- dato desconocido: 50.

#### Total

```text
total_score =
    0.40 × economic_score
  + 0.40 × environmental_score
  + 0.20 × social_score
```

La respuesta incluye desglose, razones, fuentes, confianza, precio por 100 g y CO₂e por envase.

### Algoritmo 2: optimización de la lista

El segundo algoritmo es una mochila de elección múltiple con programación dinámica dispersa.

Cada necesidad contiene una referencia, categoría y cantidad. Los candidatos son los productos completos de esa categoría. El algoritmo mantiene estados por costos alcanzables, descarta estados dominados y aplica este orden:

Las prioridades económica, ambiental y social admiten valores entre 0 y 100 y deben sumar exactamente 100. La API rechaza cualquier otra distribución con `422 INVALID_REQUEST`; el algoritmo divide los valores por 100 antes de calcular la utilidad ponderada.

1. mayor cantidad de categorías cubiertas;
2. mayor utilidad según prioridades normalizadas;
3. menor costo;
4. identificadores lexicográficamente menores.

Para `n` necesidades, `c` candidatos medios y `s` estados no dominados, el costo es `O(n × s × c)` y la memoria `O(s)` por etapa.

La respuesta compara la selección con las referencias originales y distingue ahorro, sobrecosto, impacto evitado, aumento de CO₂e y categorías no cubiertas.

## Uso de IA

La asistencia de IA se utilizó para:

- planificación de la implementación, incluyendo diseño y arquitectura;
- asistencia en la revisión de código y el análisis de posibles casos límite;
- implementación de la solución por partes para mantener el control y la trazabilidad del trabajo.
