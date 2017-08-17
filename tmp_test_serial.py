import sys
import glob
import serial
import wx
import re
import time
from control_gauge import HorizontalLabeledGauge
from threading import *
from tmp_gl_canvas import CubeCanvas
from wx.lib.pubsub import pub

# Define notification event for thread completion
EVT_RESULT_ID = wx.NewId()
EVT_DISCONNECT_ID = wx.NewId()

class ResultEvent(wx.PyEvent):
    """Simple event to carry arbitrary result data."""
    def __init__(self, data):
        """Init Result Event."""
        wx.PyEvent.__init__(self)
        self.SetEventType(EVT_RESULT_ID)
        self.data = data

class DisconnectEvent(wx.PyEvent):
    """ Simple event to set state to disconnected """
    def __init__(self):
        wx.PyEvent.__init__(self)
        self.SetEventType(EVT_DISCONNECT_ID)
        
class AppFrame(wx.Frame):
    """ The main Frame that will house the UI elements for the application """
    def __init__(self, parent, size):
        """ Construct our Frame """
        wx.Frame.__init__(self, parent, size=size)

        # create some sizers
        hSizer = wx.BoxSizer(wx.HORIZONTAL)
        vSizer = wx.BoxSizer(wx.VERTICAL)

        # A multiline TextCtrl - This is here to show how the events work in this program, don't pay too much attention to it
        self.logger = wx.TextCtrl(self, size=(480, 300), style=wx.TE_MULTILINE | wx.TE_READONLY)

        # The Panel that will handle all the serial port connection details
        self.connectionPanel = ConnectionPanel(self)

        # The Canvas to Render orientation
        self.canvas = CubeCanvas(self)
        self.canvas.SetMinSize((480, 480))

        vSizer.Add(self.connectionPanel, 0, wx.ALL, 5)
        vSizer.Add(self.logger, 0, wx.ALL, 5)
        vSizer.Add(self.canvas, 0, wx.ALL, 5)
        hSizer.Add(vSizer, 0, wx.ALL, 5)

        # The PWM gauge control display
        self.controlsPanel = ControlsPanel(self)
        hSizer.Add(self.controlsPanel, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)

        # Subscribe to relevant messages
        pub.subscribe(self.OnLogMessage, 'logger.logMessage')
        pub.subscribe(self.ParseMessage, 'data.newPacket')
        pub.subscribe(self.OnSerialDisconnect, 'serial.disconnect')
        pub.subscribe(self.OnSerialConnect, 'serial.connect')

        self.canvas.StartRender()

        self.commands = []
 
        self.SetSizerAndFit(hSizer)

    def OnLogMessage(self, message):
        """ Simply logs the message """
        self.logger.AppendText(message)

    def OnSerialDisconnect(self):
        """ Actions to handle when disconnecting from serial port """
        self.canvas.StopRender()

    def OnSerialConnect(self):
        """ Actions to handle when connection to serial port is successful """
        self.canvas.StartRender()
        self.logger.AppendText('Connected to {}\n'.format(self.connectionPanel.cbPorts.StringSelection))

    def ParseMessage(self, packet):
        """ Parse the incoming serial port data for message structure """
        commandLength = len(self.commands)
        if commandLength == 0 or '\r\n' in self.commands[commandLength - 1]:
            self.commands.append(packet)
            commandLength += 1
        else:
            self.commands[commandLength].join(packet)

        while commandLength and '\r\n' in self.commands[0]:
            command = self.commands.pop()
            commandLength = len(self.commands)
            self.logger.AppendText(packet.replace('\r', ''))
            parsedData = re.split('=|,', command.replace(' ', ''))
            if len(parsedData) == 14:
                pitch = -int(parsedData[1]) / 1000
                roll = -int(parsedData[3]) / 1000
                yaw = int(parsedData[5]) / 1000
                self.canvas.SetOrientation(pitch, roll, yaw)

                self.controlsPanel.throttleGauge.SetValue(int(parsedData[7]))
                self.controlsPanel.pitchGauge.SetValue(int(parsedData[9]))
                self.controlsPanel.yawGauge.SetValue(int(parsedData[11]))
                self.controlsPanel.rollGauge.SetValue(int(parsedData[13]))
            else:
                self.logger.AppendText('----------Bad Data----------\n')

