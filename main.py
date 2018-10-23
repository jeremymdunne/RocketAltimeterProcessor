import serial
import sys
import _thread
from tkinter import *
import math
import matplotlib
import numpy as np
from Graph import Graph
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
# implement the default mpl key bindings
from matplotlib.backend_bases import key_press_handler
from matplotlib.figure import Figure
from tkinter import filedialog
matplotlib.use('TkAgg')


class MainGui:
    def __init__(self, master):
        print("init")
        master.columnconfigure(0,weight=4)
        master.columnconfigure(0,weight=1)
        master.rowconfigure(0,weight=1)
        self.timeData = []
        self.altData = []
        self.orientationGraphFrame = Frame(master)
        #self.orientationGraph = Graph(self.orientationGraphFrame,yTag="Altitude(meters)",numAxis=3, colors = ['red','blue','green'], autoScaleY = True)
        self.graphingFigure = Figure(figsize=(5,5), dpi=100)
        self.altitudeSubGraph = self.graphingFigure.add_subplot(121)
        self.velSubGraph = self.altitudeSubGraph.twinx()
        self.accelSubGraph = self.graphingFigure.add_subplot(122)
        #self.smoothedSubGraph = self.graphingFigure.add_subplot(111,axisbg='r')
        #a.plot([1,2,3,4,5,6,7,8],[5,6,1,3,8,9,3,5])
        self.graphCanvas = FigureCanvasTkAgg(self.graphingFigure, self.orientationGraphFrame)
        self.graphCanvas.draw()
        self.graphCanvas.get_tk_widget().pack(side=BOTTOM, fill=BOTH, expand=True)

        self.graphToolbar = NavigationToolbar2Tk(self.graphCanvas, self.orientationGraphFrame)
        self.graphToolbar.update()
        self.graphCanvas._tkcanvas.pack(side=TOP, fill=BOTH, expand=True)

        self.orientationGraphFrame.grid(row=0, column=0,padx = 5,pady = 5,sticky=N+W+E+S)
        self.fileManagementFrame = Frame(master)
        #add buttons
        self.fileOpenButton = Button(self.fileManagementFrame, text="Open Altitude Log", command = self.openLogFile)
        self.fileOpenButton.grid(row=0,column=0)
        self.fileManagementFrame.grid(row=0,column=1,padx = 5)

    def openLogFile(self):
        self.logFilename =  filedialog.askopenfilename(initialdir = "C:/",title = "Select file",filetypes = (("text files" ,"*.txt"),("all files","*.*")))
        self.logFile = open(self.logFilename)
        for line in self.logFile:
            #print(line)
            lastEnd = 0
            while lastEnd < len(line):
                try:
                    start = line.index("A",lastEnd)
                except:
                    print("EOF")
                    start = len(line) + 10
                #print(start)
                if start>=0 and start < len(line):
                    alt = float(self.parseMessageForSubstring(line,"A",";",lineStart=start))
                    timeStamp = float(self.parseMessageForSubstring(line, ";",";",lineStart=start))/1000
                    self.timeData.append(timeStamp)
                    self.altData.append(alt)
                    #self.orientationGraph.addPoint([timeStamp,alt],0,graphNow = False)
                    #print("Alt:" + str(alt) + " Time: " + str(timeStamp))
                    lastEnd = start + 1
                else:
                    lastEnd = len(line)
        #self.orientationGraph.regraph()
        #lets do some perliminary altitude smoothing!
        #first do an average of n points
        self.newAltData = []
        self.newTimeData = []
        for i in range(50,len(self.altData)):
            runningAvg = 0
            runningDelta = 0
            for p in range(0,50):
                runningAvg += self.altData[i-p]
            runningAvg /=50
            self.newAltData.append(runningAvg)
            self.newTimeData.append(self.timeData[i])

        self.kalmanAlt = []
        self.kalmanTime = []
        self.altFilter = KalmanFilter(self.altData[0],1000,.001,.02,0)
        for i in range(1,len(self.altData)):
            self.kalmanAlt.append(self.altFilter.filter(self.altData[i]))
            self.kalmanTime.append(self.timeData[i])
            #print(self.p)

        self.velData = []
        self.velTime = []
        #find velocity
        for i in range(1,len(self.kalmanAlt)):
            runningDelta = 0
            #for p in range(1,1):
            runningDelta = self.kalmanAlt[i] - self.kalmanAlt[i-1]
            #runningDelta/=2
            runningDelta/=(self.timeData[i]-self.timeData[i-1])
            self.velData.append(runningDelta)
            self.velTime.append(self.kalmanTime[i])

        self.kalmanVel = []
        self.kalmanVelTime = []
        self.velFilter = KalmanFilter(self.velData[0],1000,.01,.06,0)
        for i in range(1,len(self.velData)):
            self.kalmanVel.append(self.velFilter.filter(self.velData[i]))
            self.kalmanVelTime.append(self.velTime[i])
            #print(self.p)

        self.accelData = []
        self.accelTime = []
        #find velocity
        for i in range(1,len(self.kalmanVel)):
            runningDelta = 0
            #for p in range(1,1):
            runningDelta = self.kalmanVel[i] - self.kalmanVel[i-1]
            #runningDelta/=2
            runningDelta/=(self.kalmanVelTime[i]-self.kalmanVelTime[i-1])
            self.accelData.append(runningDelta)
            self.accelTime.append(self.kalmanVelTime[i])

        self.kalmanAccel = []
        self.kalmanAccelTime = []
        self.accelFilter = KalmanFilter(self.accelData[0],1000,.01,.06,0)
        for i in range(1,len(self.accelData)):
            self.kalmanAccel.append(self.accelFilter.filter(self.accelData[i]))
            self.kalmanAccelTime.append(self.accelTime[i])
            #print(self.p)


        #self.smoothedSubGraph.plot()
        self.altitudeSubGraph.plot(self.timeData,self.altData, label='Raw Alt')
        #self.altitudeSubGraph.plot(self.newTimeData,self.newAltData, label='Filtered Alt')
        self.altitudeSubGraph.plot(self.kalmanTime,self.kalmanAlt, label='Kalman Alt 1')
        self.velSubGraph.plot(self.velTime,self.velData, color='y', label='Velocity')
        self.velSubGraph.plot(self.kalmanVelTime, self.kalmanVel, color='black', label='Kalman Velocity')
        self.accelSubGraph.plot(self.accelTime, self.accelData, label='Raw Accel')
        self.accelSubGraph.plot(self.kalmanAccelTime, self.kalmanAccel, label='Kalman Accel')
        self.altitudeSubGraph.legend(loc='upper left')
        self.velSubGraph.legend(loc='upper right')
        self.accelSubGraph.legend(loc='upper left')
        self.graphCanvas.draw()
        self.graphToolbar.update()
        print(len(self.kalmanAccelTime))
        #print("Opening log!");

    def parseMessageForSubstring(slef, message, indicator, deliminator,lineStart=0):
        start = message.index(indicator,lineStart) + len(indicator)
        end = message.index(deliminator, start)
        return message[start:end]

    def handleOrientationMessage(self, message):

        xOrientation = float(parseMessageForSubstring(message, "X:", ";"))
        yOrientation = float(parseMessageForSubstring(message, "Y:", ";"))
        zOrientation = float(parseMessageForSubstring(message, "Z:", ";"))
        time = float(parseMessageForSubstring(message, "TS:", ";"))
        self.orientationGraph.addPoint([time,xOrientation],0, graphNow = False)
        self.orientationGraph.addPoint([time,yOrientation],1, graphNow = True)
        #self.orientationGraph.addPoint([time,zOrientation],2, graphNow = True)


    def handleCommunication(self):
        #self.handleOrientationMessage("@O:X:1.5;Y:-2.3;Z:5.5;TS:0.0;")
        #self.handleOrientationMessage("@O:X:2.5;Y:-2.5;Z:4.5;TS:1.0;")
        #self.handleOrientationMessage("@O:X:1.5;Y:-2.3;Z:5.5;TS:2.0;")
        #self.handleOrientationMessage("@O:X:1.5;Y:-2.3;Z:6.5;TS:3.0;")
        while(self.serialMonitor.checkForOpenComms() == False):
            pass
        #attempt open
        self.portOptions = self.serialMonitor.getRequestedComms()
        try:
            self.serial = ArduinoCommunicator(self.portOptions)
        except Exception as e:
            print(e)
            print("Failed to Open")
            self.serialMonitor.showMessageFromTarget("Failed To Open Port")
            #try again
            self.handleCommunication()
        print("Opened Serial!")
        # start the main communication loop
        while True:
            while(self.serial.isOpen() == True):

                if(self.serial.available()):
                    #read it
                    try:
                        message = self.serial.read()
                        #print("New Message:" + message)
                        #parse it here
                        if "@O" in message:
                            self.handleOrientationMessage(message)
                        elif "@P" in message:
                            self.handlePowerMessage(message)
                        self.serialMonitor.showMessageFromTarget(message)
                    except:
                        print("error")
                if(self.serialMonitor.checkForNewMessage() == True):
                    message = self.serialMonitor.getMessage()
                    #send to the target
                    self.serial.write(message)

class KalmanFilter:
    def __init__(self, x, p, q, r, k):
        self.p = p;
        self.q = q;
        self.r = r;
        self.k = k;
        self.x = x;
    def filter(self, newMeasurement):
        self.p = self.p + self.q;
        self.k = self.p / (self.p + self.r);
        self.x = self.x + self.k * (newMeasurement - self.x);
        self.p = (1 - self.k) * self.p;
        return self.x

def main():
    root = Tk()
    root.title("Rocket Altimeter Visualizer")
    gui = MainGui(root)
    root.mainloop()





if __name__ == "__main__":
    main()
