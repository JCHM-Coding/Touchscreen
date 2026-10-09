import bpy
import os
import re
import json
import hashlib
from pathlib import Path


# ============================================================
# TOUCHSCREEN - BRUSH ASSET SHELF
# Blender 5.3 Alpha — 3D View, Image Editor, and Grease Pencil contexts
# ============================================================


def restore_native_brush_selector():
    """Undo the selector patch used by older versions of this script."""
    try:
        from bl_ui.properties_paint_common import BrushAssetShelf
        marker = "_touchscreen_original_draw_popup_selector"
        original = getattr(BrushAssetShelf, marker, None)
        if original is not None:
            BrushAssetShelf.draw_popup_selector = staticmethod(original)
            try:
                delattr(BrushAssetShelf, marker)
            except AttributeError:
                pass
    except (ImportError, AttributeError, RuntimeError):
        pass


GRID_COLUMNS = 4

ASSET_CACHE = []
CATALOG_ITEMS = {}
CATALOG_ENUM_ITEMS = []
CACHE_MODE = None
ASSETS_LOADED = False

BRUSH_ENUM_ITEMS = []
BRUSH_ENUM_MAP = {}
FAVORITE_KEYS = set()
FAVORITES_LOADED = False

MODE_SETTINGS = {
    'SCULPT': {
        "label": "Esculpido",
        "brush_flag": "use_paint_sculpt",
    },
    'PAINT_TEXTURE': {
        "label": "Pintura de texturas",
        "brush_flag": "use_paint_image",
    },
    'PAINT_VERTEX': {
        "label": "Pintura de vértices",
        "brush_flag": "use_paint_vertex",
    },
    'PAINT_WEIGHT': {
        "label": "Pintura de pesos",
        "brush_flag": "use_paint_weight",
    },
}


# ============================================================
# NOMBRES
# ============================================================

def normalize_brush_name(value):
    if value is None:
        return ""

    if isinstance(value, str):
        text = value.strip()

        if "bpy_struct" in text and "Brush(" in text:
            match = re.search(
                r'Brush\("((?:\\.|[^"\\])*)"\)',
                text,
            )
            if match:
                return (
                    match.group(1)
                    .replace('\\"', '"')
                    .replace("\\\\", "\\")
                )

        return text

    try:
        name = value.name
        if name is not None:
            return str(name)
    except (AttributeError, ReferenceError, RuntimeError):
        pass

    text = str(value)
    match = re.search(
        r'Brush\("((?:\\.|[^"\\])*)"\)',
        text,
    )

    if match:
        return (
            match.group(1)
            .replace('\\"', '"')
            .replace("\\\\", "\\")
        )

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


# ============================================================
# ESTADO
# ============================================================

GREASE_PENCIL_MODES = {
    # Blender 4.3+ / 5.x Grease Pencil modes.
    'PAINT_GREASE_PENCIL',
    'SCULPT_GREASE_PENCIL',
    'WEIGHT_GREASE_PENCIL',
    'VERTEX_GREASE_PENCIL',
    # Compatibility aliases seen in older Blender builds.
    'PAINT_GPENCIL',
    'SCULPT_GPENCIL',
    'WEIGHT_GPENCIL',
    'VERTEX_GPENCIL',
}


def get_mode_info(context):
    return MODE_SETTINGS.get(context.mode)


def is_grease_pencil_mode(context):
    return bool(context and context.mode in GREASE_PENCIL_MODES)


def get_selected_catalog(context):
    try:
        return context.window_manager.ts_brush_catalog
    except (AttributeError, TypeError):
        return "__ALL__"


def set_selected_catalog(context, key):
    try:
        context.window_manager.ts_brush_catalog = str(key)
    except (AttributeError, TypeError, ValueError):
        pass


def get_search_text(context):
    try:
        return context.window_manager.ts_brush_search.strip().casefold()
    except (AttributeError, TypeError):
        return ""


def make_catalog_key(asset_type, library_identifier, catalog_uuid):
    return f"{asset_type}|{library_identifier}|{catalog_uuid}"


# ============================================================
# PERSISTENT VIRTUAL FAVORITES CATALOG
# ============================================================

