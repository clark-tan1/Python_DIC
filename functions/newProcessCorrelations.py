# -*- coding: utf-8 -*-
"""
Created on 06/06/2016

@author: Charlie Bourigault
@contact: bourigault.charlie@gmail.com

Please report issues and request on the GitHub project from ChrisEberl (Python_DIC)
More details regarding the project on the GitHub Wiki : https://github.com/ChrisEberl/Python_DIC/wiki

Current File: This file manages the complete image processing operation
"""

import numpy as np, cv2, time, os
from functions import DIC_Global, filterFunctions, CpCorr, initData

def prepareCorrelations(fileNameList, gridX, gridY, corrsize, baseMode, floatStep, parentWidget, parentWindow, largeDisp, filterInfos, thread):

    startTime = time.time()
    # getting the images filename list
    #fileName = parentWindow.fileDataPath+'/filenamelist.dat'
    #fileNameList = getData.testReadFile(fileName)

    infosThread = thread.signal.threadSignal

    infosAnalysis = []
    isLargeDisp = 1
    # Name
    # Reference Mode
    # CorrSize
    # nbProcesses
    # total processing time
    # nbImages
    # nbMarkers
    # nbImages * nbMarkers
    # largeDisp YES/NO
    # User Profile

    for image in range(len(fileNameList)):
        fileNameList[image] = fileNameList[image].rstrip()
    fileNameList = np.array(fileNameList)

    activeImages = np.array(parentWidget.imageActiveList).astype(np.int)

    if fileNameList is None:
        return

    if largeDisp is None:
        largeDisp = np.zeros((len(fileNameList),2))
        isLargeDisp = 0


    numOfBasePoints = len(gridX)
    numOfImages = len(fileNameList)

    #parentWidget.calculationBar.changeValue(1, 'Starting Processes...')

    # Adding some informations to the DevMode widget
    parentWindow.devWindow.addInfo('Starting the correlation process with '+str(numOfBasePoints)+' markers on '+str(numOfImages)+' images.')
    if baseMode == 0:
        parentWindow.devWindow.addInfo('Reference Image : Previous')
    elif baseMode == 1:
        parentWindow.devWindow.addInfo('Reference Image : First')
    elif baseMode == 2:
        parentWindow.devWindow.addInfo('Reference Image : Shifted ('+str(floatStep)+')')


    # Setting up the processes
    PROCESSES = int(parentWindow.profileData['nbProcesses'][parentWindow.currentProfile])
    args = []
    nbMarkersPerProcess = numOfBasePoints/PROCESSES
    if nbMarkersPerProcess < 2:
        nbMarkersPerProcess = 2
        PROCESSES = int(numOfBasePoints/2)+1
    parentWindow.devWindow.addInfo('Number of processes used: '+str(PROCESSES))
    for i in range(0,PROCESSES):
        start = int(i*nbMarkersPerProcess)
        if i >= PROCESSES-1: #last process do all the last images
            end = numOfBasePoints
        else:
            end = int((i+1)*nbMarkersPerProcess)
        args.append((fileNameList, activeImages, parentWindow.filePath, gridX[start:end], gridY[start:end], baseMode, corrsize, floatStep, largeDisp, filterInfos))

    result = DIC_Global.createProcess(parentWindow, processCorrelation, args, PROCESSES, parentWidget.calculationBar, '(1/2) Processing images...')


    parentWindow.devWindow.addInfo('Calculation finished. Saving data files.')

    #neighbors calculation
    #parentWidget.calculationBar.changeValue(1, '(2/2) Calculating neighborhood...')
    parentWidget.calculationBar.percent = 0
    parentWidget.calculationBar.currentTitle = '(2/2) Calculating neighborhood...'
    activeMarkers = np.linspace(0, numOfBasePoints, num=numOfBasePoints, endpoint=False).astype(np.int)
    minNeighbors = 16
    initData.calculateNeighbors(activeMarkers, result[0][:,activeImages[0]], result[1][:,activeImages[0]], minNeighbors, parentWindow.fileDataPath, progressBar=parentWidget.calculationBar)

    #data saving
    parentWidget.calculationBar.percent = 0
    parentWidget.calculationBar.currentTitle = 'Saving validx.csv...'
    Save('validx', result[0], parentWindow.fileDataPath)
    parentWidget.calculationBar.percent = 10
    parentWidget.calculationBar.currentTitle = 'Saving validy.csv...'
    Save('validy', result[1], parentWindow.fileDataPath)
    parentWidget.calculationBar.percent = 20
    parentWidget.calculationBar.currentTitle = 'Saving stdx.csv...'
    Save('stdx', result[3], parentWindow.fileDataPath)
    parentWidget.calculationBar.percent = 30
    parentWidget.calculationBar.currentTitle = 'Saving stdy.csv...'
    Save('stdy', result[4], parentWindow.fileDataPath)
    parentWidget.calculationBar.percent = 40
    parentWidget.calculationBar.currentTitle = 'Saving corrcoef.csv...'
    Save('corrcoef', result[2], parentWindow.fileDataPath)
    parentWidget.calculationBar.percent = 50
    parentWidget.calculationBar.currentTitle = 'Saving dispx.csv...'
    Save('dispx', result[5], parentWindow.fileDataPath)
    parentWidget.calculationBar.percent = 60
    parentWidget.calculationBar.currentTitle = 'Saving dispy.csv...'
    Save('dispy', result[6], parentWindow.fileDataPath)
    parentWidget.calculationBar.percent = 70
    parentWidget.calculationBar.currentTitle = 'Saving filenamelist.csv...'
    Save('filenamelist', fileNameList, parentWindow.fileDataPath)
    parentWidget.calculationBar.percent = 80
    parentWidget.calculationBar.currentTitle = 'Saving infoMarkers.csv...'
    Save('infoMarkers', result[7].astype(int), parentWindow.fileDataPath)
    if len(filterInfos) > 0:
        filterFunctions.saveOpenFilter(parentWindow.fileDataPath, filterList=filterInfos)

    parentWindow.devWindow.addInfo('Calculation done. Data files saved.')
    totalTime = time.time() - startTime

    infosAnalysis.append(os.path.basename(parentWindow.fileDataPath))
    infosAnalysis.append(baseMode)
    infosAnalysis.append(corrsize)
    infosAnalysis.append(PROCESSES)
    infosAnalysis.append(totalTime)
    infosAnalysis.append(numOfImages)
    infosAnalysis.append(numOfBasePoints)
    infosAnalysis.append(numOfImages*numOfBasePoints)
    infosAnalysis.append(isLargeDisp)
    infosAnalysis.append(str(parentWindow.profileData['User'][parentWindow.currentProfile]))

    parentWidget.calculationBar.percent = 90
    parentWidget.calculationBar.currentTitle = 'Saving infoAnalysis.csv...'
    Save('infoAnalysis', np.array(infosAnalysis), parentWindow.fileDataPath)
    if isLargeDisp:
        parentWidget.calculationBar.percent = 95
        parentWidget.calculationBar.currentTitle = 'Saving largeDisp.csv...'
        Save('largeDisp', largeDisp, parentWindow.fileDataPath)

    parentWindow.devWindow.addInfo('Processing Time : '+str(totalTime))
    infosThread.emit([1])
    return


