import bpy

from bpy.app.handlers import persistent

TODO = True

from .opengl_helper import (
        create_framebuffer,
        delete_framebuffer,
        draw_rectangle,
        draw_rectangle_rainbow,
        view_reset,
        view_setup,
        )

from bgl import *


class GLdata:
    def __init__(self):
        self.color_tex = -1
        self.fb = -1
        self.rb = -1
        self.size = 0

global _time
_time = 0

class VirtualRealitySandboxOperator(bpy.types.Operator):
    """"""
    bl_idname = "view3d.virtual_reality_sandbox"
    bl_label = "Toggle Virtual Reality Sandbox"
    bl_description = ""

    _gl_data = None
    _timer = None
    _handle = None
    _width = 1920
    _height = 1080

    action = bpy.props.EnumProperty(
        description="",
        items=(("ENABLE", "Enable", "Enable"),
               ("DISABLE", "Disable", "Disable"),
               ),
        default="DISABLE",
        options={'SKIP_SAVE'},
        )

    @classmethod
    def poll(cls, context):
        return context.area.type == 'VIEW_3D'

    def modal(self, context, event):
        wm = context.window_manager

        if not wm.virtual_reality.is_enabled:
            self._quit_doit(context)
            context.area.tag_redraw()
            return {'FINISHED'}

        if event.type == 'TIMER':
            self._fbo_run()
            # this redraw is only required for the visualization
            context.area.tag_redraw()

        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        wm = context.window_manager
        vr = wm.virtual_reality

        is_enabled = vr.is_enabled

        if self.action == 'DISABLE':
            if vr.is_enabled:
                self._quit(context)
                return {'FINISHED'}
            else:
                self.report({'ERROR'}, "Virtual Reality is not enabled")
                return {'CANCELLED'}

        else: # ENABLE
            if vr.is_enabled:
                self.report({'ERROR'}, "Virtual Reality is already enabled")
                return {'CANCELLED'}

            self._init(context, self._width, self._height)
            return {'RUNNING_MODAL'}

        return {'CANCELLED'}

    def _quit(self, context):
        """garbage collect"""

        # change it so the original modal operator will clean things up
        wm = context.window_manager
        wm.virtual_reality.is_enabled = False

    def _quit_doit(self, context):
        """actual quit"""
        wm = context.window_manager

        if self._timer:
            wm.event_timer_remove(self._timer)
            del self._timer

        if self._handle:
            bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            del self._handle

        self._fbo_delete()

    def _init(self, context, width, height):
        wm = context.window_manager
        wm.virtual_reality.is_enabled = True

        # setup modal
        self._timer = wm.event_timer_add(1.0 / 75.0, context.window) # 75 Hz
        self._handle = bpy.types.SpaceView3D.draw_handler_add(self._draw_callback_px, (context,), 'WINDOW', 'POST_PIXEL')
        wm.modal_handler_add(self)

        # initialize opengl data
        self._gl_data = GLdata()
        self._fbo_setup()

    def _fbo_setup(self):
        gl_data = self._gl_data
        size = 128

        id_buf = Buffer(GL_INT, 1)

        #RGBA8 2D texture, 24 bit depth texture, sizexsize
        glGenTextures(1, id_buf)
        gl_data.color_tex = id_buf.to_list()[0]

        glBindTexture(GL_TEXTURE_2D, gl_data.color_tex)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)

        # NULL means reserve texture memory, but texels are undefined
        null_buffer = Buffer(GL_BYTE, [(size + 1) * (size + 1) * 4])
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, size, size, 0, GL_BGRA, GL_UNSIGNED_BYTE, null_buffer)

        glGenFramebuffers(1, id_buf)
        gl_data.fb = id_buf.to_list()[0]
        glBindFramebuffer(GL_FRAMEBUFFER, gl_data.fb)

        # Attach 2D texture to this FBO
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, gl_data.color_tex, 0)

        glGenRenderbuffers(1, id_buf)
        gl_data.depth_rb = id_buf.to_list()[0]
        glBindRenderbuffer(GL_RENDERBUFFER, gl_data.depth_rb)
        glRenderbufferStorage(GL_RENDERBUFFER, GL_DEPTH_COMPONENT24, size, size)

        # Attach depth buffer to FBO
        glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_RENDERBUFFER, gl_data.depth_rb)

        # Does the GPU support current FBO configuration?
        status = glCheckFramebufferStatus(GL_FRAMEBUFFER)

        glBindFramebuffer(GL_FRAMEBUFFER, 0)

        if status == GL_FRAMEBUFFER_COMPLETE:
            print("FBO: good :)")
        else:
            print("FBO: error", status)

    def _draw_a_quad(self):
        """
        draw an animated quad on the screen
        """
        import time
        import math

        global _time

        speed = 0.01

        one = 1.0
        zer = 0.0

        _time, _int = math.modf(_time + speed)
        factor = _time * 2.0

        if factor > 1.0:
            factor = 2.0 - factor;

        one = one - factor;
        zer = factor - zer;

        glClearColor(1.0, 1.0, 1.0, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(-1.0, 1.0, -1.0, 1.0, 1.0, 20.0)

        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        gluLookAt(0.0, 0.0, 10.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0)

        current_color = Buffer(GL_FLOAT, 4)
        glGetFloatv(GL_CURRENT_COLOR, current_color);

        glEnable(GL_COLOR_MATERIAL)

        glBegin(GL_QUADS)
        glColor3f(one, zer, zer)
        glVertex3f(-0.75, -0.75, 0.0)
        glColor3f(zer, one, zer)
        glVertex3f( 0.75, -0.75, 0.0)
        glColor3f(zer, zer, one)
        glVertex3f( 0.75,  0.75, 0.0)
        glColor3f(one, one, zer)
        glVertex3f(-0.75,  0.75, 0.0)
        glEnd()

        glColor4fv(current_color)
        glDisable(GL_COLOR_MATERIAL)

        glMatrixMode(GL_PROJECTION)
        glPopMatrix()

        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()

    def _fbo_run(self):
        """
        draw in the FBO
        """
        gl_data = self._gl_data

        # setup
        glBindFramebuffer(GL_FRAMEBUFFER, gl_data.fb)

        viewport = Buffer(GL_INT, 4)
        glGetIntegerv(GL_VIEWPORT, viewport)
        glViewport(0, 0, gl_data.size, gl_data.size)

        # actual drawing
        self._draw_a_quad()

        # unbinding
        glBindFramebuffer(GL_FRAMEBUFFER, 0)
        glViewport(viewport[0], viewport[1], viewport[2], viewport[3])

    def _fbo_visualize(self):
        """
        draw the FBO in a quad
        """
        gl_data = self._gl_data

        current_color = Buffer(GL_FLOAT, 4)
        glGetFloatv(GL_CURRENT_COLOR, current_color);

        viewport = Buffer(GL_INT, 4)
        glGetIntegerv(GL_VIEWPORT, viewport)
        glViewport(300, 200, 256, 256)
        glScissor(300, 200, 256, 256)

        glClearColor(0.0, 0.0, 0.0, 0.0)
        glClearDepth(1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()

        glMatrixMode(GL_TEXTURE)
        glPushMatrix()
        glLoadIdentity()

        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()

        glOrtho(-1, 1, -1, 1, -20, 20)
        gluLookAt(0.0, 0.0, 1.0,0.0,0.0, 0.0, 0.0,1.0,0.0)

        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, gl_data.color_tex)

        glColor3f(1.0, 1.0, 1.0)
        glBegin(GL_QUADS)
        glTexCoord3f(1.0, 1.0, 0.0)
        glVertex2f( 1.0, 1.0)
        glTexCoord3f(0.0, 1.0, 0.0)
        glVertex2f(-1.0, 1.0)
        glTexCoord3f(0.0, 0.0, 0.0)
        glVertex2f(-1.0,-1.0)
        glTexCoord3f(1.0, 0.0, 0.0)
        glVertex2f( 1.0,-1.0)
        glEnd()

        glColor4fv(current_color)

        glDisable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, 0)

        glMatrixMode(GL_PROJECTION)
        glPopMatrix()

        glMatrixMode(GL_TEXTURE)
        glPopMatrix()

        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()

        glViewport(viewport[0], viewport[1], viewport[2], viewport[3])

    def _debug_quad(self):
        viewport = Buffer(GL_INT, 4)
        glGetIntegerv(GL_VIEWPORT, viewport)
        glViewport(300, 200, 256, 256)

        # actual drawing
        self._draw_a_quad()

        glViewport(viewport[0], viewport[1], viewport[2], viewport[3])

    def _fbo_delete(self):
        """
        cleanup FBO data
        """
        gl_data = self._gl_data
        id_buf = Buffer(GL_INT, 1)

        id_buf.to_list()[0] = gl_data.color_tex
        glDeleteTextures(1, id_buf)

        id_buf.to_list()[0] = gl_data.depth_rb
        glDeleteRenderbuffers(1, id_buf)

        glBindFramebuffer(GL_FRAMEBUFFER, 0)

        id_buf.to_list()[0] = gl_data.fb
        glDeleteFramebuffers(1, id_buf)

    def _draw_callback_px(self, context):
        """core function"""
        self._fbo_visualize()
        self._debug_quad()