class ConnectionPanel(wx.Panel):
    """ The main panel for the application """
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)

        grid = wx.GridBagSizer(hgap=5, vgap=5)

        # The Port Select combobox Control
        self.availablePorts = SerialPorts()
        self.lblPorts = wx.StaticText(self, label='Port')
        grid.Add(self.lblPorts, pos=(0, 0))

        self.cbPorts = wx.ComboBox(self, choices=self.availablePorts, style=wx.CB_READONLY)
        self.cbPorts.SetSelection(len(self.availablePorts) - 1)
        self.Bind(wx.EVT_COMBOBOX, self.OnPortSelect, self.cbPorts)
        self.selectedPort = ''
        grid.Add(self.cbPorts, pos=(0, 1))

        # The BaudRate Select combobox Control
        self.availableBaudRates = ['2400', '9600', '14400', '19200', '57600', '115200', '128000', '256000']
        self.lblBaudRates = wx.StaticText(self, label='Baud Rate')
        grid.Add(self.lblBaudRates, pos=(1, 0))

        self.cbBaudRates = wx.ComboBox(self, choices=self.availableBaudRates, style=wx.CB_READONLY)
        self.cbBaudRates.SetSelection(5)
        self.Bind(wx.EVT_COMBOBOX, self.OnBaudSelect, self.cbBaudRates)
        self.selectedBaudRate = ''
        grid.Add(self.cbBaudRates, pos=(1, 1), flag=wx.EXPAND | wx.ALL)

        # A button
        self.btnConnect = wx.Button(self, label='Connect')
        self.Bind(wx.EVT_BUTTON, self.OnConnect, self.btnConnect)
        grid.Add(self.btnConnect, pos=(2, 0), flag=wx.ALIGN_LEFT | wx.ALL)

        # A button
        self.btnRefresh = wx.Button(self, label='Refresh')
        self.Bind(wx.EVT_BUTTON, self.OnRefresh, self.btnRefresh)
        grid.Add(self.btnRefresh, pos=(2, 1), flag=wx.ALIGN_RIGHT | wx.ALL)

        # Set up event handler for any worker thread results
        self.Connect(-1, -1, EVT_RESULT_ID, self.OnReceiveData)
        self.Connect(-1, -1, EVT_DISCONNECT_ID, self.OnDisconnect)
        self.serialThread = None
        self.connected = False

        self.SetSizerAndFit(grid)

    def OnPortSelect(self, event):
        """ Handler for selecting Port """
        self.selectedPort = event.GetString()
        pub.sendMessage('logger.logMessage', message='Selected Port: {}\n'.format(event.GetString()))

    def OnBaudSelect(self, event):
        """ Handler for selecting Baud Rate """
        self.selectedBaudRate = event.GetString()
        pub.sendMessage('logger.logMessage', message='Selected Baud Rate: {}\n'.format(event.GetString()))

    def OnConnect(self, event):
        """ Handle click on Connect Button """
        if not self.connected:
            pub.sendMessage('logger.logMessage', message='Connecting\n')
            if self.ConnectToSerial():
                self.connected = True
                self.btnConnect.SetLabelText('Disconnect')
        else:
            pub.sendMessage('logger.logMessage', message='Disconnecting\n')
            self.OnDisconnect(event)

    def OnDisconnect(self, event):
        """ Handle the disconnect operations """
        if self.serialThread is not None:
            self.serialThread.abort()
        self.connected = False
        self.btnConnect.SetLabelText('Connect')
        pub.sendMessage('serial.disconnect')

    def OnRefresh(self, event):
        """ Refresh the listing of serial ports """
        self.availablePorts = SerialPorts()
        self.cbPorts.Items = self.availablePorts

    def ConnectToSerial(self):
        """ Connect to the serial port and start up the worker thread """
        try:
            ser = serial.Serial(
                port=self.cbPorts.StringSelection,
                baudrate=self.cbBaudRates.StringSelection
            )
            self.serialThread = SerialThread(self, ser)
            self.serialThread.start()
            pub.sendMessage('serial.connect')
        except (OSError, serial.SerialException):
            pub.sendMessage('logger.logMessage', message='Failed To Connect\n')
            return False
        return True

    def OnReceiveData(self, event):
        """ Event that is triggered from the Serial Working thread to indicate new data has arrived """
        pub.sendMessage('data.newPacket', packet=event.data)

