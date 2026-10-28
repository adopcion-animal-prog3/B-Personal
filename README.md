<!-- calidad:inicio -->
![Calidad](https://img.shields.io/badge/Calidad-sin%20c%C3%B3digo-lightgrey)

**Calidad de servicios:** sin código en `main` (no evaluable).
<!-- calidad:fin -->

# B-Personal API

Backend inicial de B-Personal construido con FastAPI y PostgreSQL.

## Requisitos

- Python 3.12 o posterior.
- PostgreSQL 18.6 accesible desde el entorno donde se ejecuta la API.

## Instalación y configuración

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Reemplazá los valores ilustrativos de `DATABASE_URL` por la URL de conexión provista para el entorno. La aplicación no necesita una base disponible para iniciar; las comprobaciones de base de datos reportarán `503` hasta que la conexión esté configurada y disponible.

Variables de entorno:

| Variable | Obligatoria | Descripción |
| --- | --- | --- |
| `DATABASE_URL` | Para conectarse a PostgreSQL | URL SQLAlchemy, por ejemplo `postgresql+psycopg://usuario:contraseña@host:5432/base`. |
| `LOG_LEVEL` | No | Nivel de logging: `CRITICAL`, `ERROR`, `WARNING`, `INFO` o `DEBUG`. El valor predeterminado es `INFO`. |

No agregues el archivo `.env` al control de versiones.

## Ejecución

```bash
uvicorn app.main:app --reload
```

La documentación OpenAPI queda disponible en `http://127.0.0.1:8000/docs` y el esquema en `http://127.0.0.1:8000/openapi.json`.

## Comprobaciones

```bash
curl -i http://127.0.0.1:8000/health
curl -i http://127.0.0.1:8000/health/db
```

`GET /health` informa que el proceso está disponible sin depender de PostgreSQL. `GET /health/db` ejecuta `SELECT 1` y responde `503` con un mensaje genérico si la conexión no está configurada o falla.

## Estructura

- `app/routes/`: definición de endpoints HTTP.
- `app/services/`: lógica para comprobar la salud de la API y la base de datos.
- `app/repositories/`: creación del engine y acceso a PostgreSQL.
- `app/models/`: esquemas de respuesta.
- `app/config.py`: configuración cargada desde el entorno o `.env`.