def favorites_file_path():
    """Return a writable addon-owned JSON path, outside asset libraries."""
    try:
        config_dir = bpy.utils.user_resource(
            'CONFIG',
            path="touchscreen_asset_shelf",
            create=True,
        )
        if config_dir:
            return Path(config_dir) / "favorites.json"
    except (AttributeError, RuntimeError, TypeError):
        pass

    # Fallback to Blender's user configuration directory when available.
    try:
        base = Path(bpy.utils.user_resource('CONFIG', create=True))
        directory = base / "touchscreen_asset_shelf"
        directory.mkdir(parents=True, exist_ok=True)
        return directory / "favorites.json"
    except Exception:
        return Path.home() / ".touchscreen_asset_shelf_favorites.json"


def favorite_key(entry):
    """Stable identity based on the asset library and relative asset path."""
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
    except (OSError, ValueError, TypeError) as exc:
        print("[Touchscreen] Could not read favorites:", repr(exc))

    FAVORITES_LOADED = True


def save_favorites():
    path = favorites_file_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"version": 1, "favorites": sorted(FAVORITE_KEYS)}
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return True
    except (OSError, TypeError, ValueError) as exc:
        print("[Touchscreen] Could not save favorites:", repr(exc))
        return False


def is_favorite(entry):
    load_favorites()
    return favorite_key(entry) in FAVORITE_KEYS


# ============================================================
# REDIBUJADO
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
    try:
        print(
            "[Touchscreen] BUSCADOR UPDATE:",
            repr(self.ts_brush_search),
        )
    except (AttributeError, ReferenceError, RuntimeError):
        pass

    try:
        if context and context.region:
            context.region.tag_redraw()
        if context and context.area:
            context.area.tag_redraw()
    except (AttributeError, ReferenceError, RuntimeError):
        pass

    tag_view3d_redraw()


# ============================================================
# CATÁLOGOS
# ============================================================

def find_catalog_file(library_root):
    root = Path(library_root)

    candidates = [
        root / "blender_assets.cats.txt",
        root / "brushes" / "blender_assets.cats.txt",
    ]

    for candidate in candidates:
        if candidate.is_file():
            return candidate

    return None


def read_catalogs(
    library_root,
    asset_type,
    library_identifier,
    library_label,
):
    catalog_map = {}
    catalog_file = find_catalog_file(library_root)

    if catalog_file is None:
        return catalog_map

    try:
        with catalog_file.open(
            "r",
            encoding="utf-8-sig",
        ) as file:
            for raw_line in file:
                line = raw_line.strip()

                if not line or line.startswith("#"):
                    continue

                if line.upper().startswith("VERSION"):
                    continue

                parts = line.split(":", 2)

                if len(parts) != 3:
                    continue

                catalog_uuid, catalog_path, simple_name = (
                    part.strip() for part in parts
                )

                if not catalog_uuid:
                    continue

                catalog_path = catalog_path.strip("/")

                display_name = (
                    catalog_path.replace("/", " / ")
                    if catalog_path
                    else simple_name or catalog_uuid
                )

                key = make_catalog_key(
                    asset_type,
                    library_identifier,
                    catalog_uuid,
                )

                catalog_map[str(catalog_uuid)] = key

                CATALOG_ITEMS[key] = {
                    "name": str(display_name),
                    "path": str(catalog_path),
                    "uuid": str(catalog_uuid),
                    "library": str(library_label),
                    "asset_type": str(asset_type),
                    "library_identifier": str(library_identifier),
                }

    except (OSError, UnicodeError) as exc:
        print(
            "[Touchscreen] Error leyendo catálogo:",
            str(catalog_file),
            repr(exc),
        )

    return catalog_map


def rebuild_catalog_enum_items():
    global CATALOG_ENUM_ITEMS

    load_favorites()
    items = [
        (
            "__ALL__",
            "All Libraries",
            "Show brushes from all asset libraries",
        ),
        (
            "__FAVORITES__",
            "Favorites",
            "Show only your saved favorite brushes",
        ),
    ]

    for key, info in sorted(
        CATALOG_ITEMS.items(),
        key=lambda item: (
            item[1]["library"].casefold(),
            item[1]["name"].casefold(),
        ),
    ):
        label = info["name"]
        library = info["library"]

        items.append((
            key,
            f"{library}: {label}",
            f"Library: {library} | Catalog: {label}",
        ))

    CATALOG_ENUM_ITEMS = items


