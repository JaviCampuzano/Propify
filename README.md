# gestorRecibosAlquiler

Aplicacion web para gestionar alquileres, registrar gastos y controlar el estado de cobro de cada inquilino.

## Stack actual

- `FastAPI` como backend web
- `Jinja2` para la plantilla inicial
- `HTML/CSS/JavaScript` para la interfaz
- Persistencia en `datos_v2.json`, con migracion automatica desde `datos.json`

## Arranque

1. Instala dependencias:

```bash
pip3 install -r requirements.txt
```

2. Inicia el servidor:

```bash
uvicorn app:app --reload
```

3. Abre la aplicacion en:

```text
http://127.0.0.1:8000
```

## Funcionalidades ya preparadas

- Dashboard con metricas del mes
- Alta y edicion de propiedades
- Alta, edicion y borrado de inquilinos
- Marcado de pagos mensuales como cobrados
- Registro de gastos
- Configuracion basica del propietario
- Compatibilidad con datos antiguos de la version de escritorio

## Scripts de comprobacion

```bash
python3 verify_logic.py
python3 verify_v2.py
python3 verify_migration.py
```
