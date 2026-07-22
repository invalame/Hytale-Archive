# Hytale Archive Project

Un archivo automatizado para preservar el ecosistema de Hytale (mods, noticias, arte) frente a la volatilidad de las plataformas web.

## Estructura del Repositorio (¡Importante para editar!)

Este proyecto es híbrido: una parte la editas tú (el humano) y otra parte la edita el Bot de GitHub Actions automáticamente cada semana. Para evitar conflictos, respeta estas "zonas":

### 👨‍💻 Zona Humana (Puedes editar libremente)
*Tus cambios aquí no serán sobreescritos por el bot.*

- **Código de los scrapers**: `scraper_curseforge.py`, `scraper_hytale_blog.py`, `crawler_core.py`, `run_all.py`.
- **Estructura de la base de datos**: `schema.sql`, `db_manager.py`.
- **Configuración de GitHub**: `.github/workflows/run_all.yml`
- **Este archivo**: `README.md`

*(Si editas algo aquí y haces git push, el bot simplemente bajará tu nuevo código antes de correr su próxima tarea).*

### 🤖 Zona del Bot (NO TOCAR MANUALMENTE)
*El bot actualiza estos archivos cada semana. Si los modificas a mano, podrías causar conflictos en GitHub Actions.*

- **La Base de Datos**: `archivo_hytale.db` (El bot extrae nuevos datos e inserta filas aquí).
- **Archivos Descargados**: Carpeta `archivo_data/` (Aquí el bot guarda los `.zip` e imágenes pesadas).
- **El Catálogo Web (Próximamente)**: Cualquier archivo `index.html` o `.json` generado a partir de la DB.

## Cómo agregar nuevos scrapers (ej. Reddit)

1. Escribe tu nuevo scraper (ej. `scraper_reddit.py`).
2. Agrega una entrada en la lista `SCRAPERS` al principio del archivo `run_all.py`.
3. Sube los cambios con `git push`. El bot usará tu nuevo scraper en su siguiente corrida dominical.