def catalog_enum_items(self, context):
    return CATALOG_ENUM_ITEMS


# ============================================================
# COMPATIBILIDAD
# ============================================================

def brush_supports_mode(brush, context):
    info = get_mode_info(context)

    # Grease Pencil uses a different set of tools in some Blender versions.
    # Keep the shelf visible there and let Blender decide whether an asset can
    # be activated in that editor/mode; the standard paint flags do not cover
    # all Grease Pencil tools.
    if info is None and is_grease_pencil_mode(context):
        return True

    if info is None:
        return False

    flag = info["brush_flag"]

    try:
        return bool(
            hasattr(brush, flag)
            and getattr(brush, flag)
        )
    except (ReferenceError, RuntimeError, TypeError):
        return False


# ============================================================
# CACHÉ
# ============================================================

def add_entry(entries, entry):
    safe_entry = {
        "name": normalize_brush_name(entry.get("name", "")),
        "asset_type": normalize_string(
            entry.get("asset_type", "CUSTOM")
        ),
        "asset_identifier": normalize_string(
            entry.get("asset_identifier", "")
        ),
        "relative_identifier": normalize_string(
            entry.get("relative_identifier", "")
        ),
        "library_label": normalize_string(
            entry.get("library_label", "")
        ),
        "source_file": normalize_string(
            entry.get("source_file", "")
        ),
        "catalog_uuid": normalize_string(
            entry.get("catalog_uuid", "")
        ),
        "catalog_key": normalize_string(
            entry.get("catalog_key", "")
        ),
    }

    if (
        not safe_entry["name"]
        or "bpy_struct" in safe_entry["name"]
    ):
        return

    identity = (
        safe_entry["asset_type"],
        safe_entry["asset_identifier"],
        safe_entry["relative_identifier"],
    )

    for old in entries:
        old_identity = (
            old["asset_type"],
            old["asset_identifier"],
            old["relative_identifier"],
        )

        if old_identity == identity:
            return

    entries.append(safe_entry)


# ============================================================
# ESCANEAR ARCHIVOS BLEND
# ============================================================

def scan_blend_file(
    entries,
    blend_file,
    library_root,
    asset_type,
    library_identifier,
    library_label,
    catalog_map,
    context,
):
    blend_file = Path(blend_file)
    library_root = Path(library_root)

    if not blend_file.is_file():
        return

    try:
        with bpy.data.libraries.load(
            str(blend_file),
            assets_only=True,
        ) as (data_from, data_to):
            source_names = [
                normalize_brush_name(item)
                for item in list(data_from.brushes)
            ]

        source_names = [
            name for name in source_names
            if name
        ]

        if not source_names:
            return

        with bpy.data.libraries.load(
            str(blend_file),
            assets_only=True,
        ) as (data_from, data_to):
            available_names = {
                normalize_brush_name(item)
                for item in list(data_from.brushes)
            }

            requested_names = [
                name for name in source_names
                if name in available_names
            ]

            data_to.brushes = list(requested_names)

        loaded_brushes = list(data_to.brushes or [])

        relative_blend_path = os.path.relpath(
            str(blend_file),
            str(library_root),
        ).replace("\\", "/")

        for original_name, brush in zip(
            requested_names,
            loaded_brushes,
        ):
            if brush is None:
                continue

            original_name = normalize_brush_name(original_name)

            try:
                if not brush_supports_mode(brush, context):
                    continue

                catalog_uuid = ""

                try:
                    if brush.asset_data is not None:
                        catalog_uuid = normalize_string(
                            brush.asset_data.catalog_id
                        )
                except (
                    AttributeError,
                    ReferenceError,
                    RuntimeError,
                ):
                    pass

                catalog_key = catalog_map.get(
                    catalog_uuid,
                    "",
                )

                relative_identifier = (
                    f"{relative_blend_path}/Brush/{original_name}"
                )

                add_entry(entries, {
                    "name": original_name,
                    "asset_type": asset_type,
                    "asset_identifier": library_identifier,
                    "relative_identifier": relative_identifier,
                    "library_label": library_label,
                    "source_file": str(blend_file),
                    "catalog_uuid": catalog_uuid,
                    "catalog_key": catalog_key,
                })

            except (
                ReferenceError,
                RuntimeError,
                TypeError,
            ) as exc:
                print(
                    "[Touchscreen] Error leyendo brocha:",
                    original_name,
                    repr(exc),
                )

    except Exception as exc:
        print(
            "[Touchscreen] Error escaneando:",
            str(blend_file),
            repr(exc),
        )


