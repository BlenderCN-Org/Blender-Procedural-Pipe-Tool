# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

# <pep8 compliant>


import bpy
from bpy.app.handlers import load_post, persistent
from bpy.props import (BoolProperty, FloatProperty, FloatVectorProperty,
                       IntProperty, PointerProperty, StringProperty)
from bpy.types import Object, Operator, Panel, PropertyGroup
from bpy.utils import register_class, unregister_class
from bpy_extras.object_utils import AddObjectHelper, object_data_add
from mathutils import Vector

bl_info = {
    "name": "Procedural Pipe Tool",
    "description": "",
    "author": "Oleg Stepanov",
    "version": (1, 0, 0),
    "blender": (2, 80, 0),
    "location": "View3D > Sidebar",
    "warning": "",
    "wiki_url": "",
    "support": 'COMMUNITY',
    "category": "Object"
}


class PPT_PT_panel(Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Procedural Pipe Tool"
    bl_category = "Procedural Pipe Tool"

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.scale_y = 1.2
        col.operator(PPT_OT_CreateNewPipe.bl_idname, icon='IPO_CONSTANT')

        if (context.active_object):
            ob = context.active_object
            ppt_props = ob.ppt_props

            if ob.select_get() and ppt_props.is_pipe:
                col.separator()
                col.prop(ob, 'name', text="", icon='OUTLINER_DATA_FONT')

                col.split()
                col.enabled = len(context.selected_objects) == 1
                col.prop(ppt_props, 'edit_mode', toggle=True,
                         text="Edit Mode", icon='PARTICLE_POINT')

                if not ppt_props.edit_mode:
                    col = layout.column(align=True)
                    col.separator()
                    col.label(text="Parameters:")
                    col.prop(ppt_props, 'radius')
                    col.prop(ppt_props, 'bevel_radius')
                    col = layout.column(align=True)
                    col.prop(ppt_props, 'bevel_segments')
                    col.prop(ppt_props, 'radius_segments')
                    col = layout.column(align=True)
                    col.prop(ppt_props, 'fill_caps')

                return

        layout.separator()
        layout.label(text="Select Pipe to Edit", icon='ERROR')
        layout.separator()


class PPT_OT_CreateNewPipe(Operator, AddObjectHelper):
    """ """
    bl_idname = "object.ppt_op_create_new_pipe"
    bl_label = "Create New Pipe"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            return True

    def execute(self, context):
        verts = [Vector((-0.5, 0.0, 0.0)), Vector((0.5, 0.0, 0.0))]
        edges = [[0, 1]]
        mesh = bpy.data.meshes.new(name="Pipe")
        mesh.from_pydata(verts, edges, [])
        ob = object_data_add(context, mesh, operator=self)
        bpy.ops.object.ppt_op_convert_to_pipe()
        ob.ppt_props.is_pipe = True

        bpy.ops.window_manager.ppt_op_listen_for_keys('INVOKE_DEFAULT')

        return {'FINISHED'}


class PPT_OT_ConvertToPipe(Operator):
    """ """
    bl_idname = "object.ppt_op_convert_to_pipe"
    bl_label = "Convert to Pipe"
    bl_options = {'UNDO_GROUPED', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        if context.active_object and (context.active_object.type == 'MESH'):
            return True

    def execute(self, context):
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.mode_set(mode='EDIT')

        # Store line object
        verts = []
        edges = []

        ob = context.active_object
        ppt_props = ob.ppt_props

        verts = [vert.co for vert in ob.data.vertices]
        edges = [[edge.vertices[0], edge.vertices[1]]
                 for edge in ob.data.edges]

        ppt_props.verts = str(verts)
        ppt_props.edges = str(edges)

        active_material = ob.active_material

        # Convert to pipe
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.bevel(offset=ppt_props.bevel_radius, offset_pct=0,
                           segments=ppt_props.bevel_segments, vertex_only=True)
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.convert(target='CURVE')
        ob.data.use_fill_caps = ppt_props.fill_caps

        for spline in ob.data.splines:
            spline.use_smooth = True

        if len(ob.children) > 0:
            circle = ob.children[0]
        else:
            circle = create_circle(context, ob, ppt_props)

        circle.data.resolution_u = (
            round(ppt_props.radius_segments) - 4) / 2

        ob.data.bevel_object = circle

        if active_material is not None:
            ob.data.materials.append(active_material)

        return {'FINISHED'}


class PPT_OT_ConvertToMesh(Operator):
    """ """
    bl_idname = "object.ppt_op_convert_to_mesh"
    bl_label = "Convert to Mesh"
    bl_options = {'UNDO_GROUPED', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        if context.active_object and (context.active_object.type == 'CURVE'):
            return True

    def execute(self, context):
        verts = []
        edges = []

        ob = context.active_object
        ppt_props = ob.ppt_props

        verts = eval(ppt_props.verts)
        edges = eval(ppt_props.edges)

        active_material = ob.active_material

        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.convert(target='MESH')
        mesh = bpy.data.meshes.new(name=ob.name)
        mesh.from_pydata(verts, edges, [])
        ob.data = mesh

        if active_material is not None:
            ob.data.materials.append(active_material)

        return {'FINISHED'}


class PPT_OT_ListenForKeys(Operator):
    """ """
    bl_idname = "window_manager.ppt_op_listen_for_keys"
    bl_label = "Lesten For Keys"

    is_mod_key: BoolProperty(default=False)

    def modal(self, context, event):
        if event.type in ('LEFT_CTRL', 'LEFT_SHIFT', 'LEFT_ALT'):
            self.is_mod_key = True
            bpy.app.timers.register(self.reset_mod_key, first_interval=0.1)
        elif (event.shift or event.ctrl):
            pass
        elif (event.type == 'TAB' and event.value == 'RELEASE' and
              self.is_mod_key is False and len(context.selected_objects) == 1):
            ob = context.active_object

            if ob.ppt_props.is_pipe:
                edit_mode = ob.ppt_props.edit_mode
                ob.ppt_props.edit_mode = not edit_mode
                return {'FINISHED'}

        return {'PASS_THROUGH'}

    def reset_mod_key(self):
        self.is_mod_key = False

    def invoke(self, context, event):
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}


def create_circle(context, ob, ppt_props):
    ob_colection = context.active_object.users_collection[0]

    layer_collection = context.view_layer.layer_collection
    context.view_layer.active_layer_collection = get_layer_collection(
        layer_collection, ob_colection.name)

    bpy.ops.curve.primitive_bezier_circle_add(
        radius=1, enter_editmode=False, location=ob.location)
    circle = context.active_object
    radius = ppt_props.radius
    circle.scale = Vector((radius, radius, radius))
    circle.parent = ob
    circle.hide_render = True
    circle.hide_viewport = True
    circle.select_set(False)
    ob.select_set(True)
    context.view_layer.objects.active = ob

    return circle


def update_destructive(self, context):
    if context.active_object.type == 'CURVE':
        bpy.ops.object.ppt_op_convert_to_mesh()
        bpy.ops.object.ppt_op_convert_to_pipe()


def get_layer_collection(layer_colection, name):
    found = None
    if (layer_colection.name == name):
        return layer_colection
    for layer in layer_colection.children:
        found = get_layer_collection(layer, name)
        if found:
            return found


def update_non_destructive(self, context):
    ob = context.active_object

    if ob.type == 'CURVE':
        ppt_props = ob.ppt_props

        if len(ob.children) > 0:
            circle = ob.children[0]
        else:
            circle = create_circle(context, ob, ppt_props)
            ob.data.bevel_object = circle

        circle.data.resolution_u = (
            round(ppt_props.radius_segments) - 4) / 2
        radius = ppt_props.radius
        circle.scale = Vector((radius, radius, radius))
        ob.data.use_fill_caps = ppt_props.fill_caps


def update_edit_mode(self, context):
    ob = context.active_object
    ppt_props = ob.ppt_props

    if ppt_props.edit_mode:
        bpy.ops.object.ppt_op_convert_to_mesh()
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.mesh.select_mode(type='VERT')
    else:
        bpy.ops.object.ppt_op_convert_to_pipe()
        bpy.ops.object.mode_set(mode='OBJECT')

    bpy.ops.window_manager.ppt_op_listen_for_keys('INVOKE_DEFAULT')


class PPT_Props(PropertyGroup):
    is_pipe: BoolProperty(default=False)
    edit_mode: BoolProperty(default=False, update=update_edit_mode)

    radius: FloatProperty(name="Pipe Radius", default=0.25,
                          min=0.0, subtype='DISTANCE', update=update_non_destructive)
    bevel_radius: FloatProperty(name="Bevel Radius", default=0.45,
                                min=0.0, subtype='DISTANCE', update=update_destructive)

    bevel_segments: IntProperty(
        name="Bevel Segments", default=4, min=1, max=16, update=update_destructive)
    radius_segments: FloatProperty(
        name="Radius Segments", default=8, min=4, max=16, step=400, precision=0, update=update_non_destructive)

    fill_caps: BoolProperty(name="Fill Caps", default=False,
                            update=update_non_destructive)

    verts: StringProperty()
    edges: StringProperty()


classes = (
    PPT_PT_panel,
    PPT_OT_ConvertToPipe,
    PPT_OT_ConvertToMesh,
    PPT_OT_CreateNewPipe,
    PPT_OT_ListenForKeys,
    PPT_Props,
)


@persistent
def load_handler(dummy):
    bpy.ops.window_manager.ppt_op_listen_for_keys('INVOKE_DEFAULT')


def register():
    for cls in classes:
        register_class(cls)

    bpy.types.Object.ppt_props = PointerProperty(type=PPT_Props)
    load_post.append(load_handler)


def unregister():
    load_post.remove(load_handler)

    for cls in classes:
        unregister_class(cls)


if __name__ == "__main__":
    register()
