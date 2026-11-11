# B-Personal

API personal de adopción implementada con FastAPI y SQLAlchemy.

## Ejecución local

Crear un entorno virtual, instalar las dependencias e iniciar la API:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Configurar `DATABASE_URL` en `.env` con una conexión PostgreSQL a la base que
contenga el esquema compartido definido en `B-Profesional/init.sql`.
Sin conexión configurada, los endpoints de mascotas responden `503`.

Para autenticación, configurar `JWT_SECRET` con una clave aleatoria de al menos
32 bytes y, opcionalmente, `JWT_EXPIRATION_MINUTES` (60 por defecto). El registro
usa el rol `ADOPTANTE` definido por el esquema compartido. Los endpoints son
`POST /api/auth/register`, `POST /api/auth/login` y `GET /api/auth/me`.

Las lecturas de mascotas siguen siendo públicas; crear, actualizar o eliminar
mascotas requiere un usuario `ADMIN`. Las solicitudes requieren autenticación: ADMIN puede consultar todas y
ADOPTANTE solo las propias; la creación asocia el usuario autenticado y solo
admite mascotas disponibles. Solo ADMIN cambia el estado. `PENDIENTE` puede
permanecer pendiente o pasar a `APROBADA`/`RECHAZADA`; esos estados son finales.
El historial clínico está restringido a ADMIN y sus operaciones verifican la
existencia de la mascota asociada. Las rutas implementadas son:

- `GET /api/solicitudes` y `GET /api/solicitudes/{id}`
- `POST /api/solicitudes` con `mascota_id` y `mensaje` opcional
- `PUT /api/solicitudes/{id}` con `estado`
- `GET|POST /api/mascotas/{id}/historial`
- `PUT|DELETE /api/historial/{id}`

Las respuestas exitosas usan el envelope común `{success, status, data}` y
las listas incluyen `count`. Los cuerpos inválidos responden `400`; los
recursos no existentes, `404`; y los accesos no autorizados, `401`/`403`.
`DELETE /api/historial/{id}` responde `200` con el mensaje de eliminación y
el registro eliminado dentro de `data`.

Ejemplos de cuerpos y respuestas:

```http
POST /api/solicitudes
Authorization: Bearer <token>
Content-Type: application/json

{"mascota_id": 1, "mensaje": "Quisiera adoptar a Luna"}
```

```json
{
  "success": true,
  "status": "success",
  "data": {
    "id": 1,
    "usuario_id": 2,
    "mascota_id": 1,
    "estado": "PENDIENTE",
    "mensaje": "Quisiera adoptar a Luna",
    "created_at": "2026-04-03T10:30:00Z",
    "updated_at": null
  }
}
```

```http
POST /api/mascotas/1/historial
Authorization: Bearer <token-de-admin>
Content-Type: application/json

{"descripcion": "Vacunación anual", "veterinario": "Dra. Torres"}
```

Esta ruta responde `201` con el mismo envelope y un objeto `data` con
`mascota_id`, `fecha_registro`, `descripcion`, `veterinario`, `created_at` y
`updated_at`.

La documentación interactiva está disponible en `/docs`.

## Contrato de errores HTTP

Las respuestas de error mantienen el contrato común usado por Express:

```json
{
  "success": false,
  "status": "error",
  "message": "Invalid request data",
  "error": {"message": "Invalid request data"},
  "errors": [{"field": "body.email", "message": "email is invalid"}]
}
```

`errors` solo se incluye para validaciones y no contiene los valores recibidos.
Los errores inesperados responden `500` con el mensaje genérico
`Internal server error`; los detalles internos se excluyen del cuerpo y de los
logs. El mapeo HTTP es `400` para validación/reglas de negocio, `401` para
autenticación, `403` para permisos, `404` para recursos inexistentes, `409`
para conflictos, y `503` para indisponibilidad de base de datos o configuración
de autenticación. Los endpoints y esquemas de errores están documentados en
OpenAPI (`/openapi.json`) y Swagger UI (`/docs`).

Este envelope coincide con el `errorResponse` del backend Express compartido:
ambos devuelven `success`, `status`, `message` y `error.message`; FastAPI agrega
`errors` únicamente con detalles de validación.

## Docker

La imagen contiene únicamente la API; PostgreSQL debe estar disponible con el
esquema compartido. Copiar y configurar el archivo de entorno antes de iniciar
el contenedor:

```bash
cp .env.example .env
# Configure DATABASE_URL y JWT_SECRET (al menos 32 bytes).
docker compose up --build
```

La API queda disponible en `http://localhost:8000` y la documentación en
`http://localhost:8000/docs`. Para una base PostgreSQL que corre en el host, se
puede usar `host.docker.internal` como hostname en `DATABASE_URL`; Compose
configura ese alias también en Linux. No se incluyen credenciales ni secretos
en la imagen y el proceso del contenedor se ejecuta sin privilegios de root.

## Pruebas

```bash
pip install -r requirements-dev.txt
python -m pytest
```

Pytest ejecuta la suite, mide cobertura de líneas y ramas para `app.services`,
falla si es menor al 80 % y genera `htmlcov/index.html`. Para guardar también un
informe XML reproducible para CI:

```bash
python -m pytest --cov-report=xml:coverage.xml
```

Las pruebas HTTP verifican el envelope de errores, códigos HTTP, documentación
OpenAPI, permisos y validaciones. Las pruebas del repositorio verifican
persistencia en SQLite en memoria. Para comprobar PostgreSQL se necesita una
base de pruebas configurada por separado. Resultados, paridad con Express y
revisión de calidad están en [docs/VERIFICACION_CALIDAD.md](./docs/VERIFICACION_CALIDAD.md).