# ============================================================
# BROCHAS LOCALES
# ============================================================

def scan_local_brushes(entries, context):
    for brush in bpy.data.brushes:
        try:
            if brush.asset_data is None:
                continue

            if not brush_supports_mode(brush, context):
                continue

            name = normalize_brush_name(brush)
            catalog_uuid = normalize_string(
                brush.asset_data.catalog_id
            )

            add_entry(entries, {
                "name": name,
                "asset_type": "LOCAL",
                "asset_identifier": "",
                "relative_identifier": f"Brush/{name}",
                "library_label": "Archivo actual",
                "source_file": "",
                "catalog_uuid": catalog_uuid,
                "catalog_key": "",
            })

        except (
            ReferenceError,
            RuntimeError,
            TypeError,
        ):
            continue


# ============================================================
# BIBLIOTECAS PERSONALIZADAS
# ============================================================

def scan_custom_libraries(entries, context):
    try:
        libraries = list(
            bpy.context.preferences.filepaths.asset_libraries
        )
    except (AttributeError, RuntimeError):
        libraries = []

    for library in libraries:
        try:
            library_name = str(library.name)
            library_root = Path(
                bpy.path.abspath(library.path)
            )

            if not library_root.is_dir():
                continue

            catalog_map = read_catalogs(
                library_root,
                "CUSTOM",
                library_name,
                library_name,
            )

            for blend_file in library_root.rglob("*.blend"):
                scan_blend_file(
                    entries=entries,
                    blend_file=blend_file,
                    library_root=library_root,
                    asset_type="CUSTOM",
                    library_identifier=library_name,
                    library_label=library_name,
                    catalog_map=catalog_map,
                    context=context,
                )

        except Exception as exc:
            print(
                "[Touchscreen] Error en biblioteca:",
                repr(exc),
            )


# ============================================================
# BLENDER ESSENTIALS
# ============================================================

def scan_essentials(entries, context):
    try:
        datafiles = Path(
            bpy.utils.system_resource("DATAFILES")
        )
    except Exception as exc:
        print(
            "[Touchscreen] No se pudo localizar DATAFILES:",
            repr(exc),
        )
        return

    library_root = datafiles / "assets"
    brushes_dir = library_root / "brushes"

    if not brushes_dir.is_dir():
        print(
            "[Touchscreen] No se encontró:",
            str(brushes_dir),
        )
        return

    catalog_map = read_catalogs(
        library_root,
        "ESSENTIALS",
        "",
        "Blender Essentials",
    )

    if not catalog_map:
        catalog_map = read_catalogs(
            brushes_dir,
            "ESSENTIALS",
            "",
            "Blender Essentials",
        )

    for blend_file in brushes_dir.rglob("*.blend"):
        scan_blend_file(
            entries=entries,
            blend_file=blend_file,
            library_root=library_root,
            asset_type="ESSENTIALS",
            library_identifier="",
            library_label="Blender Essentials",
            catalog_map=catalog_map,
            context=context,
        )


# ============================================================
# REFRESCAR CACHÉ
# ============================================================

