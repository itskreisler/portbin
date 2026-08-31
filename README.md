# portbin

Gestor declarativo de herramientas de desarrollo portables para Windows. Define cada herramienta como un **manifest** de pasos JSON; `portbin` los ejecuta, instala el payload, crea shims y configura el entorno automáticamente.

## Características

- **Manifests en JSON** — secuencia declarativa de pasos: `download`, `verify`, `extract`, `move`, `run`, `shim`, `path`, `env`.
- **Organización por plataforma** — los manifests viven en `manifests/<tool>/<plataforma>.json` (`win32`, `linux`, `darwin`, `universal`).
- **Índice autocontenido** — `portbin index` regenera `manifests/index.json` como un array con todos los manifests y su contenido embebido, listo para servirse por URL y consumirse sin descargar archivos individuales.
- **Modo desarrollo y producción** — en fuente usa los manifests locales; compilado (`.exe`) resuelve únicamente el índice remoto vía `repo` de configuración.
- **Validación de esquema** — Pydantic valida cada manifest al cargarlo y al generar el índice; `portbin manifest-schema` imprime el JSON Schema como guía.
- **Checksums** — verificación SHA-256 opcional por paso `verify`.
- **Shims `.cmd`** — binarios portables expuestos en `~/.local/bin`.
- **Resolución de red** — `curl.exe` (Schannel, reintentos + resume) con fallback `urllib` + `truststore`.

## Instalación

```sh
# Desde el código fuente
uv sync
uv run python -m portbin --help
```

Consultar `--help` para la lista completa de comandos y opciones.

## Uso

```sh
# Ver herramientas disponibles en el índice
portbin available

# Instalar una herramienta
portbin add fresh --yes

# Reinstalar / actualizar
portbin update fresh

# Listar herramientas registradas (con versión y estado)
portbin list

# Desinstalar
portbin remove fresh

# Regenerar el índice desde los manifests locales
portbin index

# Imprimir el JSON Schema de un manifest
portbin manifest-schema

# Estado del entorno
portbin check
```

## Comandos

| Comando           | Descripción                                        |
|-------------------|----------------------------------------------------|
| `add <tool>`      | Instala una herramienta desde su manifest          |
| `update <tool>`   | Reinstala una herramienta                          |
| `remove <tool>`   | Desinstala una herramienta                         |
| `list`            | Lista herramientas registradas                     |
| `available`       | Lista manifests disponibles                        |
| `config`          | Muestra o fija la configuración (`--scope`, `--bin-dir`, `--prefix`, `--repo`) |
| `index`           | Regenera `manifests/index.json`                    |
| `manifest-schema` | Imprime el JSON Schema de un manifest              |
| `check`           | Muestra estado del entorno                         |

Flags globales: `-v/--verbose` (detalle de pasos), `-h/--help`.

## Añadir una herramienta

1. Crear `manifests/<tool>/<plataforma>.json` siguiendo el esquema (`portbin manifest-schema`).
2. Pasos típicos: `download` → `verify` (sha256) → `extract`/`move` → `shim` → `run` (captura versión) → `path`.
3. Ejecutar `portbin index` para incluirla en el catálogo.
4. `portbin add <tool>` para instalarla.

## Configuración

Persistida en `~/.config/portbin/portbin.json` (estilo XDG). Estado de instalación (registro + caché de manifests) en `~/.config/portbin/`.

| Clave      | Descripción                                        |
|------------|----------------------------------------------------|
| `scope`    | Alcance por defecto: `user` o `machine`            |
| `bin_dir`  | Directorio de shims (default `~/.local/bin`)       |
| `prefix`   | Raíz de payload (default `~/.local/share/portbin/tools`) |
| `repo`     | Base URL del índice remoto (raw GitHub)            |

Si `repo` está vacío, se usa el valor por defecto apuntando al catálogo de `itskreisler/portbin`.

## Versiones instaladas

Herramientas presentes en el sistema — comando de versión, versión actual (escaneo 2026-08-28) y si están indexadas en el catálogo de portbin.

| tool       | command             | current        | indexado |
|------------|---------------------|----------------|----------|
| java       | `java -version`     | 25.0.2 (LTS)   | ✗        |
| dotnet     | `dotnet --version`  | 10.0.400       | ✗        |
| gcc        | `gcc --version`     | 16.2.0         | ✗        |
| make       | `make --version`    | 4.4.1          | ✗        |
| yt-dlp     | `yt-dlp --version`  | 2026.08.19     | ✗        |
| ngrok      | `ngrok version`     | 3.23.3         | ✗        |
| ffmpeg     | `ffmpeg -version`   | git 2024-11-28 | ✓        |
| adb        | `adb --version`     | 34.0.4         | ✗        |
| sdkmanager | `sdkmanager --version` | 19.0        | ✗        |
| flutter    | `flutter --version` | 3.41.4         | ✗        |
| scrcpy     | `scrcpy --version`  | 3.3.3          | ✗        |
| cmake      | `cmake --version`   | 4.2.1          | ✗        |
| go         | `go version`        | 1.26.6         | ✗        |
| composer   | `composer --version`| 2.5.3          | ✓        |
| fresh      | `fresh --version`   | 0.4.10         | ✓        |

**Leyenda**: `✓` indexado en `manifests/index.json` · `✗` pendiente de manifest.

## Licencia

MIT
