import bpy

# =========================================================================
# 1. PROPIEDADES Y ESTRUCTURA DE DATOS
# =========================================================================

class FavoriteItem(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="Nombre", default="Favorito")
    command: bpy.props.StringProperty(name="Operador (ej: object.select_all)", default="object.select_all")

class AddonFavoritesProperties(bpy.types.PropertyGroup):
    object_favorites: bpy.props.CollectionProperty(type=FavoriteItem)
    edit_favorites: bpy.props.CollectionProperty(type=FavoriteItem)
    
    object_fav_index: bpy.props.IntProperty()
    edit_fav_index: bpy.props.IntProperty()

def get_current_favorites(context):
    """Devuelve la colección y los identificadores según el modo activo."""
    props = context.scene.my_addon_favorites
    if context.mode.startswith('EDIT'):
        return props.edit_favorites, props, "edit_fav_index"
    return props.object_favorites, props, "object_fav_index"


# =========================================================================
# 2. OPERADORES
# =========================================================================

# --- Operadores de Acción Rápida (Touch / Workspace Helper) ---
class MYADDON_OT_quick_undo(bpy.types.Operator):
    """Deshacer última acción"""
    bl_idname = "myaddon.quick_undo"
    bl_label = "Deshacer"
    
    def execute(self, context):
        bpy.ops.ed.undo()
        return {'FINISHED'}

class MYADDON_OT_quick_redo(bpy.types.Operator):
    """Rehacer última acción"""
    bl_idname = "myaddon.quick_redo"
    bl_label = "Rehacer"
    
    def execute(self, context):
        bpy.ops.ed.redo()
        return {'FINISHED'}

class MYADDON_OT_quick_delete(bpy.types.Operator):
    """Eliminar selección activa"""
    bl_idname = "myaddon.quick_delete"
    bl_label = "Borrar"
    
    def execute(self, context):
        if context.mode.startswith('EDIT'):
            bpy.ops.mesh.delete(type='VERT')
        else:
            bpy.ops.object.delete(use_global=False)
        return {'FINISHED'}


# --- Operadores de Gestión de Favoritos ---
class MYADDON_OT_execute_favorite(bpy.types.Operator):
    """Ejecutar el comando del favorito"""
    bl_idname = "myaddon.execute_favorite"
    bl_label = "Ejecutar Favorito"
    
    command: bpy.props.StringProperty()

    def execute(self, context):
        if not self.command:
            self.report({'WARNING'}, "Sin comando asignado")
            return {'CANCELLED'}
        try:
            python_code = f"bpy.ops.{self.command}()"
            exec(python_code)
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Error ejecutando {self.command}: {e}")
            return {'CANCELLED'}

class MYADDON_OT_add_favorite(bpy.types.Operator):
    """Añadir favorito al modo actual"""
    bl_idname = "myaddon.add_favorite"
    bl_label = "Añadir Favorito"
    
    item_name: bpy.props.StringProperty(name="Nombre del Botón", default="Mi Favorito")
    item_command: bpy.props.StringProperty(name="Operador (ej: object.select_all)", default="object.select_all")

    def execute(self, context):
        fav_collection, props, index_prop = get_current_favorites(context)
        item = fav_collection.add()
        item.name = self.item_name
        item.command = self.item_command
        
        setattr(props, index_prop, len(fav_collection) - 1)
        
        mode_str = "Edit Mode" if context.mode.startswith('EDIT') else "Object Mode"
        self.report({'INFO'}, f"Favorito añadido a {mode_str}")
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

class MYADDON_OT_remove_favorite(bpy.types.Operator):
    """Eliminar favorito del modo activo"""
    bl_idname = "myaddon.remove_favorite"
    bl_label = "Quitar Favorito"
    
    index: bpy.props.IntProperty(default=-1)

    def execute(self, context):
        fav_collection, props, index_prop = get_current_favorites(context)
        target_index = self.index if self.index >= 0 else getattr(props, index_prop)
        
        if 0 <= target_index < len(fav_collection):
            fav_collection.remove(target_index)
            setattr(props, index_prop, max(0, target_index - 1))
            self.report({'INFO'}, "Favorito eliminado")
            return {'FINISHED'}
            
        self.report({'WARNING'}, "No hay elemento seleccionado")
        return {'CANCELLED'}