def refresh_assets(context):
    global ASSET_CACHE, CATALOG_ITEMS
    global CACHE_MODE, ASSETS_LOADED
    global BRUSH_ENUM_ITEMS, BRUSH_ENUM_MAP

    ASSET_CACHE = []
    CATALOG_ITEMS = {}
    BRUSH_ENUM_ITEMS = []
    BRUSH_ENUM_MAP = {}
    ASSETS_LOADED = False

    print("[Touchscreen] Iniciando escaneo...")

    scan_local_brushes(ASSET_CACHE, context)
    scan_custom_libraries(ASSET_CACHE, context)
    scan_essentials(ASSET_CACHE, context)

    used_keys = {
        entry["catalog_key"]
        for entry in ASSET_CACHE
        if entry["catalog_key"]
    }

    CATALOG_ITEMS = {
        key: info
        for key, info in CATALOG_ITEMS.items()
        if key in used_keys
    }

    ASSET_CACHE.sort(
        key=lambda entry: (
            entry["library_label"].casefold(),
            entry["name"].casefold(),
        )
    )

    CACHE_MODE = str(context.mode)
    ASSETS_LOADED = True

    rebuild_catalog_enum_items()

    try:
        selected = context.window_manager.ts_brush_catalog

        valid_keys = {item[0] for item in CATALOG_ENUM_ITEMS}
        if selected not in valid_keys:
            context.window_manager.ts_brush_catalog = "__ALL__"

    except (AttributeError, TypeError):
        pass

    print("[Touchscreen] Modo:", CACHE_MODE)
    print("[Touchscreen] Brochas compatibles:", len(ASSET_CACHE))
    print("[Touchscreen] Catálogos compatibles:", len(CATALOG_ITEMS))
    print("[Touchscreen] Caché preparada.")

    tag_view3d_redraw()


def ensure_assets_loaded(context):
    if not ASSETS_LOADED or CACHE_MODE != context.mode:
        refresh_assets(context)


def get_filtered_assets(
    context,
    selected=None,
    search_text=None,
):
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
        assets = [
            entry for entry in ASSET_CACHE
            if entry["catalog_key"] == selected
        ]

    if search_text:
        assets = [
            entry for entry in assets
            if search_text in entry["name"].casefold()
        ]

    return assets


# ============================================================
# ICONOS / PREVIEWS
# ============================================================

def get_preview_icon(brush_name):
    brush_name = normalize_brush_name(brush_name)

    try:
        brush = bpy.data.brushes.get(brush_name)

        if brush is None:
            brush = next(
                (
                    item for item in bpy.data.brushes
                    if item.name == brush_name
                    or item.name.startswith(brush_name + ".")
                ),
                None,
            )

        if brush is None:
            return 0

        try:
            preview = brush.preview

            if preview is not None and preview.icon_id:
                return preview.icon_id

        except (
            AttributeError,
            ReferenceError,
            RuntimeError,
        ):
            pass

        try:
            brush.preview_ensure()
            preview = brush.preview

            if preview is not None and preview.icon_id:
                return preview.icon_id

        except (
            AttributeError,
            ReferenceError,
            RuntimeError,
            TypeError,
        ):
            pass

    except (
        AttributeError,
        ReferenceError,
        RuntimeError,
    ):
        pass

    return 0


# ============================================================
# ENUM DINÁMICO PARA LAS MINIATURAS
# ============================================================

def brush_choice_items(self, context):
    global BRUSH_ENUM_ITEMS, BRUSH_ENUM_MAP

    if context is None:
        return BRUSH_ENUM_ITEMS

    try:
        ensure_assets_loaded(context)

        selected_catalog = getattr(
            self,
            "catalog_key",
            get_selected_catalog(context),
        )

        search_text = getattr(
            self,
            "search",
            get_search_text(context),
        )

        assets = get_filtered_assets(
            context,
            selected=selected_catalog,
            search_text=search_text,
        )

        items = []
        mapping = {}

        for index, entry in enumerate(assets):
            name = normalize_brush_name(entry.get("name", ""))

            if not name or "bpy_struct" in name:
                continue

            identifier = "TS_BRUSH_" + hashlib.sha1(
                favorite_key(entry).encode("utf-8")
            ).hexdigest()[:16]

            icon_id = get_preview_icon(name)
            icon = icon_id if icon_id else 'BRUSH_DATA'

            items.append((
                identifier,
                name,
                f"Activate brush: {name}",
                icon,
                index,
            ))

            mapping[identifier] = entry

        BRUSH_ENUM_ITEMS = items
        BRUSH_ENUM_MAP = mapping

        return BRUSH_ENUM_ITEMS

    except Exception as exc:
        print(
            "[Touchscreen] Error generando previews:",
            repr(exc),
        )
        BRUSH_ENUM_ITEMS = []
        BRUSH_ENUM_MAP = {}
        return BRUSH_ENUM_ITEMS


