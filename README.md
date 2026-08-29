# portbin

Gestor declarativo de herramientas dev portables en Windows: manifiestos de pasos JSON, shims en `~/.local/bin`, payload en `~/.local/share/portbin/tools`, PATH/variables por registro.

## Estado actual

- Manifests viven dentro del repo (`manifests/`) y se subirán a GitHub; el CLI los resuelve: local → caché → repo (config `repo`, formato `https://raw.githubusercontent.com/USER/REPO/main`).
- `portbin index` regenera `manifests/index.json` (catalogo). Ya ejecutado: 1 tool (composer).
- Config pelistente en `~/.config/portbin/portbin.json` (style XDG) — `scope`, `bin_dir`, `prefix`, `repo`. Estado (registro + caché de manifests) en `~/.config/portbin/`.
- Flag global `-v/--verbose`: imprime detalle de pasos (bytes por chunk de descarga).
- `portbin check`: detalle de plataforma (OS, release, arch, python, exe, admin, temp, bin_dir+contenido, config/scope/repo, registro).
- Comandos: `add`, `update`, `remove`, `list`, `available`, `config`, `index`, `check`.
- Pasos de manifest soportados: `download`, `verify` (sha256 opcional), `extract` (zip/tar, achatilla un solo dir interno), `move`, `copy`, `run` (`capture` → versión; expande `~`), `shim` (genera `.cmd`), `path`, `env`.
- Downloader: en Windows usa `curl.exe` (Schannel, retry 5x + resume `-C -` con fallback si el server no soporta ranges); `urllib`+`truststore` como fallback (un problemático body stall en OpenSSL/urllib).

## Problema pendiente de red

- La red del sandbox frena descargas grandes a mitad (~700 KB) — getcomposer y github stalls; no es código. Reintentar cuando mejore.
- `portbin add composer` nunca completó el ciclo completo tras el refactor (colgado por red/`-C -`; ya se corrigió el fallback de resume). Falta validar instalación real end-to-end.

## Pendientes para mañana (orden)

1. **Validar add composer end-to-end**: `$env:PATH='D:/Users/Kreisler/.local/bin;'+machine+user; uv run python -u -m portbin -v add composer --yes` (config ya apunta a `D:/Users/Kreisler/.local/bin` + prefix). Verificar shim+payload en `D:/Users/Kreisler/.local`, `portbin list`, luego `remove`.
2. **Soporte `7z`** en `src/portbin/extractor.py` (vía `tar.exe`/libarchive en Windows o `py7zr`) para `portbin add ffmpeg` full (`ffmpeg-git-full.7z`).
3. **Manifest ffmpeg** (`manifests/ffmpeg.json`): download essentials `.zip` (recomendado) o full `.7z`, extract a `~/.local/share/portbin/tools/ffmpeg`, shim `ffmpeg`/`ffprobe`/`ffplay`, run capture versión, path `~/.local/bin`. `portbin index` de nuevo (2 tools).
4. **Rebuild exe**: `uv run -- pyinstaller --onefile --name portbin src/portbin/__main__.py` (dist/portbin.exe desactualizado).
5. **Commit**: revisar diff, mensaje en estilo repo.

## Versiones instaladas (D:\LIBS)

Herramientas del sistema `D:\LIBS` — comando y version actual (escaneo 2026-08-28).

| tool       | command             | current        |
|------------|---------------------|----------------|
| java       | `java -version`     | 25.0.2 (LTS)   |
| dotnet     | `dotnet --version`  | 10.0.400       |
| gcc        | `gcc --version`     | 16.2.0         |
| make       | `make --version`    | 4.4.1          |
| yt-dlp     | `yt-dlp --version`  | 2026.08.19     |
| ngrok      | `ngrok version`     | 3.23.3         |
| ffmpeg     | `ffmpeg -version`   | git 2024-11-28 |
| adb        | `adb --version`     | 34.0.4         |
| sdkmanager | `sdkmanager --version` | 19.0        |
| flutter    | `flutter --version` | 3.41.4         |
| scrcpy     | `scrcpy --version`  | 3.3.3          |
| cmake      | `cmake --version`   | 4.2.1          |
| go         | `go version`        | 1.26.6         |
| composer   | `composer --version`| 2.5.3          |
| fresh      | `fresh --version`   | 0.4.10         |
| w64devkit  | `w64devkit --version` | 2.9.1        |

## ffmpeg (instalación manual, alternativa a manifest)

El marco de pasos aún no cubre `7z` (URL full es `ffmpeg-git-full.7z`); el build `essentials` es `.zip` y sí entra como manifest, pero la descarga a gyan.dev no responde en este entorno. Mientras tanto, setup manual:

1. Elegir paquete apropiado en https://www.gyan.dev/ffmpeg/builds/:
   - `ffmpeg-release-essentials.zip` — funcionalidad básica (recomendado)
   - `ffmpeg-release-full.zip` — feature set completo
   - `ffmpeg-release-shared.zip` — librerías compartidas
2. Extraer el ZIP a ubicación permanente (p. ej. `C:\ffmpeg`).
3. Agregar FFmpeg al PATH del sistema:
   1. Propiedades del sistema (clic derecho en "Este equipo" → Propiedades)
   2. Configuración avanzada del sistema
   3. Variables de entorno
   4. En variables de sistema seleccionar `Path` y clic en Editar
   5. Agregar nueva entrada: `C:\ffmpeg\bin` (ajustar ruta si necesario)
   6. Aceptar en todas las ventanas