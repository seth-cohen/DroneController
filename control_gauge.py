#!/usr/bin/python
import wx

class HorizontalControlGauge(wx.Panel):
    """ Gauge-like control to show the relative value of an input """
    def __init__(self, parent, extents=(0, 100), value=0):
        """ Constructor """
        wx.Panel.__init__(self, parent, style=wx.SUNKEN_BORDER)

        self.SetMinSize((200, 30))
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_SIZE, self.OnSize)

        if extents[0] > extents[1]:
            extents[0] = extents[1]

        self.extents = extents
        self.value = value

        self.Show(True)

    def OnPaint(self, event):
        """ Handle the EVT_PAINT event """
        dc = wx.PaintDC(self)
        w, h = self.GetSize()

        level = (w / float((self.extents[1] - self.extents[0]))) * (self.value - self.extents[0])

        dc.SetPen(wx.Pen('#0000CD'))
        dc.SetBrush(wx.Brush('#0000CD'))
        dc.DrawRectangle(0, 0, level, h)

    def OnSize(self, event):
        """ Refresh panel on size event """
        self.Refresh()

    def SetValue(self, value):
        """ Sets the value - clips it to be within the range of self.extents """
        value = min(value, self.extents[1])
        self.value = max(value, self.extents[0])
        self.Refresh()
    
class HorizontalLabeledGauge(wx.Panel):
    """ Custom Control Gauge with label """
    def __init__(self, parent, label, size=(200, 30), extents=(0, 100), value=0):
        """ You've guessed it - Constructor """
        wx.Panel.__init__(self, parent, size=size)
        hSizer = wx.BoxSizer(wx.HORIZONTAL)

        # Put the label to the left
        lblText = wx.StaticText(self, label=label)
        hSizer.Add(lblText, 0, wx.ALL|wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL, 5)

        self.gaugePanel = HorizontalControlGauge(self, extents=extents, value=value)
        hSizer.Add(self.gaugePanel, 1, wx.ALL|wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL, 5)

        self.SetSizerAndFit(hSizer)

    def SetValue(self, value):
        """ Proxy through to the gaugePanel's SetValue method """
        self.gaugePanel.SetValue(value)
