import bpy

# ############################################################
# User Interface
# ############################################################

class VirtualRealityPanel(bpy.types.Panel):
    bl_label = "Head Mounted Display"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_category = 'Virtual Reality'

    @staticmethod
    def draw(self, context):
        layout = self.layout

        col = layout.column()
        col.operator("view3d.virtual_reality_toggle", text="Virtual Reality Preview", icon="PLAY")

        col.separator()
        wm = context.window_manager

        if wm.virtual_reality.is_enabled:
            col.operator("view3d.virtual_reality_sandbox", text="Virtual Reality", icon="X").action='DISABLE'
        else:
            col.operator("view3d.virtual_reality_sandbox", text="Virtual Reality", icon="PLAY").action='ENABLE'


# ############################################################
# Un/Registration
# ############################################################

def register():
    bpy.utils.register_class(VirtualRealityPanel)


def unregister():
    bpy.utils.unregister_class(VirtualRealityPanel)