def on_brush_choice_update(self, context):
    if context is None:
        return

    identifier = getattr(self, "ts_brush_choice", None)
    if identifier is None:
        identifier = getattr(self, "brush_choice", "")
    entry = BRUSH_ENUM_MAP.get(identifier)

    if entry is None:
        print(
            "[Touchscreen] No se encontró la brocha seleccionada:",
            identifier,
        )
        return

    try:
        result = bpy.ops.ts_asset_shelf.activate_brush(
            'EXEC_DEFAULT',
            brush_name=entry["name"],
            asset_type=entry["asset_type"],
            asset_identifier=entry["asset_identifier"],
            relative_identifier=entry["relative_identifier"],
            library_label=entry["library_label"],
        )

        print(
            "[Touchscreen] Selección desde preview:",
            entry["name"],
            "| Resultado:",
            result,
        )

    except Exception as exc:
        print(
            "[Touchscreen] Error activando desde preview:",
            repr(exc),
        )


# ============================================================
# ACTIVAR BROCHA
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
        name = normalize_brush_name(self.brush_name)
        asset_type = normalize_string(self.asset_type)
        library_id = normalize_string(self.asset_identifier)
        relative_id = normalize_string(self.relative_identifier)

        if (
            not name
            or "bpy_struct" in name
            or not relative_id
            or "bpy_struct" in relative_id
        ):
            self.report(
                {'ERROR'},
                "Invalid brush name or asset path.",
            )
            return {'CANCELLED'}

        try:
            result = bpy.ops.brush.asset_activate(
                'EXEC_DEFAULT',
                asset_library_type=asset_type,
                asset_library_identifier=library_id,
                relative_asset_identifier=relative_id,
                use_toggle=False,
            )

            print(
                "[Touchscreen] Activando:",
                name,
                "| Resultado:",
                result,
            )

            if 'FINISHED' in result:
                return {'FINISHED'}

        except Exception as exc:
            print(
                "[Touchscreen] Error activando asset:",
                repr(exc),
            )

        self.report(
            {'ERROR'},
            "Could not activate brush. See the console for details.",
        )
        return {'CANCELLED'}


# ============================================================
# SIDEBAR CONTROLS AND FAVORITES OPERATORS
# ============================================================

def on_catalog_update(self, context):
    global BRUSH_ENUM_ITEMS, BRUSH_ENUM_MAP
    BRUSH_ENUM_ITEMS = []
    BRUSH_ENUM_MAP = {}
    tag_view3d_redraw()


def on_show_names_update(self, context):
    tag_view3d_redraw()


class TS_ASSET_SHELF_OT_refresh(bpy.types.Operator):
    bl_idname = "ts_asset_shelf.refresh"
    bl_label = "Refresh Brushes"
    bl_description = "Rescan available brush asset libraries"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        global BRUSH_ENUM_ITEMS, BRUSH_ENUM_MAP
        try:
            refresh_assets(context)
            load_favorites()
            BRUSH_ENUM_ITEMS = []
            BRUSH_ENUM_MAP = {}
            self.report({'INFO'}, "Brush assets refreshed")
            return {'FINISHED'}
        except Exception as exc:
            print("[Touchscreen] Error refreshing brushes:", repr(exc))
            self.report({'ERROR'}, "Could not refresh brush assets; see console")
            return {'CANCELLED'}


def get_current_brush_entry(context):
    """Resolve the current grid selection to its cached asset entry."""
    if context is None:
        return None
    wm = context.window_manager
    identifier = getattr(wm, "ts_brush_choice", "")
    entry = BRUSH_ENUM_MAP.get(identifier)
    if entry is not None:
        return entry

    # If the selection is stale (for example after changing catalogs), do not
    # guess by index: that could identify a different brush.
    return None


