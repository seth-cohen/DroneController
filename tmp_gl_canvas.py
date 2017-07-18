import wx
import sys

from wx import glcanvas

# The Python OpenGL package can be found at
# http://PyOpenGL.sourceforge.net/
from OpenGL.GL import *
from OpenGL.GLUT import *

class MyCanvasBase(glcanvas.GLCanvas):
    def __init__(self, parent):
        glcanvas.GLCanvas.__init__(self, parent, -1)
        self.init = False
        self.context = glcanvas.GLContext(self)
        
        # initial mouse position
        self.Bind(wx.EVT_ERASE_BACKGROUND, self.OnEraseBackground)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_PAINT, self.OnPaint)

    def OnEraseBackground(self, event):
        pass # Do nothing, to avoid flashing on MSW.

    def OnSize(self, event):
        size = self.size = self.GetClientSize()
        if self.context:
            self.SetCurrent(self.context)
            glViewport(0, 0, size.width, size.height)
        event.Skip()

    def OnPaint(self, event):
        dc = wx.PaintDC(self)
        self.SetCurrent(self.context)
        if not self.init:
            self.InitGL()
            self.init = True
        self.OnDraw()

class CubeCanvas(MyCanvasBase):
    def __init__(self, parent):
        MyCanvasBase.__init__(self, parent)
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.OnDraw, self.timer)
    
        self.pitch = 0
        self.roll = 0
        self.yaw = 0

    def InitGL(self):
        # set viewing projection
        glMatrixMode(GL_PROJECTION)
        glFrustum(-1.5, 1.5, -1.5, 1.5, 1.0, 100.0) #glFrustum(-10, 10, -10, 10, 1.0, 100.0)

        # position viewe
        glMatrixMode(GL_MODELVIEW)
        glTranslatef(0.0, 0.0, -10.0)

        # position object
        glRotatef(self.pitch, 1.0, 0.0, 0.0)
        glRotatef(self.roll, 0.0, 0.0, 1.0)
        glRotatef(self.yaw, 0.0, 1.0, 0.0)

        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)

    def StartRender(self):
        """ Starts the timer to render every 100 ms """
        self.timer.Start(100)

    def StopRender(self):
        """ Stops the timer and thus the rendering process """
        self.timer.Stop()

    def OnDraw(self, event=None):
        """ Use openGL to draw into the back buffer, then swap buffers to display on screen """
        if not self.init:
            return

        # clear color and depth buffers
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        # draw six faces of a cube
        glBegin(GL_QUADS)

        # Top face - define clockwise
        glNormal3f(0.0, 1.0, 0.0)
        glVertex3f(-5.0, 0.5, 6.0)
        glVertex3f(-6.0, 0.5, 5.0)
        glVertex3f(5.0, 0.5, -6.0)
        glVertex3f(6.0, 0.5, -5.0)

        # Bottom face
        glNormal3f(0.0, -1.0, 0.0)
        glVertex3f(-5.0, -0.5, 6.0) 
        glVertex3f(-6.0, -0.5, 5.0)
        glVertex3f(5.0, -0.5, -6.0)
        glVertex3f(6.0, -0.5, -5.0)

        # Right face
        glNormal3f(0.707, 0.0, 0.707)
        glVertex3f(6.0, 0.5, -5.0)
        glVertex3f(6.0, -0.5, -5.0)
        glVertex3f(-5.0, -0.5, 6.0)
        glVertex3f(-5.0, 0.5, 6.0)

        # Left Face
        glNormal3f(-0.707, 0.0, -0.707)
        glVertex3f(-6.0, 0.5, 5.0)
        glVertex3f(-6.0, -0.5, 5.0)
        glVertex3f(5.0, 0.5, -6.0)
        glVertex3f(5.0, -0.5, -6.0)

        # Front Face
        glNormal3f(-0.707, 0.0, 0.707)
        glVertex3f(-6.0, 0.5, 5.0)
        glVertex3f(-5.0, 0.5, 6.0)
        glVertex3f(-5.0, -0.5, 6.0)
        glVertex3f(-6.0, -0.5, 5.0)

        # Back Face
        glNormal3f(0.707, 0.0, -0.707)
        glVertex3f(6.0, 0.5, -5.0)
        glVertex3f(5.0, 0.5, -6.0)
        glVertex3f(5.0, -0.5, -6.0)
        glVertex3f(6.0, -0.5, -5.0)

        # ------ 2nd Cube ------ #
        # Top face - define clockwise
        glNormal3f(0.0, 1.0, 0.0)
        glVertex3f(6.0, 0.5, 5.0)
        glVertex3f(5.0, 0.5, 6.0)
        glVertex3f(-6.0, 0.5, -5.0)
        glVertex3f(-5.0, 0.5, -6.0)

        # Bottom face
        glNormal3f(0.0, -1.0, 0.0)
        glVertex3f(5.0, -0.5, 6.0) 
        glVertex3f(6.0, -0.5, 5.0)
        glVertex3f(-5.0, -0.5, -6.0)
        glVertex3f(-6.0, -0.5, -5.0)

        # Right face
        glNormal3f(0.707, 0.0, -0.707)
        glVertex3f(-5.0, 0.5, -6.0)
        glVertex3f(-5.0, -0.5, -6.0)
        glVertex3f(6.0, -0.5, 5.0)
        glVertex3f(6.0, 0.5, 5.0)

        # Left Face
        glNormal3f(-0.707, 0.0, 0.707)
        glVertex3f(5.0, 0.5, 6.0)
        glVertex3f(5.0, -0.5, 6.0)
        glVertex3f(-6.0, -0.5, -5.0)
        glVertex3f(-6.0, 0.5, -5.0)

        # Front Face
        glNormal3f(0.707, 0.0, 0.707)
        glVertex3f(5.0, 0.5, 6.0)
        glVertex3f(6.0, 0.5, 5.0)
        glVertex3f(6.0, -0.5, 5.0)
        glVertex3f(5.0, -0.5, 6.0)

        # Back Face
        glNormal3f(-0.707, 0.0, -0.707)
        glVertex3f(-5.0, 0.5, -6.0)
        glVertex3f(-6.0, 0.5, -5.0)
        glVertex3f(-6.0, -0.5, -5.0)
        glVertex3f(-5.0, -0.5, -6.0)

        glEnd()

        if self.size is None:
            self.size = self.GetClientSize()
        w, h = self.size
        w = max(w, 1.0)
        h = max(h, 1.0)
        xScale = 180.0 / w
        yScale = 180.0 / h

        # position viewer
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        glTranslatef(0.0, 0.0, -10.0)

        # position object
        glRotatef(self.pitch, 1.0, 0.0, 0.0)
        glRotatef(self.roll, 0.0, 0.0, 1.0)
        glRotatef(self.yaw, 0.0, 1.0, 0.0)

        self.SwapBuffers()

    def SetOrientation(self, pitch, roll, yaw):
        self.pitch = pitch
        self.roll = roll
        self.yaw = yaw
