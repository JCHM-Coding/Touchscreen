import bpy

# =========================================================================
# 1. ESTRUCTURA DE DATOS DINÁMICA POR MODO
# =========================================================================

class DynamicFavoriteItem(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="Nombre")
    operator_id: bpy.props.StringProperty(name="Operador Blender")
    mode: bpy.props.StringProperty(name="Modo de Origen")

class AddonFavoritesProperties(bpy.types.PropertyGroup):
    all_favorites: bpy.props.CollectionProperty(type=DynamicFavoriteItem)

def get_favorites_for_current_mode(context):
    """Filtra y devuelve solo los favoritos que coinciden exactamente con el modo activo."""
    if not hasattr(context, "scene") or not context.scene:
        return []
        
    props = getattr(context.scene, "my_addon_favorites", None)
    if not props:
        return []
        
    current_mode = context.mode
    return [(i, item) for i, item in enumerate(props.all_favorites) if item.mode == current_mode]


# =========================================================================
# 2. OPERADORES (AÑADIR, EJECUTAR, ELIMINAR, DESHACER/REHACER)
# =========================================================================

class MYADDON_OT_quick_undo(bpy.types.Operator):
    """Deshacer última acción"""
    bl_idname = "myaddon.quick_undo"
    bl_label = "Deshacer"
    
    def execute(self, context):
        try:
            bpy.ops.ed.undo()
        except Exception:
            pass
        return {'FINISHED'}

class MYADDON_OT_quick_redo(bpy.types.Operator):
    """Rehacer última acción"""
    bl_idname = "myaddon.quick_redo"
    bl_label = "Rehacer"
    
    def execute(self, context):
        try:
            bpy.ops.ed.redo()
        except Exception:
            pass
        return {'FINISHED'}

class MYADDON_OT_add_current_op(bpy.types.Operator):
    """Añadir favorito directamente al modo actual"""
    bl_idname = "myaddon.add_current_op"
    bl_label = "Añadir a Favoritos del Modo"
    
    name: bpy.props.StringProperty(name="Nombre del Botón", default="Mi Acción")
    operator_id: bpy.props.StringProperty(name="Operador (ej: object.select_all)", default="")

    def execute(self, context):
        if not self.operator_id:
            self.report({'WARNING'}, "Debes ingresar el identificador del operador")
            return {'CANCELLED'}
            
        props = context.scene.my_addon_favorites
        item = props.all_favorites.add()
        item.name = self.name
        item.operator_id = self.operator_id.strip()
        item.mode = context.mode
        
        self.report({'INFO'}, f"Favorito añadido a {context.mode}")
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

class MYADDON_OT_execute_favorite(bpy.types.Operator):
    """Ejecutar el operador del favorito de forma segura"""
    bl_idname = "myaddon.execute_favorite"
    bl_label = "Ejecutar Favorito"
    
    operator_id: bpy.props.StringProperty()

    def execute(self, context):
        if not self.operator_id:
            return {'CANCELLED'}
        try:
            # Dividir el identificador "modulo.operador" de forma segura sin usar eval()
            parts = self.operator_id.split(".")
            if len(parts) == 2:
                module, op_name = parts
                op_func = getattr(getattr(bpy.ops, module, None), op_name, None)
                if op_func:
                    op_func()
                    return {'FINISHED'}
            self.report({'ERROR'}, f"Operador no válido: '{self.operator_id}'")
        except Exception as e:
            self.report({'ERROR'}, f"Error ejecutando '{self.operator_id}': {e}")
        return {'CANCELLED'}

class MYADDON_OT_remove_favorite(bpy.types.Operator):
    """Eliminar favorito"""
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
# 3. INTERFAZ: TOOLBAR (HEADER) Y N-PANEL
# =========================================================================

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
            layout.label(text="Quitar favoritos de este modo:")
            for real_idx, item in filtered_favs:
                op = layout.operator("myaddon.remove_favorite", text=f"Eliminar: {item.name}", icon='TRASH')
                op.real_index = real_idx


def draw_toolbar_favorites(self, context):
    """Función de renderizado para el Header/Toolbar del Viewport"""
    layout = self.layout
    filtered_favs = get_favorites_for_current_mode(context)
    
    layout.separator()
    
    # Controles de Undo / Redo
    row_quick = layout.row(align=True)
    row_quick.operator("myaddon.quick_undo", text="", icon='LOOP_BACK')
    row_quick.operator("myaddon.quick_redo", text="", icon='LOOP_FORW')
    
    layout.separator()

    # Dibuja solo los favoritos del modo actual
    for real_idx, item in filtered_favs:
        row = layout.row(align=True)
        op_exec = row.operator("myaddon.execute_favorite", text=item.name)
        op_exec.operator_id = item.operator_id

    # Menú desplegable para añadir/borrar sin salir del Viewport
    layout.menu("MYADDON_MT_favorites_menu", text="", icon='DOWNARROW_HLT')


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
        box.operator("myaddon.add_current_op", text="Añadir Favorito", icon='ADD')

        layout.separator()

        if not filtered_favs:
            layout.label(text="No hay favoritos guardados para este modo.")
        else:
            for real_idx, item in filtered_favs:
                row = layout.row(align=True)
                
                op_exec = row.operator("myaddon.execute_favorite", text=item.name)
                op_exec.operator_id = item.operator_id
                
                op_del = row.operator("myaddon.remove_favorite", text="", icon='X')
                op_del.real_index = real_idx


# =========================================================================
# 4. REGISTRO
# =========================================================================

classes = (
    DynamicFavoriteItem,
    AddonFavoritesProperties,
    MYADDON_OT_quick_undo,
    MYADDON_OT_quick_redo,
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
    if hasattr(bpy.types.Scene, "my_addon_favorites"):
        del bpy.types.Scene.my_addon_favorites
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()