# =========================================================================
# 3. MENÚS Y COMPONENTES DE INTERFAZ
# =========================================================================

class MYADDON_MT_favorites_menu(bpy.types.Menu):
    bl_label = "Gestionar Favoritos"
    bl_idname = "MYADDON_MT_favorites_menu"

    def draw(self, context):
        layout = self.layout
        fav_collection, _, _ = get_current_favorites(context)
        
        layout.operator("myaddon.add_favorite", text="Añadir Nuevo...", icon='ADD')
        layout.separator()
        
        if len(fav_collection) == 0:
            layout.label(text="Sin favoritos en este modo")
        else:
            layout.label(text="Borrar favorito:")
            for i, item in enumerate(fav_collection):
                op = layout.operator("myaddon.remove_favorite", text=f"Eliminar: {item.name}", icon='TRASH')
                op.index = i


# Panel Lateral N-Panel
class MYADDON_PT_interface_helper(bpy.types.Panel):
    bl_label = "Interface & Touch Helper"
    bl_idname = "MYADDON_PT_interface_helper"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Favoritos'

    def draw(self, context):
        layout = self.layout
        
        # --- Sección 1: Accesos Rápidos Táctiles ---
        box = layout.box()
        box.label(text="Acciones Rápidas", icon='HAND')
        row = box.row(align=True)
        row.operator("myaddon.quick_undo", text="Undo", icon='LOOP_BACK')
        row.operator("myaddon.quick_redo", text="Redo", icon='LOOP_FORW')
        row.operator("myaddon.quick_delete", text="Delete", icon='TRASH')

        layout.separator()

        # --- Sección 2: Favoritos del Modo Activo ---
        fav_collection, _, _ = get_current_favorites(context)
        mode_label = "Modo Edición" if context.mode.startswith('EDIT') else "Modo Objeto"
        
        box_fav = layout.box()
        header_row = box_fav.row()
        header_row.label(text=f"Favoritos ({mode_label})", icon='BOOKMARK')
        header_row.operator("myaddon.add_favorite", text="", icon='ADD')

        if len(fav_collection) == 0:
            box_fav.label(text="Lista vacía para este modo.", icon='INFO')
        else:
            for i, item in enumerate(fav_collection):
                row = box_fav.row(align=True)
                
                # Botón de Ejecutar
                op_exec = row.operator("myaddon.execute_favorite", text=item.name)
                op_exec.command = item.command
                
                # Botón de Borrar (X)
                op_rem = row.operator("myaddon.remove_favorite", text="", icon='X')
                op_rem.index = i


# Función de dibujo para el Header / Toolbar Superior
def draw_toolbar_favorites(self, context):
    layout = self.layout
    fav_collection, _, _ = get_current_favorites(context)
    
    layout.separator()
    
    # Accesos rápidos en la barra
    row_quick = layout.row(align=True)
    row_quick.operator("myaddon.quick_undo", text="", icon='LOOP_BACK')
    row_quick.operator("myaddon.quick_redo", text="", icon='LOOP_FORW')
    
    layout.separator()

    # Botones de Favoritos del Modo Activo
    for item in fav_collection:
        op = layout.operator("myaddon.execute_favorite", text=item.name)
        op.command = item.command

    # Menú desplegable para añadir/borrar rápidamente
    layout.menu("MYADDON_MT_favorites_menu", text="", icon='DOWNARROW_HLT')


# =========================================================================
# 4. REGISTRO DEL ADDON
# =========================================================================

classes = (
    FavoriteItem,
    AddonFavoritesProperties,
    MYADDON_OT_quick_undo,
    MYADDON_OT_quick_redo,
    MYADDON_OT_quick_delete,
    MYADDON_OT_execute_favorite,
    MYADDON_OT_add_favorite,
    MYADDON_OT_remove_favorite,
    MYADDON_MT_favorites_menu,
    MYADDON_PT_interface_helper,
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