def processCorrelation(fileNameList, activeImages, filePath, gridX, gridY, baseMode, corrsize, floatStep, largeDisp, filterInfos, q, pipe):


    # Initialise variables:
    [basePointsX, basePointsY, inputPointsX, inputPointsY] = InitFunc(gridX, gridY)
    numOfBasePoints = len(basePointsX)
    numOfImages = len(fileNameList)

    # Creating the main matrices to register the data
    ValidX = np.zeros((numOfBasePoints, numOfImages))
    ValidY = np.zeros((numOfBasePoints, numOfImages))
    CorrCoef = np.zeros((numOfBasePoints,numOfImages))
    StdX = np.zeros((numOfBasePoints, numOfImages))
    StdY = np.zeros((numOfBasePoints, numOfImages))
    DispX = np.zeros((numOfBasePoints,numOfImages))
    DispY = np.zeros((numOfBasePoints,numOfImages))
    infoMarkers = np.zeros((numOfBasePoints,numOfImages))


    result = np.zeros((8, numOfBasePoints, numOfImages))

    refImg = 0
    # Loading the reference image and applying filter if exist
    while(activeImages[refImg] == 0):
        ValidX[:,refImg] = np.nan
        ValidY[:,refImg] = np.nan
        DispX[:, refImg] = np.nan
        DispY[:, refImg] = np.nan
        CorrCoef[:,refImg] = np.nan
        StdX[:,refImg] = np.nan
        StdY[:,refImg] = np.nan
        refImg += 1
    base = cv2.imread(filePath+'/'+fileNameList[refImg], 0) # Reference image
    #base = cv2.cvtColor(baseRaw, cv2.COLOR_BGR2GRAY)


    #apply filter if loaded
    base = filterFunctions.applyFilterListToImage(filterInfos, base)


    ValidX[:,refImg]=basePointsX[:,0]
    ValidY[:,refImg]=basePointsY[:,0]


    previousTime = time.time()
    # Process all images: calculate correlation between reference and current image
    for CurrentImage in range(refImg+1, numOfImages):


        currentProgress = CurrentImage * 100 / numOfImages
        currentTime = time.time()
        if currentTime > previousTime + .05:
            previousTime = currentTime
            pipe.send(currentProgress)

        if activeImages[CurrentImage] == 1:

            inputImg = cv2.imread(filePath+'/'+fileNameList[CurrentImage], 0)
            inputImg = filterFunctions.applyFilterListToImage(filterInfos, inputImg)
            #inputImg = cv2.cvtColor(inputRaw, cv2.COLOR_BGR2GRAY)

            if baseMode == 2:
                #Reference image is shifted from float
                if sum(activeImages[0:CurrentImage]) > floatStep:
                    imageSelection = 0
                    while(activeImages[CurrentImage-floatStep-imageSelection] == 0):
                        imageSelection += 1
                    base = cv2.imread(filePath+'/'+fileNameList[CurrentImage-floatStep-imageSelection], 0)
                    base = filterFunctions.applyFilterListToImage(filterInfos, base)
                    newX = ValidX[:,CurrentImage-floatStep-imageSelection]
                    newY = ValidY[:,CurrentImage-floatStep-imageSelection]
                    basePointsX = np.reshape(newX, (len(newX),1))
                    basePointsY = np.reshape(newY, (len(newY),1))



            #adding large displacement
            largeDisplacementX = largeDisp[CurrentImage, 0] - largeDisp[CurrentImage-1, 0]
            largeDisplacementY = largeDisp[CurrentImage, 1] - largeDisp[CurrentImage-1, 1]


            inputPointsX = inputPointsX + largeDisplacementX
            inputPointsY = inputPointsY + largeDisplacementY


            [inputCorrX, inputCorrY, currentStdX, currentStdY, currentCorrCoef, infosError] = CpcorrFunc(basePointsX, basePointsY, inputPointsX, inputPointsY, base, inputImg, corrsize)
            inputPointsX = inputCorrX
            inputPointsY = inputCorrY


            if baseMode == 0:
                # Reference is previous image
                base = inputImg
                basePointsX = inputCorrX
                basePointsY = inputCorrY
                #basePointsX = np.round(inputCorrX, decimals = 1)
                #basePointsY = np.round(inputCorrY, decimals = 1)


            [ValidXCollected,ValidYCollected,StdXCollected,StdYCollected,CorrCoefCollected] = CollectDataFunc(inputCorrX, inputCorrY, currentStdX, currentStdY, currentCorrCoef) # a column for each image
            #[self.XSize, self.YSize] = self.input.shape
            ValidX[:,CurrentImage] = ValidXCollected[:,0]
            ValidY[:,CurrentImage] = ValidYCollected[:,0]
            DispX[:, CurrentImage] = ValidX[:, CurrentImage] - ValidX[:, refImg] - largeDisp[CurrentImage, 0]
            DispY[:, CurrentImage] = ValidY[:, CurrentImage] - ValidY[:, refImg] - largeDisp[CurrentImage, 1]
            CorrCoef[:,CurrentImage] = CorrCoefCollected[:,0]
            StdX[:,CurrentImage] = StdXCollected[:,0]
            StdY[:,CurrentImage] = StdYCollected[:,0]
            infoMarkers[:,CurrentImage] = infosError[:,0]

        else: #image has been removed by the user, putting NaN values in data

            ValidX[:,CurrentImage] = np.nan
            ValidY[:,CurrentImage] = np.nan
            DispX[:, CurrentImage] = np.nan
            DispY[:, CurrentImage] = np.nan
            CorrCoef[:,CurrentImage] = np.nan
            StdX[:,CurrentImage] = np.nan
            StdY[:,CurrentImage] = np.nan



    #assembling all matrices into one 3D result matrice
    result[0] = ValidX
    result[1] = ValidY
    result[2] = CorrCoef
    result[3] = StdX
    result[4] = StdY
    result[5] = DispX
    result[6] = DispY
    result[7] = infoMarkers

    q.put(result)
    q.close()
    return