class TS_ASSET_SHELF_OT_add_favorite(bpy.types.Operator):
    bl_idname = "ts_asset_shelf.add_favorite"
    bl_label = "Add to Favorites"
    bl_description = "Save the selected brush in your Favorites catalog"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        global BRUSH_ENUM_ITEMS, BRUSH_ENUM_MAP
        load_favorites()
        entry = get_current_brush_entry(context)
        if entry is None:
            self.report({'WARNING'}, "Select a brush first")
            return {'CANCELLED'}

        FAVORITE_KEYS.add(favorite_key(entry))
        if not save_favorites():
            self.report({'ERROR'}, "Could not save Favorites; see console")
            return {'CANCELLED'}

        BRUSH_ENUM_ITEMS = []
        BRUSH_ENUM_MAP = {}
        tag_view3d_redraw()
        self.report({'INFO'}, f"Added '{entry['name']}' to Favorites")
        return {'FINISHED'}


class TS_ASSET_SHELF_OT_remove_favorite(bpy.types.Operator):
    bl_idname = "ts_asset_shelf.remove_favorite"
    bl_label = "Remove from Favorites"
    bl_description = "Remove the selected brush from your Favorites catalog"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        global BRUSH_ENUM_ITEMS, BRUSH_ENUM_MAP
        load_favorites()
        entry = get_current_brush_entry(context)
        if entry is None:
            self.report({'WARNING'}, "Select a brush first")
            return {'CANCELLED'}

        key = favorite_key(entry)
        if key not in FAVORITE_KEYS:
            self.report({'INFO'}, "This brush is not in Favorites")
            return {'CANCELLED'}

        FAVORITE_KEYS.discard(key)
        if not save_favorites():
            self.report({'ERROR'}, "Could not save Favorites; see console")
            return {'CANCELLED'}

        BRUSH_ENUM_ITEMS = []
        BRUSH_ENUM_MAP = {}
        tag_view3d_redraw()
        self.report({'INFO'}, f"Removed '{entry['name']}' from Favorites")
        return {'FINISHED'}


def draw_asset_shelf(layout, context):
    wm = context.window_manager
    ensure_assets_loaded(context)
    load_favorites()

    # A single compact row for search, catalog, labels, and refresh.
    controls = layout.row(align=True)
    controls.prop(wm, "ts_brush_search", text="", icon='VIEWZOOM')
    controls.prop(wm, "ts_brush_catalog", text="", icon='DOWNARROW_HLT')
    controls.prop(wm, "ts_brush_show_names", text="Names", icon='FONT_DATA', toggle=True)
    controls.operator("ts_asset_shelf.refresh", text="", icon='FILE_REFRESH')

    assets = get_filtered_assets(context)
    if not assets:
        layout.label(text="No brushes found", icon='INFO')
    else:
        layout.template_icon_view(
            wm,
            "ts_brush_choice",
            show_labels=wm.ts_brush_show_names,
            scale=4.0,
            scale_popup=4.0,
        )

    entry = get_current_brush_entry(context)
    if entry is not None:
        favorite_row = layout.row(align=True)
        if is_favorite(entry):
            favorite_row.operator(
                "ts_asset_shelf.remove_favorite",
                text="Remove from Favorites",
                icon='REMOVE',
            )
            disabled_add = favorite_row.row(align=True)
            disabled_add.enabled = False
            disabled_add.operator(
                "ts_asset_shelf.add_favorite",
                text="Add to Favorites",
                icon='ADD',
            )
        else:
            favorite_row.operator(
                "ts_asset_shelf.add_favorite",
                text="Add to Favorites",
                icon='ADD',
            )
            disabled_remove = favorite_row.row(align=True)
            disabled_remove.enabled = False
            disabled_remove.operator(
                "ts_asset_shelf.remove_favorite",
                text="Remove from Favorites",
                icon='REMOVE',
            )

    layout.label(text=f"{len(assets)} brushes", icon='BRUSH_DATA')