# ############################################################
# Roadmap
# ############################################################

"""
Testing FBO
===========
get FBO drawing working

* create FBO
* draw to FBO via python
* draw FBO on screen


Testing Oculus
==============
draw FBO to direct mode

* get as far as required for direct mode


Blender FBO Rendering
=====================
test bpy.ops.view3d.offset()

* make sure matrices are correctly taken into account


Final Oculus Implementation
===========================
(https://developer.oculus.com/documentation/pcsdk/latest/concepts/dg-render/)

* obtain eye position
* calculate modelview matrix
* obtain projection matrix
* bpy.ops.view3d.offset()
* submit frame to oculus
"""

# ############################################################
# Global Properties
# ############################################################

class VirtualRealityInfo(bpy.types.PropertyGroup):
    is_enabled = bpy.props.BoolProperty(
            name="Enabled",
            default=False,
            )

# ############################################################
# Un/Registration
# ############################################################

@persistent
def virtual_reality_load_pre(dummy):
    wm = bpy.context.window_manager
    wm.virtual_reality.is_enabled = False


@persistent
def virtual_reality_load_post(dummy):
    wm = bpy.context.window_manager
    wm.virtual_reality.is_enabled = False


# ############################################################
# Un/Registration
# ############################################################

def register():
    bpy.app.handlers.load_pre.append(virtual_reality_load_pre)
    bpy.app.handlers.load_pre.append(virtual_reality_load_post)

    bpy.utils.register_class(VirtualRealitySandboxOperator)
    bpy.utils.register_class(VirtualRealityInfo)
    bpy.types.WindowManager.virtual_reality = bpy.props.PointerProperty(
            name="virtual_reality",
            type=VirtualRealityInfo,
            options={'HIDDEN'},
            )


def unregister():
    bpy.app.handlers.load_pre.remove(virtual_reality_load_pre)
    bpy.app.handlers.load_pre.remove(virtual_reality_load_post)

    bpy.utils.unregister_class(VirtualRealitySandboxOperator)
    del bpy.types.WindowManager.virtual_reality
    bpy.utils.unregister_class(VirtualRealityInfo)