def InitFunc(GridX, GridY):
    # Initialize variables
    inputPointsX = np.reshape(GridX,(len(GridX),1))
    inputPointsY = np.reshape(GridY,(len(GridY),1))
    basePointsX = np.reshape(GridX,(len(GridX),1))
    basePointsY = np.reshape(GridY,(len(GridY),1))
    return basePointsX, basePointsY, inputPointsX, inputPointsY


def CpcorrFunc(BasePointsX, BasePointsY, InputPointsX, InputPointsY, Base, Input, corrsize):

    #Process all markers and images by cpcorr.m (provided by matlab image processing toolbox)
    InputPointsX=np.array(InputPointsX)
    InputPointsY=np.array(InputPointsY)
    BasePointsX=np.array(BasePointsX)
    BasePointsY=np.array(BasePointsY)
    InputPoints = np.hstack([InputPointsX,InputPointsY])
    BasePoints = np.hstack([BasePointsX,BasePointsY])
    [xymoving, stdX, stdY, corrCoef, errorInfos] = CpCorr.cpcorr(InputPoints,BasePoints,Input,Base, corrsize)
    inputCorrX = xymoving[:,0]
    inputCorrY = xymoving[:,1]
    inputCorrX = np.array(inputCorrX)
    inputCorrY = np.array(inputCorrY)
    stdX = np.array(stdX)
    stdY = np.array(stdY)
    inputCorrX = np.reshape(inputCorrX, (len(inputCorrX),1))
    inputCorrY = np.reshape(inputCorrY, (len(inputCorrY),1))
    stdX = np.reshape(stdX, (len(stdX),1))
    stdY = np.reshape(stdY, (len(stdY),1))
    return inputCorrX, inputCorrY, stdX, stdY, corrCoef, errorInfos