class TS_ASSET_SHELF_PT_sidebar(bpy.types.Panel):
    """Touchscreen brush shelf in the 3D View sidebar, including GP modes."""
    bl_label = "Touchscreen Asset Shelf"
    bl_idname = "TS_ASSET_SHELF_PT_sidebar"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Tool"

    @classmethod
    def poll(cls, context):
        return context.mode in MODE_SETTINGS or is_grease_pencil_mode(context)

    def draw(self, context):
        draw_asset_shelf(self.layout, context)


class TS_ASSET_SHELF_PT_image_editor(bpy.types.Panel):
    """Same shelf in Image Editor paint contexts."""
    bl_label = "Touchscreen Asset Shelf"
    bl_idname = "TS_ASSET_SHELF_PT_image_editor"
    bl_space_type = 'IMAGE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Tool"

    @classmethod
    def poll(cls, context):
        # Image Editor exposes texture painting through PAINT_TEXTURE in
        # supported Blender versions. The fallback checks the editor's mode.
        return context.mode in MODE_SETTINGS and context.mode in {'PAINT_TEXTURE'}

    def draw(self, context):
        draw_asset_shelf(self.layout, context)


# ============================================================
# REGISTRO
# ============================================================

CLASSES = (
    TS_ASSET_SHELF_OT_activate_brush,
    TS_ASSET_SHELF_OT_refresh,
    TS_ASSET_SHELF_OT_add_favorite,
    TS_ASSET_SHELF_OT_remove_favorite,
    TS_ASSET_SHELF_PT_sidebar,
    TS_ASSET_SHELF_PT_image_editor,
)


def unregister():
    restore_native_brush_selector()
    global ASSET_CACHE, CATALOG_ITEMS, CATALOG_ENUM_ITEMS
    global CACHE_MODE, ASSETS_LOADED, BRUSH_ENUM_ITEMS, BRUSH_ENUM_MAP
    global FAVORITE_KEYS, FAVORITES_LOADED

    for prop_name in (
        "ts_brush_catalog",
        "ts_brush_search",
        "ts_brush_show_names",
        "ts_brush_choice",
    ):
        if hasattr(bpy.types.WindowManager, prop_name):
            delattr(bpy.types.WindowManager, prop_name)

    for cls in reversed(CLASSES):
        try:
            bpy.utils.unregister_class(cls)
        except (RuntimeError, ValueError):
            pass

    ASSET_CACHE = []
    CATALOG_ITEMS = {}
    CATALOG_ENUM_ITEMS = []
    CACHE_MODE = None
    ASSETS_LOADED = False
    BRUSH_ENUM_ITEMS = []
    BRUSH_ENUM_MAP = {}
    FAVORITE_KEYS = set()
    FAVORITES_LOADED = False


def register():
    unregister()
    load_favorites()
    rebuild_catalog_enum_items()

    bpy.types.WindowManager.ts_brush_catalog = (
        bpy.props.EnumProperty(
            name="Catalog",
            description="Filter brushes by asset catalog",
            items=catalog_enum_items,
            update=on_catalog_update,
        )
    )

    bpy.types.WindowManager.ts_brush_search = (
        bpy.props.StringProperty(
            name="Search Brushes",
            description="Filter brushes by name",
            default="",
            options={'TEXTEDIT_UPDATE'},
            update=on_brush_search_update,
        )
    )

    bpy.types.WindowManager.ts_brush_show_names = (
        bpy.props.BoolProperty(
            name="Show Names",
            description="Show or hide brush names below thumbnails",
            default=True,
            update=on_show_names_update,
        )
    )

    bpy.types.WindowManager.ts_brush_choice = (
        bpy.props.EnumProperty(
            name="Brushes",
            description="Select and activate a brush",
            items=brush_choice_items,
            update=on_brush_choice_update,
            options={'SKIP_SAVE'},
        )
    )

    for cls in CLASSES:
        try:
            bpy.utils.register_class(cls)

        except (RuntimeError, ValueError) as exc:
            print(
                "[Touchscreen] Error registrando",
                cls.__name__,
                repr(exc),
            )
            unregister()
            return

    load_favorites()
    print("[Touchscreen] Persistent Touchscreen Asset Shelf registered.")


if __name__ == "__main__":
    register()