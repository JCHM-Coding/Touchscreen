import bpy

# =========================================================================
# 1. ESTRUCTURA DE DATOS DINÁMICA POR MODO
# =========================================================================

class DynamicFavoriteItem(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="Nombre")
    operator_id: bpy.props.StringProperty(name="Operador Blender")
    mode: bpy.props.StringProperty(name="Modo de Origen")

class AddonFavoritesProperties(bpy.types.PropertyGroup):
    # Colección global donde cada ítem sabe a qué modo pertenece
    all_favorites: bpy.props.CollectionProperty(type=DynamicFavoriteItem)

def get_favorites_for_current_mode(context):
    """Filtra y devuelve solo los favoritos del modo activo del Viewport."""
    props = context.scene.my_addon_favorites
    current_mode = context.mode
    
    # Devuelve lista de tuplas (índice_real, elemento)
    filtered = [(i, item) for i, item in enumerate(props.all_favorites) if item.mode == current_mode]
    return filtered


# =========================================================================
# 2. OPERADORES: AÑADIR, EJECUTAR Y ELIMINAR DESDE EL PROGRAMA
# =========================================================================

class MYADDON_OT_add_current_op(bpy.types.Operator):
    """Añadir una acción rápida al modo actual directamente desde la interfaz"""
    bl_idname = "myaddon.add_current_op"
    bl_label = "Añadir a Favoritos del Modo"
    
    name: bpy.props.StringProperty(name="Nombre del Botón", default="Mi Acción")
    operator_id: bpy.props.StringProperty(name="Identificador del Operador (ej: sculpt.expand)", default="")

    def execute(self, context):
        if not self.operator_id:
            self.report({'WARNING'}, "Se requiere el identificador de un operador")
            return {'CANCELLED'}
            
        props = context.scene.my_addon_favorites
        item = props.all_favorites.add()
        item.name = self.name
        item.operator_id = self.operator_id
        item.mode = context.mode  # Guarda el modo exacto activo ("SCULPT", "EDIT_MESH", "OBJECT", etc.)
        
        self.report({'INFO'}, f"Añadido a favoritos de {context.mode}")
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)


class MYADDON_OT_execute_favorite(bpy.types.Operator):
    """Ejecutar favorito asignado"""
    bl_idname = "myaddon.execute_favorite"
    bl_label = "Ejecutar Favorito"
    
    operator_id: bpy.props.StringProperty()

    def execute(self, context):
        if not self.operator_id:
            return {'CANCELLED'}
        try:
            # Soportar llamadas tipo "sculpt.expand" u "object.select_all"
            eval(f"bpy.ops.{self.operator_id}()")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Error al ejecutar '{self.operator_id}': {e}")
            return {'CANCELLED'}


class MYADDON_OT_remove_favorite(bpy.types.Operator):
    """Quitar elemento de los favoritos"""
    bl_idname = "myaddon.remove_favorite"
    bl_label = "Eliminar Favorito"
    
    real_index: bpy.props.IntProperty()

    def execute(self, context):
        props = context.scene.my_addon_favorites
        if 0 <= self.real_index < len(props.all_favorites):
            props.all_favorites.remove(self.real_index)
            self.report({'INFO'}, "Favorito eliminado")
            return {'FINISHED'}
        return {'CANCELLED'}


# =========================================================================
# 3. INTERFAZ: TOOLBAR Y N-PANEL FILTRADOS POR CONTEXT.MODE
# =========================================================================

# Menú contextual/desplegable rápido en el Header
class MYADDON_MT_favorites_menu(bpy.types.Menu):
    bl_label = "Gestión de Favoritos"
    bl_idname = "MYADDON_MT_favorites_menu"

    def draw(self, context):
        layout = self.layout
        filtered_favs = get_favorites_for_current_mode(context)
        
        layout.operator("myaddon.add_current_op", text=f"Añadir Favorito a {context.mode}", icon='ADD')
        layout.separator()
        
        if not filtered_favs:
            layout.label(text=f"Sin favoritos en {context.mode}")
        else:
            layout.label(text="Borrar favoritos de este modo:")
            for real_idx, item in filtered_favs:
                op = layout.operator("myaddon.remove_favorite", text=f"Eliminar: {item.name}", icon='TRASH')
                op.real_index = real_idx


# Dibujo en la Barra Superior (Header / Toolbar)
def draw_toolbar_favorites(self, context):
    layout = self.layout
    filtered_favs = get_favorites_for_current_mode(context)
    
    layout.separator()
    
    # Controles de Undo / Redo rápidos
    row_quick = layout.row(align=True)
    row_quick.operator("ed.undo", text="", icon='LOOP_BACK')
    row_quick.operator("ed.redo", text="", icon='LOOP_FORW')
    
    layout.separator()

    # Dibuja ÚNICAMENTE los favoritos que coinciden con context.mode
    for real_idx, item in filtered_favs:
        row = layout.row(align=True)
        op_exec = row.operator("myaddon.execute_favorite", text=item.name)
        op_exec.operator_id = item.operator_id

    # Menú para agregar/eliminar sin salir de la vista
    layout.menu("MYADDON_MT_favorites_menu", text="", icon='DOWNARROW_HLT')


# Dibujo en el N-Panel
class MYADDON_PT_favorites_npanel(bpy.types.Panel):
    bl_label = "Favoritos por Modo"
    bl_idname = "MYADDON_PT_favorites_npanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Favoritos'

    def draw(self, context):
        layout = self.layout
        current_mode = context.mode
        filtered_favs = get_favorites_for_current_mode(context)
        
        box = layout.box()
        box.label(text=f"Modo Activo: {current_mode}", icon='VIEW3D')
        
        row_add = box.row()
        row_add.operator("myaddon.add_current_op", text="Añadir Favorito", icon='ADD')

        layout.separator()

        if not filtered_favs:
            layout.label(text="No hay favoritos guardados para este modo.")
        else:
            for real_idx, item in filtered_favs:
                row = layout.row(align=True)
                
                # Ejecutar
                op_exec = row.operator("myaddon.execute_favorite", text=item.name)
                op_exec.operator_id = item.operator_id
                
                # Borrar directo (X)
                op_del = row.operator("myaddon.remove_favorite", text="", icon='X')
                op_del.real_index = real_idx


# =========================================================================
# 4. REGISTRO
# =========================================================================

classes = (
    DynamicFavoriteItem,
    AddonFavoritesProperties,
    MYADDON_OT_add_current_op,
    MYADDON_OT_execute_favorite,
    MYADDON_OT_remove_favorite,
    MYADDON_MT_favorites_menu,
    MYADDON_PT_favorites_npanel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
        
    bpy.types.Scene.my_addon_favorites = bpy.props.PointerProperty(type=AddonFavoritesProperties)
    bpy.types.VIEW3D_HT_header.append(draw_toolbar_favorites)

def unregister():
    bpy.types.VIEW3D_HT_header.remove(draw_toolbar_favorites)
    del bpy.types.Scene.my_addon_favorites
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()