class ControlsPanel(wx.Panel):
    """ The main panel for the application """
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)

        vSizer = wx.BoxSizer(wx.VERTICAL)

        # Create a gauge control for each of the PWM signals to indicate strength
        self.throttleGauge = HorizontalLabeledGauge(self, 'Throttle', extents=(1000, 2000), value=1200)
        vSizer.Add(self.throttleGauge, 0, wx.ALL, 5)

        self.pitchGauge = HorizontalLabeledGauge(self, 'Pitch', extents=(1000, 2000), value=1200)
        vSizer.Add(self.pitchGauge, 0, wx.ALL, 5)

        self.yawGauge = HorizontalLabeledGauge(self, 'Yaw', extents=(1000, 2000), value=1200)
        vSizer.Add(self.yawGauge, 0, wx.ALL, 5)

        self.rollGauge = HorizontalLabeledGauge(self, 'Roll', extents=(1000, 2000), value=1200)
        vSizer.Add(self.rollGauge, 0, wx.ALL, 5)

        self.SetSizerAndFit(vSizer)

class SerialThread(Thread):
    """ Worker thread to continual read data from serial port as available"""
    def __init__(self, guiWindow, serialPort):
        """ Initialize the thread """
        Thread.__init__(self)
        self.guiWindow = guiWindow
        self.serialPort = serialPort
        self._shouldAbort = 0

    def run(self):
        """ The actual meat and potatoes of the thread """
        while not self._shouldAbort and self.serialPort:
            try:
                # actually this is not working... seems like too much data is coming across and
                # serial port is bogging down the computer... perhaps just need to switch to 
                # polling scheme with a sleep/timer
                self.serialPort.write("getPacket\r")
                bytesToRead = self.serialPort.inWaiting()
                # throw these away in order to save some cycles on CPU we are burning out of time 
                if bytesToRead:
                    readBytes = self.serialPort.read(bytesToRead)
                    wx.PostEvent(self.guiWindow, ResultEvent(readBytes))
                time.sleep(0.050)
                
            except:
                self._shouldAbort = 1                
        self.serialPort = None
        wx.PostEvent(self.guiWindow, DisconnectEvent())

    def abort(self):
        """ Kill the thread - called by the gui """
        self._shouldAbort = 1

def SerialPorts():
    """ Lists serial port names

        :raises EnvironmentError:
            On unsupported or unknown platforms
        :returns:
            A list of the serial ports available on the system
    """
    if sys.platform.startswith('win'):
        ports = ['COM%s' % (i + 1) for i in range(256)]
    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        # this excludes your current terminal '/dev/tty'
        ports = glob.glob('/dev/tty[A-Za-z]*')
    elif sys.platform.startswith('darwin'):
        ports = glob.glob('/dev/tty.*')
    else:
        raise EnvironmentError('Unsupported platform')

    result = []
    for port in ports:
        try:
            s = serial.Serial(port)
            s.close()
            result.append(port)
        except (OSError, serial.SerialException):
            pass
    return result

app = wx.App(False)
frame = AppFrame(None, size=(1000, 1000))
frame.Show()
app.MainLoop()
