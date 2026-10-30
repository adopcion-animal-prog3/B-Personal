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
contenga el esquema compartido de `mascotas` definido en `B-Profesional/init.sql`.
Sin conexión configurada, los endpoints de mascotas responden `503`.

La documentación interactiva está disponible en `/docs`.

## Pruebas

```bash
pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

Las pruebas HTTP usan un repositorio doble; las pruebas del repositorio verifican
persistencia en SQLite en memoria. Para comprobar PostgreSQL se necesita una base
de pruebas configurada por separado.