def CollectDataFunc(InputCorrX,InputCorrY,StdX,StdY,CorrCoef):
    validXCurrent = InputCorrX
    validYCurrent = InputCorrY
    corrCoefCurrent = CorrCoef
    stdXCurrent = StdX
    stdYCurrent = StdY
    return validXCurrent, validYCurrent, stdXCurrent, stdYCurrent, corrCoefCurrent

def Save(FileName, Data, filePath, extension='csv'):

    np.savetxt(filePath+'/'+FileName+'.'+extension, Data, fmt="%s", delimiter=',')

def shiftDetection(filePath, imageList, activeImages, area, filterList, thread):

    largeDisp = np.zeros((len(imageList),2))

    initImage = cv2.imread(filePath+'/'+imageList[0].rstrip(), 0) #read the full image
    initImage = filterFunctions.applyFilterListToImage(filterList, initImage)
    nbImages = len(imageList)
    currentPercent = 1

    activeFileList = []
    for image in range(1, nbImages):
        if activeImages[image] == 1:
            activeFileList.append(image)

    template = initImage[area[1]:area[3],area[0]:area[2]] #select the template data
    width = area[2]-area[0]
    height = area[3]-area[1]

    origin = (area[0], area[1])
    startTime = time.time()
    for i in activeFileList:

        newImage = cv2.imread(filePath+'/'+imageList[i].rstrip(),0)
        newImage = filterFunctions.applyFilterListToImage(filterList, newImage)

        matchArea = cv2.matchTemplate(newImage, template, cv2.TM_CCORR_NORMED)
        minVal, maxVal, minLoc, maxLoc = cv2.minMaxLoc(matchArea)
        template = newImage[maxLoc[1]:maxLoc[1]+height,maxLoc[0]:maxLoc[0]+width] #the template for the next image is update with the template found on the current picture

        largeDisp[i][0] = maxLoc[0]-origin[0] #save the displacement
        largeDisp[i][1] = maxLoc[1]-origin[1]

        percent = i*100/nbImages
        if percent > currentPercent:
            thread.signal.threadSignal.emit([percent, i, largeDisp[i][0], largeDisp[i][1]])
            currentPercent = percent

    totalTime = time.time() - startTime
    thread.signal.threadSignal.emit([100, nbImages, largeDisp, totalTime])
    #print totalTime
