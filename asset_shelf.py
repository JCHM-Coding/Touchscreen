import bpy
import os
import re
import json
import hashlib
from pathlib import Path
from bpy.app.handlers import persistent


# ============================================================
# TOUCHSCREEN - BRUSH ASSET SHELF (SIDEBAR PANEL)
# Blender 5.3 Alpha — 3D View, Image Editor, and Grease Pencil contexts
# ============================================================

ASSET_CACHE = []
CATALOG_ITEMS = {}
CATALOG_ENUM_ITEMS = []
CACHE_MODE = None
ASSETS_LOADED = False

BRUSH_ENUM_ITEMS = []
BRUSH_ENUM_MAP = {}
FAVORITE_KEYS = set()
FAVORITES_LOADED = False

# Nombres de brochas que ESTE add-on ha importado desde librerías.
# Solo estas se consideran "gestionadas" a efectos de limpieza:
# nunca se tocan las brochas creadas por el usuario.
LIBRARY_LOADED_BRUSHES = set()

MODE_SETTINGS = {
    'SCULPT': {
        "label": "Sculpting",
        "brush_flag": "use_paint_sculpt",
    },
    'PAINT_TEXTURE': {
        "label": "Texture Paint",
        "brush_flag": "use_paint_image",
    },
    'PAINT_VERTEX': {
        "label": "Vertex Paint",
        "brush_flag": "use_paint_vertex",
    },
    'PAINT_WEIGHT': {
        "label": "Weight Paint",
        "brush_flag": "use_paint_weight",
    },
}


# ============================================================
# NAMES AND UTILITIES
# ============================================================

def normalize_brush_name(value):
    if value is None:
        return ""
    if isinstance(value, str):
        text = value.strip()
        if "bpy_struct" in text and "Brush(" in text:
            match = re.search(r'Brush\("((?:\\.|[^"\\])*)"\)', text)
            if match:
                return match.group(1).replace('\\"', '"').replace("\\\\", "\\")
        return text

    try:
        name = value.name
        if name is not None:
            return str(name)
    except (AttributeError, ReferenceError, RuntimeError):
        pass

    text = str(value)
    match = re.search(r'Brush\("((?:\\.|[^"\\])*)"\)', text)
    if match:
        return match.group(1).replace('\\"', '"').replace("\\\\", "\\")
    return text


