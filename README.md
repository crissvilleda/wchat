# wchatv0

Backend API for Wchat, built with [FastAPI](https://fastapi.tiangolo.com) and deployed on [Azure Functions](https://learn.microsoft.com/en-us/azure/azure-functions/).

---

## English

Follow these steps in order. Don't skip any — each one is required before the next.

---

### Step 1 — Install Python 3.13+

If you don't have Python 3.13 or newer installed, download and install it from [https://python.org](https://python.org).

To verify the installation, open a terminal and run:

```bash
python --version
```

It should print `Python 3.13.x` or higher.

---

### Step 2 — Install uv

This project uses [uv](https://docs.astral.sh/uv/) as its package manager.

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Verify the installation:

```bash
uv --version
```

---

### Step 3 — Clone the repository

```bash
git clone <repository-url>
cd wchatv0
```

Replace `<repository-url>` with the actual URL of this repository.

---

### Step 4 — Install project dependencies

Inside the project folder, run:

```bash
uv sync
```

This creates a virtual environment and installs all required packages. It may take a minute or two.

---

### Step 5 — Install dotenvx

This project uses [dotenvx](https://dotenvx.com) to handle encrypted environment variables. You need to install it once on your machine.

Pick the method that works best for you:

```bash
# Option A — npm (recommended if you already have Node.js)
npm install @dotenvx/dotenvx --global

# Option B — Homebrew (macOS / Linux)
brew install dotenvx/brew/dotenvx

# Option C — curl
curl -sfS https://dotenvx.sh | sh
```

> For Windows (WinGet) or Docker, see the [full install docs](https://dotenvx.com/docs/install).

Verify the installation:

```bash
dotenvx --version
```

---

### Step 6 — Set up the environment file

The repository includes an encrypted file called `.env.encrypted`. You need to rename it to `.env` so the app can read it:

```bash
mv .env.encrypted .env
```

> On Windows (Command Prompt): `rename .env.encrypted .env`

---

### Step 7 — Get the private key file

The `.env` file is encrypted and cannot be read without a private key file called `.env.keys`.

**Ask a team member privately (via direct message) for the `.env.keys` file. Never share it in a chat group, email, or public channel, and never commit it to the repository.**

Once you receive it, place the file in the root of the project folder (same level as `pyproject.toml`). The file is already listed in `.gitignore` so it will never be accidentally committed.

---

### Step 8 — Run the development server

**Option A — Azure Functions (recommended, matches production):**

Make sure you have [Azure Functions Core Tools](https://learn.microsoft.com/en-us/azure/azure-functions/functions-run-local) installed, then run:

```bash
dotenvx run -- func start
```

The API will be available at `http://localhost:7071/api/`.

**Option B — FastAPI dev server (quick iteration):**

```bash
dotenvx run -- uv run uvicorn api.app:fastapi_app --reload --port 8000
```

The API will be available at `http://localhost:8000/`.

---

### Other useful commands

```bash
# Run tests
dotenvx run -- uv run pytest

# Run tests with verbose output
dotenvx run -- uv run pytest -v

# Run a specific test file
dotenvx run -- uv run pytest tests/test_whatsapp_webhook.py

# Run the linter
dotenvx run -- uv run ruff check .

# Format code
dotenvx run -- uv run ruff format .
```

---
---

## Español

Sigue estos pasos en orden. No omitas ninguno — cada uno es necesario antes del siguiente.

---

### Paso 1 — Instalar Python 3.13+

Si aún no tienes Python 3.13 o superior, descárgalo desde [https://python.org](https://python.org).

Para verificar la instalación, abre una terminal y ejecuta:

```bash
python --version
```

Debe mostrar `Python 3.13.x` o superior.

---

### Paso 2 — Instalar uv

Este proyecto usa [uv](https://docs.astral.sh/uv/) como gestor de paquetes.

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Verifica la instalación:

```bash
uv --version
```

---

### Paso 3 — Clonar el repositorio

```bash
git clone <url-del-repositorio>
cd wchatv0
```

Reemplaza `<url-del-repositorio>` con la URL real de este repositorio.

---

### Paso 4 — Instalar las dependencias del proyecto

Dentro de la carpeta del proyecto, ejecuta:

```bash
uv sync
```

Esto crea un entorno virtual e instala todos los paquetes necesarios. Puede tardar uno o dos minutos.

---

### Paso 5 — Instalar dotenvx

Este proyecto usa [dotenvx](https://dotenvx.com) para manejar variables de entorno cifradas. Necesitas instalarlo una vez en tu máquina.

Elige la opción que mejor te funcione:

```bash
# Opción A — npm (recomendado si ya tienes Node.js)
npm install @dotenvx/dotenvx --global

# Opción B — Homebrew (macOS / Linux)
brew install dotenvx/brew/dotenvx

# Opción C — curl
curl -sfS https://dotenvx.sh | sh
```

> Para Windows (WinGet) o Docker, consulta la [documentación completa de instalación](https://dotenvx.com/docs/install).

Verifica la instalación:

```bash
dotenvx --version
```

---

### Paso 6 — Configurar el archivo de entorno

El repositorio incluye un archivo cifrado llamado `.env.encrypted`. Necesitas renombrarlo a `.env` para que la aplicación pueda leerlo:

```bash
mv .env.encrypted .env
```

> En Windows (Símbolo del sistema): `rename .env.encrypted .env`

---

### Paso 7 — Obtener el archivo de llaves privadas

El archivo `.env` está cifrado y no puede leerse sin un archivo de llaves privadas llamado `.env.keys`.

**Solicita el archivo `.env.keys` de forma privada a un miembro del equipo (por mensaje directo). Nunca lo compartas en grupos de chat, correo público o canales abiertos, y nunca lo subas al repositorio.**

Una vez que lo recibas, colócalo en la raíz del proyecto (al mismo nivel que `pyproject.toml`). El archivo ya está en `.gitignore`, así que nunca se subirá accidentalmente.

---

### Paso 8 — Correr el servidor de desarrollo

**Opción A — Azure Functions (recomendado, igual que producción):**

Asegúrate de tener [Azure Functions Core Tools](https://learn.microsoft.com/en-us/azure/azure-functions/functions-run-local) instalado, luego ejecuta:

```bash
dotenvx run -- func start
```

La API estará disponible en `http://localhost:7071/api/`.

**Opción B — Servidor FastAPI (iteración rápida):**

```bash
dotenvx run -- uv run uvicorn api.app:fastapi_app --reload --port 8000
```

La API estará disponible en `http://localhost:8000/`.

---

### Otros comandos útiles

```bash
# Correr las pruebas
dotenvx run -- uv run pytest

# Correr pruebas con salida detallada
dotenvx run -- uv run pytest -v

# Correr un archivo de pruebas específico
dotenvx run -- uv run pytest tests/test_whatsapp_webhook.py

# Correr el linter
dotenvx run -- uv run ruff check .

# Formatear el código
dotenvx run -- uv run ruff format .
```
