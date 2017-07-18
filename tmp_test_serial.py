import sys
import glob
import serial
import wx
from threading import *
from tmp_gl_canvas import CubeCanvas
import re
from time import sleep

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
        
class ExamplePanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)

        # create some sizers
        vSizer = wx.BoxSizer(wx.VERTICAL)
        grid = wx.GridBagSizer(hgap=5, vgap=5)

        # A multiline TextCtrl - This is here to show how the events work in this program, don't pay too much attention to it
        self.logger = wx.TextCtrl(self, size=(480, 300), style=wx.TE_MULTILINE | wx.TE_READONLY)

        # The Port Select combobox Control
        self.availablePorts = SerialPorts()
        self.lblPorts = wx.StaticText(self, label="Port")
        grid.Add(self.lblPorts, pos=(0, 0))

        self.cbPorts = wx.ComboBox(self, choices=self.availablePorts, style=wx.CB_READONLY)
        self.cbPorts.SetSelection(len(self.availablePorts) - 1)
        self.Bind(wx.EVT_COMBOBOX, self.OnPortSelect, self.cbPorts)
        self.selectedPort = ''
        grid.Add(self.cbPorts, pos=(0, 1))

        # The BaudRate Select combobox Control
        self.availableBaudRates = ['2400', '9600', '14400', '19200', '57600', '115200', '128000', '256000']
        self.lblBaudRates = wx.StaticText(self, label="Baud Rate")
        grid.Add(self.lblBaudRates, pos=(1, 0))

        self.cbBaudRates = wx.ComboBox(self, choices=self.availableBaudRates, style=wx.CB_READONLY)
        self.cbBaudRates.SetSelection(5)
        self.Bind(wx.EVT_COMBOBOX, self.OnBaudSelect, self.cbBaudRates)
        self.selectedBaudRate = ''
        grid.Add(self.cbBaudRates, pos=(1, 1), flag=wx.EXPAND | wx.ALL)

        # A button
        self.btnConnect = wx.Button(self, label="Connect")
        self.Bind(wx.EVT_BUTTON, self.OnConnect, self.btnConnect)
        grid.Add(self.btnConnect, pos=(2, 0), flag=wx.ALIGN_LEFT | wx.ALL)

        # A button
        self.btnRefresh = wx.Button(self, label="Refresh")
        self.Bind(wx.EVT_BUTTON, self.OnRefresh, self.btnRefresh)
        grid.Add(self.btnRefresh, pos=(2, 1), flag=wx.ALIGN_RIGHT | wx.ALL)

        # The Canvas to Render orientation
        self.canvas = CubeCanvas(self)
        self.canvas.SetMinSize((480, 480))

        vSizer.Add(grid, 0, wx.ALL, 5)
        vSizer.Add(self.logger, 0, wx.ALL, 5)
        vSizer.Add(self.canvas, 0, wx.ALL, 5)
        self.SetSizerAndFit(vSizer)

        # Set up event handler for any worker thread results
        self.Connect(-1, -1, EVT_RESULT_ID, self.OnReceiveData)
        self.Connect(-1, -1, EVT_DISCONNECT_ID, self.OnDisconnect)
        self.serialThread = None
        self.connected = False
        self.commands = []

    def OnPortSelect(self, event):
        """ Handler for selecting Port """
        self.selectedPort = event.GetString()
        self.logger.AppendText('Selected Port: %s\n' % event.GetString())

    def OnBaudSelect(self, event):
        """ Handler for selecting Baud Rate """
        self.selectedBaudRate = event.GetString()
        self.logger.AppendText('Selected Baud Rate: %s\n' % event.GetString())

    def OnConnect(self, event):
        """ Handle click on Connect Button """
        if not self.connected:
            self.logger.AppendText('Connecting\n')
            if self.ConnectToSerial():
                self.connected = True
                self.btnConnect.SetLabelText('Disconnect')
        else:
            self.logger.AppendText('Disconnecting\n')
            self.OnDisconnect(event)

    def OnDisconnect(self, event):
        """ Handle the disconnect operations """
        if self.serialThread is not None:
            self.serialThread.abort()
        self.connected = False
        self.canvas.StopRender()
        self.btnConnect.SetLabelText('Connect')

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
            self.canvas.StartRender()
        except (OSError, serial.SerialException):
            self.logger.AppendText("Failed To Connect\n")
            return False
        return True

    def OnReceiveData(self, event):
        """ Event that is triggered from the Serial Working thread to indicate new data has arrived """
        self.ParseMessage(event.data)

    def ParseMessage(self, data):
        """ Parse the incoming serial port data for message structure """
        commandLength = len(self.commands)
        if commandLength == 0 or '\r\n' in self.commands[commandLength - 1]:
            self.commands.append(data)
            commandLength += 1
        else:
            self.commands[commandLength].join(data)

        while commandLength and '\r\n' in self.commands[0]:
            command = self.commands.pop()
            commandLength = len(self.commands)
            self.logger.AppendText(data.replace('\r', ''))
            parsedData = re.split('=|,', command.replace(' ', ''))
            if len(parsedData) == 6:
                pitch = -int(parsedData[1]) / 1000
                roll = -int(parsedData[3]) / 1000
                yaw = int(parsedData[5]) / 1000
                self.canvas.SetOrientation(pitch, roll, yaw)
            else:
                self.logger.AppendText("----------Bad Data----------\n")

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
                bytesToRead = self.serialPort.inWaiting()
                if bytesToRead:
                    readBytes = self.serialPort.read(bytesToRead)
                    wx.PostEvent(self.guiWindow, ResultEvent(readBytes))
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
        # this excludes your current terminal "/dev/tty"
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
frame = wx.Frame(None, size=(1000, 1000))
panel = ExamplePanel(frame)
frame.Show()
app.MainLoop()
