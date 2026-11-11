# Verificación de calidad del backend

## Evidencia reproducible

Comando usado:

```bash
python -m pytest
```

Resultado medido el 2026-11-11:

```text
46 passed
Total de líneas de app/services/: 94.65%
Umbral configurado: 80%
Cobertura de ramas activada: sí (--cov-branch)
Informe HTML: htmlcov/index.html
```

La suite incluye tests de mascotas, autenticación, autorización, solicitudes,
historial, health, errores HTTP e inventario OpenAPI. Pytest genera la tabla de
cobertura cada ejecución y falla bajo el 80 % de cobertura de líneas de
`app/services/`; los comandos del README permiten reproducir HTML y XML.
El informe HTML y `.coverage` son artefactos generados localmente y están
ignorados por Git para que no se publique una medición desactualizada.

Cobertura de líneas por módulo de servicio medida en esa ejecución:

| Módulo | Líneas |
|---|---:|
| `auth.py` | 93 % |
| `health.py` | 100 % |
| `historial.py` | 96 % |
| `mascotas.py` | 100 % |
| `policies.py` | 97 % |
| `solicitudes.py` | 90 % |
| **Total** | **94.65 %** |

La persistencia de repositorios se prueba con SQLite en memoria. No se afirma
haber ejecutado una prueba real contra PostgreSQL; se requiere una instancia de
prueba para esa evidencia.

## Inventario y paridad con Express

El inventario esperado en OpenAPI se verifica automáticamente: 18 operaciones
HTTP en 11 rutas (incluye health, auth y los ocho endpoints de negocio).
Los ocho endpoints de solicitudes e historial existen en ambos backends.
La envoltura exitosa y la estructura base de errores (`success`, `status`,
`message`, `error.message`) coinciden.

| Área | Express (B-Profesional) | FastAPI (B-Personal) | Estado / diferencia |
|---|---|---|---|
| Solicitudes | GET/POST `/api/solicitudes`; GET/PUT `/api/solicitudes/{id}` | Mismos métodos y rutas | Paridad funcional. Ambos limitan listados de ADOPTANTE a solicitudes propias y reservan el cambio de estado a ADMIN. FastAPI incluye `count` en el listado. |
| Historial | GET/POST `/api/mascotas/{id}/historial`; PUT/DELETE `/api/historial/{id}` | Mismas rutas y métodos | Paridad funcional. FastAPI incluye `count` en listados y valida fechas con Pydantic; un PUT vacío es `400`, mientras Express lo trata como no-op `200`. |
| Mascotas | CRUD `/api/mascotas` | Mismas rutas | Diferencia deliberada de seguridad: B-Personal exige ADMIN para escrituras por las reglas B4; Express documenta las rutas de escritura sin autenticación. DELETE responde `204` vacío en FastAPI y `200` con el recurso eliminado en Express. |
| Autenticación | POST `/api/auth/login`; GET `/api/auth/validate-token`, `/admin-only`, `/adoptante-only` | POST `/api/auth/register`, `/login`; GET `/api/auth/me` | `/me` cubre la consulta del usuario autenticado, pero no conserva los nombres de ruta de validate-token. B-Personal agrega registro; los endpoints demostrativos de rol de Express no existen en B-Personal. |
| Health | GET `/health`; GET `/api/db-check` | GET `/health`; GET `/health/db` | La comprobación de proceso coincide. El endpoint de DB tiene distinta ruta y respuesta: Express usa `available`/`databaseTime`; FastAPI usa `status` y responde `503` si no está disponible. |
| Errores | Envelope común con `success`, `status`, `message`, `error.message` | Mismo envelope; validación agrega `errors` sin valores de entrada | Coincidencia base; los detalles adicionales de validación son específicos de FastAPI. |

Las diferencias de rutas/respuestas de mascotas, auth y health quedan
documentadas para que los consumidores decidan si requieren un ajuste coordinado
del contrato. No se cambiaron en esta tarea para evitar alterar contratos o
reglas de autorización fuera del alcance.

## Revisión estática

- **SQL:** los valores de entrada se enlazan como parámetros SQLAlchemy. En la
  actualización dinámica de mascotas, nombres de columnas proceden de una
  allowlist fija (`_UPDATE_COLUMNS`); no se interpolan valores de usuario en SQL.
- **Secretos:** no se encontraron credenciales, JWT ni claves privadas en el
  código de producción. `DATABASE_URL` y `JWT_SECRET` se leen de entorno; los
  tests usan SQLite temporal y claves efímeras.
- **Depuración:** no se encontraron `print`, `pdb`, `debugger` ni llamadas
  `console.*` en `app/`.
- **Capas:** rutas, servicios, repositorios y modelos están separados en
  carpetas convencionales.
- **Datos de autenticación:** las respuestas OpenAPI de usuario/token no
  contienen `password` ni `password_hash`; un test lo comprueba.
- **Docker:** imagen no-root y `.env` excluido del contexto de build. La prueba
  no requiere credenciales reales.

## Problemas detectados y tratados

1. La suite anterior usaba `unittest` y no medía cobertura. Se agregó pytest,
   pytest-cov, cobertura por ramas y umbral de 80 % sobre services.
2. No había una prueba automatizada que asegurara que el inventario HTTP del
   contrato apareciera completo en OpenAPI. Se agregó una verificación exacta
   de rutas y métodos.
3. Las ramas de health, hash de contraseña malformado y configuración de JWT
   no tenían cobertura específica. Se agregaron tests sin usar credenciales
   persistentes.
4. No se encontró SQL por concatenación de datos, secretos de producción ni
   instrucciones de depuración durante la revisión estática.