def normalize_string(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    try:
        if hasattr(value, "name"):
            return str(value.name)
    except (ReferenceError, RuntimeError):
        pass
    return str(value)


def get_asset_shelf_preferences():
    """Return the parent Touchscreen add-on preferences, if available."""
    try:
        addon = bpy.context.preferences.addons.get(__package__)
        if addon is not None:
            return addon.preferences
    except (AttributeError, ReferenceError, RuntimeError):
        pass
    return None


def get_asset_shelf_scale():
    """Read thumbnail scales from Touchscreen Preferences."""
    prefs = get_asset_shelf_preferences()
    if prefs is None:
        return 4.0, 2.2
    try:
        return float(prefs.asset_shelf_scale), float(prefs.asset_shelf_scale_popup)
    except (AttributeError, TypeError, ValueError):
        return 4.0, 2.2


GREASE_PENCIL_MODES = {
    'PAINT_GREASE_PENCIL',
    'SCULPT_GREASE_PENCIL',
    'WEIGHT_GREASE_PENCIL',
    'VERTEX_GREASE_PENCIL',
    'PAINT_GPENCIL',
    'SCULPT_GPENCIL',
    'WEIGHT_GPENCIL',
    'VERTEX_GPENCIL',
}


# Catalog terms used to filter custom Grease Pencil libraries by active mode.
GREASE_PENCIL_MODE_TERMS = {
    "DRAW_GREASE_PENCIL": ("grease pencil draw", "grease pencil drawing"),
    "PAINT_GREASE_PENCIL": ("grease pencil draw", "grease pencil drawing"),
    "VERTEX_GREASE_PENCIL": (
        "grease pencil paint", "grease pencil vertex paint", "grease pencil vertex"
    ),
    "SCULPT_GREASE_PENCIL": ("grease pencil sculpt",),
    "WEIGHT_GREASE_PENCIL": ("grease pencil weight paint",),
    "PAINT_GPENCIL": ("grease pencil draw", "grease pencil drawing"),
    "VERTEX_GPENCIL": (
        "grease pencil paint", "grease pencil vertex paint", "grease pencil vertex"
    ),
    "SCULPT_GPENCIL": ("grease pencil sculpt",),
    "WEIGHT_GPENCIL": ("grease pencil weight paint",),
}


def normalize_search_text(value):
    """Normalize catalog labels and paths, including slash-separated categories."""
    value = normalize_string(value).casefold()
    value = re.sub(r"[_/\\:.-]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def grease_pencil_entry_matches(entry, context):
    """Filter GP brushes by the active mode and their Essentials file/catalog."""
    mode = getattr(context, "mode", "")
    filename = Path(normalize_string(entry.get("source_file", ""))).name.casefold()

    # FIX: nombres reales de los ficheros Essentials de Grease Pencil
    # (gp_draw, gp_sculpt, gp_vertex, gp_weight — no *_paint).
    essentials_mode_files = {
        "DRAW_GREASE_PENCIL": ("essentials_brushes-gp_draw",),
        "PAINT_GREASE_PENCIL": ("essentials_brushes-gp_draw",),
        "VERTEX_GREASE_PENCIL": ("essentials_brushes-gp_vertex",),
        "SCULPT_GREASE_PENCIL": ("essentials_brushes-gp_sculpt",),
        "WEIGHT_GREASE_PENCIL": ("essentials_brushes-gp_weight",),
        "PAINT_GPENCIL": ("essentials_brushes-gp_draw",),
        "VERTEX_GPENCIL": ("essentials_brushes-gp_vertex",),
        "SCULPT_GPENCIL": ("essentials_brushes-gp_sculpt",),
        "WEIGHT_GPENCIL": ("essentials_brushes-gp_weight",),
    }

    if entry.get("asset_type") == "ESSENTIALS" and filename:
        expected = essentials_mode_files.get(mode, ())
        all_known = tuple(stem for stems in essentials_mode_files.values() for stem in stems)
        if any(filename.startswith(stem) for stem in expected):
            return True
        if any(filename.startswith(stem) for stem in all_known):
            return False

    terms = GREASE_PENCIL_MODE_TERMS.get(mode, ())
    if not terms:
        return False

    catalog_info = CATALOG_ITEMS.get(entry.get("catalog_key", ""), {})
    searchable = normalize_search_text(" ".join((
        normalize_string(catalog_info.get("name", "")),
        normalize_string(catalog_info.get("simple_name", "")),
        normalize_string(catalog_info.get("path", "")),
    )))
    return any(term in searchable for term in terms)


def get_mode_info(context):
    return MODE_SETTINGS.get(context.mode)


def is_grease_pencil_mode(context):
    return bool(context and context.mode in GREASE_PENCIL_MODES)


def get_selected_catalog(context):
    try:
        return context.window_manager.ts_brush_catalog
    except (AttributeError, TypeError):
        return "__ALL__"


def get_search_text(context):
    try:
        return context.window_manager.ts_brush_search.strip()
    except (AttributeError, TypeError):
        return ""


def make_catalog_key(asset_type, library_identifier, catalog_uuid):
    return f"{asset_type}|{library_identifier}|{catalog_uuid}"


def get_active_brush(context):
    """Return the active brush for regular paint and Grease Pencil modes."""
    try:
        ts = context.tool_settings
        if not ts:
            return None

        mode = getattr(context, "mode", "")
        regular_settings = {
            "SCULPT": "sculpt",
            "PAINT_TEXTURE": "image_paint",
            "PAINT_VERTEX": "vertex_paint",
            "PAINT_WEIGHT": "weight_paint",
        }
        settings_name = regular_settings.get(mode)
        if settings_name:
            settings = getattr(ts, settings_name, None)
            return getattr(settings, "brush", None) if settings else None

        gp_settings_by_mode = {
            "DRAW_GREASE_PENCIL": ("gpencil_paint", "gpencil_draw"),
            "PAINT_GREASE_PENCIL": ("gpencil_paint", "gpencil_draw"),
            "VERTEX_GREASE_PENCIL": ("gpencil_vertex_paint", "gpencil_paint"),
            "SCULPT_GREASE_PENCIL": ("gpencil_sculpt_paint", "gpencil_sculpt"),
            "WEIGHT_GREASE_PENCIL": ("gpencil_weight_paint",),
            "PAINT_GPENCIL": ("gpencil_paint",),
            "VERTEX_GPENCIL": ("gpencil_vertex_paint", "gpencil_paint"),
            "SCULPT_GPENCIL": ("gpencil_sculpt_paint", "gpencil_sculpt"),
            "WEIGHT_GPENCIL": ("gpencil_weight_paint",),
        }
        for candidate in gp_settings_by_mode.get(mode, ()):
            settings = getattr(ts, candidate, None)
            brush = getattr(settings, "brush", None) if settings else None
            if brush is not None:
                return brush
    except (AttributeError, ReferenceError, RuntimeError, TypeError):
        pass
    return None


# ============================================================
# PERSISTENT FAVORITES
# ============================================================

def favorites_file_path():
    try:
        config_dir = bpy.utils.user_resource('CONFIG', path="touchscreen_asset_shelf", create=True)
        if config_dir:
            return Path(config_dir) / "favorites.json"
    except (AttributeError, RuntimeError, TypeError):
        pass
    return Path.home() / ".touchscreen_asset_shelf_favorites.json"


def favorite_key(entry):
    return json.dumps(
        [
            normalize_string(entry.get("asset_type", "")),
            normalize_string(entry.get("asset_identifier", "")),
            normalize_string(entry.get("relative_identifier", "")),
        ],
        ensure_ascii=False,
        separators=(",", ":"),
    )


def load_favorites():
    global FAVORITE_KEYS, FAVORITES_LOADED
    if FAVORITES_LOADED:
        return
    FAVORITE_KEYS = set()
    path = favorites_file_path()
    try:
        if path.is_file():
            data = json.loads(path.read_text(encoding="utf-8"))
            values = data.get("favorites", []) if isinstance(data, dict) else []
            FAVORITE_KEYS = {str(value) for value in values if value}
    except (OSError, ValueError, TypeError):
        pass
    FAVORITES_LOADED = True


def save_favorites():
    path = favorites_file_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"version": 1, "favorites": sorted(FAVORITE_KEYS)}
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except (OSError, TypeError, ValueError):
        return False


def is_favorite(entry):
    load_favorites()
    return favorite_key(entry) in FAVORITE_KEYS


# ============================================================
# REDRAW & CATALOGS
# ============================================================

def tag_view3d_redraw():
    try:
        wm = bpy.context.window_manager
        if wm is None:
            return
        for window in wm.windows:
            screen = window.screen
            if screen is None:
                continue
            for area in screen.areas:
                if area.type in {'VIEW_3D', 'IMAGE_EDITOR'}:
                    area.tag_redraw()
    except (AttributeError, ReferenceError, RuntimeError):
        pass


def on_brush_search_update(self, context):
    tag_view3d_redraw()


def on_catalog_update(self, context):
    if context is None:
        return
    try:
        wm = context.window_manager
        ensure_assets_loaded(context)
        assets = get_filtered_assets(context)
        if assets:
            first_entry = assets[0]
            first_ident = "TS_BRUSH_" + hashlib.sha1(favorite_key(first_entry).encode("utf-8")).hexdigest()[:16]
            wm.ts_brush_choice = first_ident
        else:
            wm.ts_brush_choice = "NONE"
    except Exception:
        pass
    tag_view3d_redraw()


def read_catalogs(library_root, asset_type, library_identifier, library_label):
    catalog_map = {}
    root = Path(library_root)
    if not root.is_dir():
        return catalog_map

    try:
        catalog_files = sorted(root.rglob("blender_assets.cats.txt"))
    except OSError:
        catalog_files = []

    for catalog_file in catalog_files:
        try:
            with catalog_file.open("r", encoding="utf-8-sig") as file:
                for raw_line in file:
                    line = raw_line.strip()
                    if not line or line.startswith("#") or line.upper().startswith("VERSION"):
                        continue
                    parts = line.split(":", 2)
                    if len(parts) != 3:
                        continue

                    catalog_uuid, catalog_path, simple_name = (p.strip() for p in parts)
                    if not catalog_uuid:
                        continue

                    catalog_path = catalog_path.strip("/")
                    display_name = (
                        catalog_path.replace("/", " / ")
                        if catalog_path else simple_name or catalog_uuid
                    )
                    key = make_catalog_key(asset_type, library_identifier, catalog_uuid)
                    catalog_map[str(catalog_uuid)] = key
                    CATALOG_ITEMS[key] = {
                        "name": str(display_name),
                        "simple_name": str(simple_name),
                        "path": str(catalog_path),
                        "uuid": str(catalog_uuid),
                        "library": str(library_label),
                        "asset_type": str(asset_type),
                        "library_identifier": str(library_identifier),
                    }
        except (OSError, UnicodeError):
            continue

    return catalog_map


def rebuild_catalog_enum_items():
    global CATALOG_ENUM_ITEMS
    load_favorites()
    items = [
        ("__ALL__", "All Libraries", "Show brushes from all asset libraries"),
        ("__FAVORITES__", "Favorites", "Show only your saved favorite brushes"),
    ]
    for key, info in sorted(CATALOG_ITEMS.items(), key=lambda item: (item[1]["library"].casefold(), item[1]["name"].casefold())):
        items.append((key, f"{info['library']}: {info['name']}", f"Library: {info['library']} | Catalog: {info['name']}"))
    CATALOG_ENUM_ITEMS = items


def catalog_enum_items(self, context):
    if not CATALOG_ENUM_ITEMS:
        rebuild_catalog_enum_items()
    return CATALOG_ENUM_ITEMS


def brush_supports_mode(brush, context):
    info = get_mode_info(context)
    if info is None and is_grease_pencil_mode(context):
        return True
    if info is None:
        return False
    flag = info["brush_flag"]
    try:
        return bool(hasattr(brush, flag) and getattr(brush, flag))
    except (ReferenceError, RuntimeError, TypeError):
        return False


def add_entry(entries, entry):
    safe_entry = {
        "name": normalize_brush_name(entry.get("name", "")),
        "asset_type": normalize_string(entry.get("asset_type", "CUSTOM")),
        "asset_identifier": normalize_string(entry.get("asset_identifier", "")),
        "relative_identifier": normalize_string(entry.get("relative_identifier", "")),
        "library_label": normalize_string(entry.get("library_label", "")),
        "source_file": normalize_string(entry.get("source_file", "")),
        "catalog_uuid": normalize_string(entry.get("catalog_uuid", "")),
        "catalog_key": normalize_string(entry.get("catalog_key", "")),
    }
    if not safe_entry["name"] or "bpy_struct" in safe_entry["name"]:
        return

    identity = (safe_entry["asset_type"], safe_entry["asset_identifier"], safe_entry["relative_identifier"])
    for old in entries:
        if (old["asset_type"], old["asset_identifier"], old["relative_identifier"]) == identity:
            return
    entries.append(safe_entry)


def cleanup_library_brush_duplicates(context):
    """Elimina SOLO copias sufragadas (.001, .002...) de brochas que este
    add-on importó desde librerías. Las brochas del usuario nunca se tocan."""
    active_brush = get_active_brush(context)
    kept_by_base_name = {}

    for brush in list(bpy.data.brushes):
        try:
            raw_name = brush.name
            base_name = re.sub(r'\.\d{3}$', '', raw_name)

            # Solo gestionamos brochas importadas por este add-on.
            if base_name not in LIBRARY_LOADED_BRUSHES and raw_name not in LIBRARY_LOADED_BRUSHES:
                continue

            if brush == active_brush:
                # La brocha activa siempre gana: se queda ella.
                loser = kept_by_base_name.pop(base_name, None)
                kept_by_base_name[base_name] = brush
                if loser is not None and loser != brush:
                    try:
                        bpy.data.brushes.remove(loser, do_unlink=True)
                    except Exception:
                        pass
                continue

            if base_name in kept_by_base_name:
                keeper = kept_by_base_name[base_name]
                # Prioriza la que ya es un asset (metadatos intactos).
                keeper_is_asset = False
                try:
                    keeper_is_asset = keeper.asset_data is not None
                except (ReferenceError, RuntimeError):
                    pass
                brush_is_asset = False
                try:
                    brush_is_asset = brush.asset_data is not None
                except (ReferenceError, RuntimeError):
                    pass
                remove_me = brush
                if brush_is_asset and not keeper_is_asset:
                    remove_me = keeper
                    kept_by_base_name[base_name] = brush
                if remove_me is not None:
                    try:
                        bpy.data.brushes.remove(remove_me, do_unlink=True)
                    except Exception:
                        pass
            else:
                kept_by_base_name[base_name] = brush
        except (ReferenceError, RuntimeError):
            pass


def essentials_file_supports_mode(context):
    """FIX: en Essentials, el modo se deduce del nombre del fichero .blend
    (mesh_sculpt, mesh_texture, mesh_vertex, mesh_weight), porque varias
    brochas comparten nombre entre ficheros y bpy.data.brushes solo guarda
    una copia: comprobar los flags de la brocha cargada puede usar la del
    fichero equivocado y filtrar brochas legítimas."""
    mode = getattr(context, "mode", "")
    stems = {
        "SCULPT": ("essentials_brushes-mesh_sculpt",),
        "PAINT_TEXTURE": ("essentials_brushes-mesh_texture",),
        "PAINT_VERTEX": ("essentials_brushes-mesh_vertex",),
        "PAINT_WEIGHT": ("essentials_brushes-mesh_weight",),
        "DRAW_GREASE_PENCIL": ("essentials_brushes-gp_draw",),
        "PAINT_GREASE_PENCIL": ("essentials_brushes-gp_draw",),
        "VERTEX_GREASE_PENCIL": ("essentials_brushes-gp_vertex",),
        "SCULPT_GREASE_PENCIL": ("essentials_brushes-gp_sculpt",),
        "WEIGHT_GREASE_PENCIL": ("essentials_brushes-gp_weight",),
        "PAINT_GPENCIL": ("essentials_brushes-gp_draw",),
        "VERTEX_GPENCIL": ("essentials_brushes-gp_vertex",),
        "SCULPT_GPENCIL": ("essentials_brushes-gp_sculpt",),
        "WEIGHT_GPENCIL": ("essentials_brushes-gp_weight",),
    }
    return stems.get(mode, ())


def scan_blend_file(entries, blend_file, library_root, asset_type, library_identifier, library_label, catalog_map, context):
    blend_file = Path(blend_file)
    library_root = Path(library_root)
    if not blend_file.is_file():
        return

    try:
        with bpy.data.libraries.load(str(blend_file), assets_only=True) as (data_from, data_to):
            source_names = [normalize_brush_name(item) for item in list(data_from.brushes)]
            source_names = [name for name in source_names if name]
            if not source_names:
                return

            # Solo importamos lo que aún no existe con el nombre exacto.
            # Esto evita que Blender cree copias ".001" en cada refresh.
            brushes_to_load = [name for name in source_names if bpy.data.brushes.get(name) is None]
            if brushes_to_load:
                data_to.brushes = brushes_to_load

        relative_blend_path = os.path.relpath(str(blend_file), str(library_root)).replace("\\", "/")
        active_brush = get_active_brush(context)

        for original_name in source_names:
            brush = bpy.data.brushes.get(original_name)
            # Fallback: recuperar una copia sufragada si la original ya no existe.
            if brush is None:
                brush = next((b for b in bpy.data.brushes if b.name == original_name or b.name.startswith(original_name + ".")), None)

            if brush is None:
                continue

            # Registrarla como gestionada (para la limpieza de duplicados).
            base_name = re.sub(r'\.\d{3}$', '', brush.name)
            LIBRARY_LOADED_BRUSHES.add(original_name)
            LIBRARY_LOADED_BRUSHES.add(base_name)

            try:
                if hasattr(brush, "preview") and brush.preview:
                    _ = brush.preview.icon_id

                relative_identifier = f"{relative_blend_path}/Brush/{original_name}"
                temp_entry = {
                    "name": original_name,
                    "asset_type": asset_type,
                    "asset_identifier": library_identifier,
                    "relative_identifier": relative_identifier,
                    "library_label": library_label,
                    "source_file": str(blend_file),
                    "catalog_uuid": "",
                    "catalog_key": "",
                }

                # FIX: en Essentials el modo se decide SOLO por el fichero
                # de origen. Nunca se consultan los flags de la brocha cargada:
                # como curve_sculpt y gp_* se escanean antes (orden alfabético),
                # los homónimos ("Smooth", "Airbrush"...) ya están ocupados por
                # brochas de otro fichero y sus flags dan respuestas equivocadas
                # (hacían aparecer librerías GP/curve en modos mesh y ocultar
                # brochas legítimas).
                if asset_type == "ESSENTIALS":
                    filename_stem = Path(str(blend_file)).stem.casefold()
                    mode_stems = tuple(s.casefold() for s in essentials_file_supports_mode(context))
                    if mode_stems and filename_stem not in mode_stems:
                        continue
                elif not brush_supports_mode(brush, context):
                    # Librerías CUSTOM: fuera del filtro, no se lista
                    # (y no se elimina, para no re-importarla con sufijo .001).
                    continue

                catalog_uuid = ""
                try:
                    if brush.asset_data is not None:
                        catalog_uuid = normalize_string(brush.asset_data.catalog_id)
                except (AttributeError, ReferenceError, RuntimeError):
                    pass

                catalog_key = catalog_map.get(catalog_uuid, "")
                temp_entry["catalog_uuid"] = catalog_uuid
                temp_entry["catalog_key"] = catalog_key

                add_entry(entries, temp_entry)

            except (ReferenceError, RuntimeError, TypeError):
                pass
    except Exception:
        pass


def scan_local_brushes(entries, context, local_catalog_map=None):
    for brush in bpy.data.brushes:
        try:
            if brush.asset_data is None or not brush_supports_mode(brush, context):
                continue
            name = normalize_brush_name(brush)
            # FIX: las brochas importadas por este add-on desde librerías
            # ya aparecen listadas con su librería de origen; si también
            # se listaran como "Current File" se verían duplicadas en el panel.
            base_name = re.sub(r'\.\d{3}$', '', name)
            if name in LIBRARY_LOADED_BRUSHES or base_name in LIBRARY_LOADED_BRUSHES:
                continue
            if hasattr(brush, "preview") and brush.preview:
                _ = brush.preview.icon_id
            catalog_uuid = normalize_string(brush.asset_data.catalog_id)
            catalog_key = (local_catalog_map or {}).get(catalog_uuid, "")
            add_entry(entries, {
                "name": name,
                "asset_type": "LOCAL",
                "asset_identifier": "",
                "relative_identifier": f"Brush/{name}",
                "library_label": "Current File",
                "source_file": "",
                "catalog_uuid": catalog_uuid,
                "catalog_key": catalog_key,
            })
        except (ReferenceError, RuntimeError, TypeError):
            continue


def scan_custom_libraries(entries, context):
    try:
        libraries = list(bpy.context.preferences.filepaths.asset_libraries)
    except (AttributeError, RuntimeError):
        libraries = []

    for library in libraries:
        try:
            library_name = str(library.name)
            library_root = Path(bpy.path.abspath(library.path))
            if not library_root.is_dir():
                continue
            catalog_map = read_catalogs(library_root, "CUSTOM", library_name, library_name)
            for blend_file in library_root.rglob("*.blend"):
                scan_blend_file(entries, blend_file, library_root, "CUSTOM", library_name, library_name, catalog_map, context)
        except Exception:
            pass


def scan_essentials(entries, context):
    try:
        datafiles = Path(bpy.utils.system_resource("DATAFILES"))
    except Exception:
        return
    library_root = datafiles / "assets"
    brushes_dir = library_root / "brushes"
    if not brushes_dir.is_dir():
        return

    catalog_map = read_catalogs(library_root, "ESSENTIALS", "", "Blender Essentials")
    if not catalog_map:
        catalog_map = read_catalogs(brushes_dir, "ESSENTIALS", "", "Blender Essentials")

    for blend_file in brushes_dir.rglob("*.blend"):
        scan_blend_file(entries, blend_file, library_root, "ESSENTIALS", "", "Blender Essentials", catalog_map, context)


def get_context_cache_key(context):
    try:
        obj = context.active_object
        object_type = obj.type if obj else "NO_OBJECT"
    except (AttributeError, ReferenceError, RuntimeError):
        object_type = "NO_OBJECT"
    return (
        str(getattr(context, "mode", "UNKNOWN")),
        object_type,
        bool(is_grease_pencil_mode(context)),
    )


def invalidate_asset_cache():
    global ASSETS_LOADED, CACHE_MODE
    ASSETS_LOADED = False
    CACHE_MODE = None
    tag_view3d_redraw()


@persistent
def ts_asset_shelf_load_post(_dummy):
    try:
        register()
    except Exception as exc:
        print("[Touchscreen Brush Asset Shelf] Could not restore after file load:", exc)
        try:
            invalidate_asset_cache()
        except Exception:
            pass


def refresh_assets(context):
    global ASSET_CACHE, CATALOG_ITEMS, CACHE_MODE, ASSETS_LOADED
    ASSET_CACHE = []
    CATALOG_ITEMS = {}
    ASSETS_LOADED = False

    # Limpiar solo duplicados de brochas gestionadas (importadas por el addon).
    cleanup_library_brush_duplicates(context)

    try:
        datafiles = Path(bpy.utils.system_resource("DATAFILES"))
        local_catalog_map = read_catalogs(
            datafiles / "assets", "ESSENTIALS", "", "Blender Essentials"
        )
    except Exception:
        local_catalog_map = {}

    scan_local_brushes(ASSET_CACHE, context, local_catalog_map)
    scan_custom_libraries(ASSET_CACHE, context)
    scan_essentials(ASSET_CACHE, context)

    if is_grease_pencil_mode(context):
        ASSET_CACHE = [
            entry for entry in ASSET_CACHE
            if grease_pencil_entry_matches(entry, context)
        ]

    # Deduplicar entradas por identidad absoluta (librería + fichero + brocha).
    # FIX: ya NO se deduplica por nombre — brochas legítimas con el mismo nombre
    # en distintos ficheros Essentials (Blur, Smear, Paint...) se eliminaban
    # entre sí y desaparecían del panel.
    unique_assets = []
    seen_identities = set()
    for entry in ASSET_CACHE:
        identity = (entry["asset_type"], entry["asset_identifier"], entry["relative_identifier"])
        if identity not in seen_identities:
            seen_identities.add(identity)
            unique_assets.append(entry)
    ASSET_CACHE = unique_assets

    used_keys = {entry["catalog_key"] for entry in ASSET_CACHE if entry["catalog_key"]}
    CATALOG_ITEMS = {k: v for k, v in CATALOG_ITEMS.items() if k in used_keys}
    ASSET_CACHE.sort(key=lambda entry: (entry["library_label"].casefold(), entry["name"].casefold()))
    CACHE_MODE = get_context_cache_key(context)
    ASSETS_LOADED = True
    rebuild_catalog_enum_items()
    tag_view3d_redraw()


def ensure_assets_loaded(context):
    current_key = get_context_cache_key(context)
    if not ASSETS_LOADED or CACHE_MODE != current_key:
        refresh_assets(context)


def get_filtered_assets(context, selected=None, search_text=None):
    if selected is None:
        selected = get_selected_catalog(context)
    if search_text is None:
        search_text = get_search_text(context)
    search_text = search_text.strip().casefold()
    load_favorites()

    if selected == "__ALL__":
        assets = ASSET_CACHE
    elif selected == "__FAVORITES__":
        assets = [entry for entry in ASSET_CACHE if favorite_key(entry) in FAVORITE_KEYS]
    else:
        assets = [entry for entry in ASSET_CACHE if entry["catalog_key"] == selected]

    if search_text:
        assets = [entry for entry in assets if search_text in entry["name"].casefold()]
    return assets


# ============================================================
# ICONS AND ENUMS
# ============================================================

def get_preview_icon(brush_name):
    brush_name = normalize_brush_name(brush_name)
    try:
        brush = bpy.data.brushes.get(brush_name)
        if brush is None:
            brush = next((item for item in bpy.data.brushes if item.name == brush_name or item.name.startswith(brush_name + ".")), None)
        if brush is None:
            return 0
        try:
            preview = brush.preview
            if preview is not None and preview.icon_id:
                return preview.icon_id
        except (AttributeError, ReferenceError, RuntimeError):
            pass
    except (AttributeError, ReferenceError, RuntimeError):
        pass
    return 0


def brush_choice_items(self, context):
    global BRUSH_ENUM_ITEMS, BRUSH_ENUM_MAP
    if context is None:
        return BRUSH_ENUM_ITEMS

    try:
        ensure_assets_loaded(context)
        assets = get_filtered_assets(context)
        items = []
        mapping = {}

        for index, entry in enumerate(assets):
            name = normalize_brush_name(entry.get("name", ""))
            if not name or "bpy_struct" in name:
                continue
            identifier = "TS_BRUSH_" + hashlib.sha1(favorite_key(entry).encode("utf-8")).hexdigest()[:16]
            icon_id = get_preview_icon(name)
            items.append((identifier, name, f"Activate brush: {name}", icon_id if icon_id else 'BRUSH_DATA', index))
            mapping[identifier] = entry

        BRUSH_ENUM_ITEMS = items
        BRUSH_ENUM_MAP = mapping

        if not items:
            return [("NONE", "No Brushes", "No brushes available in this selection", 'INFO', 0)]

        return BRUSH_ENUM_ITEMS
    except Exception:
        return [("NONE", "Error", "Error loading brushes", 'ERROR', 0)]


def on_brush_choice_update(self, context):
    if context is None:
        return
    identifier = getattr(self, "ts_brush_choice", None)
    if identifier == "NONE" or not identifier:
        return
    entry = BRUSH_ENUM_MAP.get(identifier)
    if entry is None:
        return
    try:
        bpy.ops.ts_asset_shelf.activate_brush(
            'EXEC_DEFAULT',
            brush_name=entry["name"],
            asset_type=entry["asset_type"],
            asset_identifier=entry["asset_identifier"],
            relative_identifier=entry["relative_identifier"],
            library_label=entry["library_label"],
        )
    except Exception:
        pass


# ============================================================
# OPERATORS AND MENUS
# ============================================================

class TS_ASSET_SHELF_OT_activate_brush(bpy.types.Operator):
    bl_idname = "ts_asset_shelf.activate_brush"
    bl_label = "Activate Brush"
    bl_description = "Activate this brush"

    brush_name: bpy.props.StringProperty(default="")
    asset_type: bpy.props.StringProperty(default="CUSTOM")
    asset_identifier: bpy.props.StringProperty(default="")
    relative_identifier: bpy.props.StringProperty(default="")
    library_label: bpy.props.StringProperty(default="")

    def execute(self, context):
        try:
            result = bpy.ops.brush.asset_activate(
                'EXEC_DEFAULT',
                asset_library_type=self.asset_type,
                asset_library_identifier=self.asset_identifier,
                relative_asset_identifier=self.relative_identifier,
                use_toggle=False,
            )
            if 'FINISHED' in result:
                return {'FINISHED'}
        except Exception:
            pass
        return {'CANCELLED'}


class TS_ASSET_SHELF_OT_refresh_libraries(bpy.types.Operator):
    bl_idname = "ts_asset_shelf.refresh_libraries"
    bl_label = "Refresh Libraries"
    bl_description = "Reread assets and catalogs from libraries"
    bl_options = {'INTERNAL'}

    use_remote_listing: bpy.props.BoolProperty(default=False)
    use_shift_for_remote_listing: bpy.props.BoolProperty(default=False)

    def execute(self, context):
        refresh_assets(context)
        self.report({'INFO'}, "Asset libraries refreshed")
        return {'FINISHED'}


def get_current_brush_entry(context):
    if context is None:
        return None
    return BRUSH_ENUM_MAP.get(getattr(context.window_manager, "ts_brush_choice", ""))


class TS_ASSET_SHELF_OT_add_favorite(bpy.types.Operator):
    bl_idname = "ts_asset_shelf.add_favorite"
    bl_label = "Add to Favorites"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        load_favorites()
        entry = get_current_brush_entry(context)
        if entry is not None:
            FAVORITE_KEYS.add(favorite_key(entry))
            save_favorites()
            tag_view3d_redraw()
        return {'FINISHED'}


class TS_ASSET_SHELF_OT_remove_favorite(bpy.types.Operator):
    bl_idname = "ts_asset_shelf.remove_favorite"
    bl_label = "Remove from Favorites"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        load_favorites()
        entry = get_current_brush_entry(context)
        if entry is not None:
            FAVORITE_KEYS.discard(favorite_key(entry))
            save_favorites()
            tag_view3d_redraw()
        return {'FINISHED'}


class TS_ASSET_SHELF_MT_specials(bpy.types.Menu):
    bl_idname = "TS_ASSET_SHELF_MT_specials"
    bl_label = "Brush Specials"

    def draw(self, context):
        layout = self.layout
        active_brush = get_active_brush(context)

        if active_brush:
            layout.operator("brush.asset_save_as", text="Duplicate to Asset...", icon='DUPLICATE')

            if active_brush.asset_data:
                if getattr(active_brush, "has_unsaved_changes", False):
                    layout.label(text="* Has Unsaved Changes", icon='ERROR')

                layout.operator("brush.asset_save", text="Save Changes to Asset", icon='FILE_TICK')
                layout.operator("brush.asset_revert", text="Revert to Asset", icon='FILE_BACKUP')

                layout.separator()
                layout.operator("brush.asset_edit_metadata", text="Edit Metadata", icon='PREFERENCES')
            else:
                layout.operator("asset.mark", text="Mark as Scene Asset", icon='ASSET_MANAGER')

            layout.separator()
            layout.operator("brush.asset_delete", text="Delete Asset", icon='TRASH')

            context.window_manager.defer_layout_update()

            if not active_brush.asset_data:
                refresh_assets(context)
        else:
            layout.label(text="No active brush detected", icon='ERROR')


# ============================================================
# MAIN SIDEBAR PANEL
# ============================================================

class TS_ASSET_SHELF_PT_sidebar(bpy.types.Panel):
    bl_label = "Brush Asset Shelf"
    bl_idname = "TS_ASSET_SHELF_PT_sidebar"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Tool"

    @classmethod
    def poll(cls, context):
        return context.mode in MODE_SETTINGS or is_grease_pencil_mode(context)

    def draw(self, context):
        layout = self.layout
        wm = context.window_manager
        ensure_assets_loaded(context)
        load_favorites()

        if not get_search_text(context):
            active_brush = get_active_brush(context)
            if active_brush:
                active_name = normalize_brush_name(active_brush.name)
                for entry in ASSET_CACHE:
                    if normalize_brush_name(entry.get("name", "")) == active_name:
                        ident = "TS_BRUSH_" + hashlib.sha1(favorite_key(entry).encode("utf-8")).hexdigest()[:16]
                        if wm.ts_brush_choice != ident and ident in BRUSH_ENUM_MAP:
                            wm.ts_brush_choice = ident
                        break

        # Row 1: Search filter
        layout.prop(wm, "ts_brush_search", text="", icon='VIEWZOOM')

        # Row 2: Catalog selector
        layout.prop(wm, "ts_brush_catalog", text="", icon='DOWNARROW_HLT')

        # Row 3: Names toggle, Refresh Libraries operator, and Brush Specials menu
        row3 = layout.row(align=True)
        row3.prop(wm, "ts_brush_show_names", text="Names", icon='FONT_DATA', toggle=True)

        op_refresh = row3.operator("ts_asset_shelf.refresh_libraries", text="", icon='FILE_REFRESH')
        op_refresh.use_remote_listing = False
        op_refresh.use_shift_for_remote_listing = False

        row3.menu("TS_ASSET_SHELF_MT_specials", text="", icon='DOWNARROW_HLT')

        # Icon grid view
        assets = get_filtered_assets(context)
        shelf_scale, shelf_scale_popup = get_asset_shelf_scale()
        if not assets:
            layout.label(text="No brushes found", icon='INFO')
        else:
            layout.template_icon_view(
                wm,
                "ts_brush_choice",
                show_labels=wm.ts_brush_show_names,
                scale=shelf_scale,
                scale_popup=shelf_scale_popup,
            )

        active_brush = get_active_brush(context)
        if active_brush:
            layout.label(text=f"Active: {active_brush.name}", icon='BRUSH_DATA')

        entry = get_current_brush_entry(context)
        if entry is not None:
            favorite_row = layout.row(align=True)
            if is_favorite(entry):
                favorite_row.operator("ts_asset_shelf.remove_favorite", text="Remove from Favorites", icon='REMOVE')
            else:
                favorite_row.operator("ts_asset_shelf.add_favorite", text="Add to Favorites", icon='ADD')

        layout.label(text=f"{len(assets)} brushes", icon='BRUSH_DATA')


# ============================================================
# REGISTRATION
# ============================================================

CLASSES = (
    TS_ASSET_SHELF_OT_activate_brush,
    TS_ASSET_SHELF_OT_refresh_libraries,
    TS_ASSET_SHELF_OT_add_favorite,
    TS_ASSET_SHELF_OT_remove_favorite,
    TS_ASSET_SHELF_MT_specials,
    TS_ASSET_SHELF_PT_sidebar,
)


def unregister():
    handlers = bpy.app.handlers.load_post
    if ts_asset_shelf_load_post in handlers:
        handlers.remove(ts_asset_shelf_load_post)

    for prop_name in ("ts_brush_catalog", "ts_brush_search", "ts_brush_show_names", "ts_brush_choice"):
        if hasattr(bpy.types.WindowManager, prop_name):
            delattr(bpy.types.WindowManager, prop_name)

    for cls in reversed(CLASSES):
        try:
            bpy.utils.unregister_class(cls)
        except (RuntimeError, ValueError):
            pass

    # Nota: no se eliminan las brochas importadas aquí. Ya están en el
    # archivo del usuario (bpy.data.brushes) y borrarlas al desactivar el
    # addon destruiría trabajo del usuario. Solo se olvidan como gestionadas.
    LIBRARY_LOADED_BRUSHES.clear()


def register():
    unregister()
    load_favorites()
    rebuild_catalog_enum_items()

    bpy.types.WindowManager.ts_brush_catalog = bpy.props.EnumProperty(
        name="Catalog",
        description="Filter brushes by asset catalog",
        items=catalog_enum_items,
        update=on_catalog_update,
    )
    bpy.types.WindowManager.ts_brush_search = bpy.props.StringProperty(
        name="Search Brushes",
        description="Filter brushes by name",
        default="",
        options={'TEXTEDIT_UPDATE'},
        update=on_brush_search_update,
    )
    bpy.types.WindowManager.ts_brush_show_names = bpy.props.BoolProperty(
        name="Show Names",
        description="Show or hide brush names below thumbnails",
        default=True,
    )
    bpy.types.WindowManager.ts_brush_choice = bpy.props.EnumProperty(
        name="Brushes",
        description="Select and activate a brush",
        items=brush_choice_items,
        update=on_brush_choice_update,
        options={'SKIP_SAVE'},
    )

    for cls in CLASSES:
        try:
            bpy.utils.register_class(cls)
        except (RuntimeError, ValueError):
            unregister()
            return

    load_favorites()

    handlers = bpy.app.handlers.load_post
    if ts_asset_shelf_load_post not in handlers:
        handlers.append(ts_asset_shelf_load_post)

    invalidate_asset_cache()


if __name__ == "__main__":
    register()