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
from matplotlib.figure import Figure
from tkinter import filedialog
matplotlib.use('TkAgg')

#AltimeterViewer handles showing the data from the log files and running all data smothing and other algorithms
class AltimeterViewer:
    def __init__(self, master):
        #set up main screen with a master frame with the graphing canvas and side buttons/options
        master.columnconfigure(0,weight=4)
        master.columnconfigure(0,weight=1)
        master.rowconfigure(0,weight=1)
        self.masterGraphFrame = Frame(master)
        self.graphingFigure = Figure(figsize=(5,5), dpi=100)
        #create the different subplots, both position and velocity share the same graph, acceleration on another
        self.altitudeSubGraph = self.graphingFigure.add_subplot(121)
        self.velSubGraph = self.altitudeSubGraph.twinx()
        self.accelSubGraph = self.graphingFigure.add_subplot(122)
        #graph configuration stuffs
        self.graphCanvas = FigureCanvasTkAgg(self.graphingFigure, self.masterGraphFrame)
        self.graphCanvas.draw()
        self.graphCanvas.get_tk_widget().pack(side=BOTTOM, fill=BOTH, expand=True)
        self.graphToolbar = NavigationToolbar2Tk(self.graphCanvas, self.masterGraphFrame)
        self.graphToolbar.update()
        self.graphCanvas._tkcanvas.pack(side=TOP, fill=BOTH, expand=True)
        self.masterGraphFrame.grid(row=0, column=0,padx = 5,pady = 5,sticky=N+W+E+S)
        #create the options frame
        self.fileManagementFrame = Frame(master)
        #add buttons on the right
        self.fileOpenButton = Button(self.fileManagementFrame, text="Open Altitude Log", command = self.openLogFile)
        self.fileOpenButton.grid(row=0,column=0)
        self.fileManagementFrame.grid(row=0,column=1,padx = 5)
        #data initialization
        #raw data
        self.timeData = []
        self.altData = []
        #derived data
        self.kalmanAlt = []
        self.kalmanTime = []
        self.kalmanVel = []
        self.kalmanVelTime = []
        self.velData = []
        self.velTime = []
        self.accelData = []
        self.accelTime = []
        self.kalmanAccel = []
        self.kalmanAccelTime = []

    #opens the log file and parses raw altitude data from it
    def openAndParseFile(self, fileName):
        logFile = open(fileName)
        for line in logFile:
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

    #handles data smoothing/filters
    def filterData(self):
        #apply a kalman filter on the altitude data to smooth it
        self.altFilter = KalmanFilter(self.altData[0],1000,.001,.02,0)
        for i in range(1,len(self.altData)):
            self.kalmanAlt.append(self.altFilter.filter(self.altData[i]))
            self.kalmanTime.append(self.timeData[i])
            #print(self.p)
        #find velocity by taking the d/dt of the filtered altitude data
        for i in range(1,len(self.kalmanAlt)):
            runningDelta = 0
            #for p in range(1,1):
            runningDelta = self.kalmanAlt[i] - self.kalmanAlt[i-1]
            #runningDelta/=2
            runningDelta/=(self.timeData[i]-self.timeData[i-1])
            self.velData.append(runningDelta)
            self.velTime.append(self.kalmanTime[i])
        #apply a kalman filter on the velocity data to smooth the results
        self.velFilter = KalmanFilter(self.velData[0],1000,.01,.06,0)
        for i in range(1,len(self.velData)):
            self.kalmanVel.append(self.velFilter.filter(self.velData[i]))
            self.kalmanVelTime.append(self.velTime[i])
        #find acceleration by taking the da/dt from the filtered altitude data
        for i in range(1,len(self.kalmanVel)):
            runningDelta = 0
            #for p in range(1,1):
            runningDelta = self.kalmanVel[i] - self.kalmanVel[i-1]
            #runningDelta/=2
            runningDelta/=(self.kalmanVelTime[i]-self.kalmanVelTime[i-1])
            self.accelData.append(runningDelta)
            self.accelTime.append(self.kalmanVelTime[i])
        #apply a kalman filter on the raw acceleration data to smooth the data
        self.accelFilter = KalmanFilter(self.accelData[0],1000,.01,.06,0)
        for i in range(1,len(self.accelData)):
            self.kalmanAccel.append(self.accelFilter.filter(self.accelData[i]))
            self.kalmanAccelTime.append(self.accelTime[i])
            #print(self.p)

    def openLogFile(self):
        self.logFilename =  filedialog.askopenfilename(initialdir = "C:/",title = "Select file",filetypes = (("text files" ,"*.txt"),("all files","*.*")))
        self.openAndParseFile(self.logFilename)
        #self.orientationGraph.regraph()
        self.filterData()
        self.plotGraphs()

    def plotGraphs(self):
        self.altitudeSubGraph.plot(self.timeData,self.altData, label='Raw Alt')
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

#simple kalman filter for one data set
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
    gui = AltimeterViewer(root)
    root.mainloop()



if __name__ == "__main__":
    main()
