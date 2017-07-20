# -*- coding: utf-8 -*-
"""
/***************************************************************************
Name                 : Auxiliary Window
Description          : Plugin for open synchronized window with selected layers
Date                 : June, 2015
copyright            : (C) 2015 by Luiz Motta
email                : motta.luiz@gmail.com

 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

from PyQt4.QtGui import ( QMainWindow, QWidget, QGridLayout, QSizePolicy, QDockWidget,
                          QIcon, QColor, QAbstractItemView,
                          QToolBar, QToolButton, QCheckBox, QLabel, QDoubleSpinBox, QAction )
from PyQt4.QtCore import ( Qt, QRect, QTimer, pyqtSlot, pyqtSignal )

import qgis
from qgis.gui import  ( QgsRubberBand, QgsLayerTreeMapCanvasBridge, QgsLayerTreeView,
                        QgsMapCanvas, QgsMapToolPan,
                        QgsVertexMarker, QgsMessageBar )
from qgis.core import ( QGis, QgsMapLayerRegistry, QgsProject, QgsLayerTreeModel, QgsLayerTreeGroup,
                        QgsVectorLayer, QgsGeometry, QgsRectangle, QgsPoint )

import locale
import os
import json


class AuxiliaryLegend( QDockWidget ):

  currentLayerChanged = pyqtSignal( "QgsMapLayer" )
  currentLayerQgis = pyqtSignal( "QgsMapLayer" )
  syncGroupLayer = pyqtSignal()
  addSelectedLayersQgis = pyqtSignal()
  removeLayer = pyqtSignal( "QgsMapLayer" )
  needSelectLayer = pyqtSignal()
  closed = pyqtSignal()

  def __init__( self, parent, numWin ):
    def setTreeView():
      def setModel():
        self.model = QgsLayerTreeModel( ltg )
        self.model.setFlag( QgsLayerTreeModel.AllowNodeReorder )
        self.model.setFlag( QgsLayerTreeModel.AllowNodeChangeVisibility, True )
        self.tview.setModel( self.model )

      self.tview = QgsLayerTreeView( self )
      self.tview.setSelectionMode( QAbstractItemView.ExtendedSelection )
      setModel()
      self.tview.currentLayerChanged.connect( self.currentLayerChanged.emit )

    def setupUi():
      self.setAllowedAreas( Qt.LeftDockWidgetArea )
      winLegend.setWindowFlags( Qt.Widget )
      toolBar.setFloatable( False )
      toolBar.setMovable( False )
      winLegend.addToolBar( toolBar )
      self.setWidget( winLegend )

    def addActions():
      actn = QAction( winLegend )
      actn.setIcon( qgis.utils.iface.actionShowSelectedLayers().icon() )
      actn.setIconText( 'Show selected layers')
      actn.setObjectName( 'showLayer')
      actn.triggered.connect( self.onAction )
      toolBar.addAction( actn )

      actn = QAction( winLegend )
      actn.setIcon( qgis.utils.iface.actionHideSelectedLayers().icon() )
      actn.setIconText( 'Hide selected layers')
      actn.setObjectName( 'hideLayer')
      actn.triggered.connect( self.onAction )
      toolBar.addAction( actn )

      actn = QAction( winLegend )
      actn.setIcon( qgis.utils.iface.actionRemoveLayer().icon() )
      actn.setIconText( 'Remove selected layers')
      actn.setObjectName( 'removeLayer')
      actn.triggered.connect( self.onAction )
      toolBar.addAction( actn )

      toolBar.addSeparator()

      actn = QAction( winLegend )
      actn.setIcon( qgis.utils.iface.actionDuplicateLayer().icon() )
      actn.setIconText( 'Add selected layers from main map')
      actn.setObjectName( 'addLayer')
      actn.triggered.connect( self.onAction )
      toolBar.addAction( actn )

      actn = QAction( winLegend )
      actn.setIcon( QIcon( os.path.join( os.path.dirname(__file__), 'mActionCurrentLayer.png' ) ) )
      actn.setIconText( 'Current layer for main map')
      actn.setObjectName( 'currentLayer')
      actn.triggered.connect( self.onAction )
      toolBar.addAction( actn )

      actn = QAction( winLegend )
      actn.setIcon( QIcon( os.path.join( os.path.dirname(__file__), 'mActionAddGroup.png' ) ) )
      actn.setObjectName( 'syncGroup' )
      actn.triggered.connect( self.onAction )
      toolBar.addAction( actn )


    super( AuxiliaryLegend, self ).__init__( "#%d - Layers" % numWin, parent )

    ltg = parent.ltg    
    self.tview = self.model = self.bridge = None
    self.textSync = "Sync with group(main map) for new layers"
    self.actSync = None
    setTreeView()

    winLegend = QMainWindow( self )
    toolBar = QToolBar( winLegend )
    setupUi()
    addActions()
    self.addNameSyncGroup( "None" )
    winLegend.setCentralWidget( self.tview )

  def addNameSyncGroup(self, name):
    act = self.findChild( QAction, 'syncGroup' )
    text = "%s -> %s" % ( self.textSync, name )
    act.setIconText( text )

  def setBridge(self, canvas):
    ltg = self.model.rootGroup() 
    self.bridge = QgsLayerTreeMapCanvasBridge( ltg, canvas ) # Need wait populate ltg

  def clearBridge(self):
    if not self.bridge is None:
      self.bridge.clear()

  def closeEvent(self, event):
    event.accept()
    self.closed.emit()

  @pyqtSlot()
  def onAction(self):
    nameSender = self.sender().objectName()

    if nameSender in ( 'showLayer', 'hideLayer', 'removeLayer'):
      nodes = self.tview.selectedLayerNodes()
      if len( nodes ) == 0:
        self.needSelectLayer.emit()
        return
      
      if nameSender in ( 'showLayer', 'hideLayer'):
        checked = Qt.Checked if nameSender == 'showLayer' else Qt.Unchecked
        map( lambda item: item.setVisible( checked ), nodes )
      else:
        ltg = self.model.rootGroup()
        for node in nodes:
          self.removeLayer.emit( node.layer() )
          ltg.removeChildNode( node )

    # addLayer, currentLayer
    else: 
      if nameSender == 'addLayer':
        self.addSelectedLayersQgis.emit()
      elif nameSender == 'currentLayer':
        self.currentLayerQgis.emit( self.tview.currentLayer() )
      else:
        self.syncGroupLayer.emit()


class MarkerWindow():
  def __init__(self, canvas):
    self.canvas = canvas
    self.markerBack = self.marker = None

  def add(self):
    def createMarker( colorRGB, penWidth, iconSize, iconType ):
      marker = QgsVertexMarker( self.canvas )
      marker.setColor( QColor( colorRGB['R'], colorRGB['G'] , colorRGB['B'] ) )
      marker.setPenWidth( penWidth )
      marker.setIconSize( iconSize )
      marker.setIconType( iconType )

      return marker

    if not self.markerBack is None:
      self.canvas.scene().removeItem( self.markerBack )
    if not self.marker is None:
      self.canvas.scene().removeItem( self.marker )

    iconType = QgsVertexMarker.ICON_CROSS
    colorRGB = { 'R': 255, 'G': 255, 'B': 255 }
    self.markerBack = createMarker( colorRGB, 4, 10, QgsVertexMarker.ICON_CROSS )
    colorRGB = { 'R': 255, 'G': 0, 'B': 0 }
    self.marker = createMarker( colorRGB, 2, 8, QgsVertexMarker.ICON_CROSS )
    
  def remove(self):
    if not self.markerBack is None:
      self.canvas.scene().removeItem( self.markerBack )
      self.markerBack = None
    if not self.marker is None:
      self.canvas.scene().removeItem( self.marker )
      self.marker = None

  @pyqtSlot('QgsPoint')
  def onXYCoordinates(self, point ):
    if not self.markerBack is None:
      self.markerBack.setCenter( point )
    if not self.marker is None:
      self.marker.setCenter( point )


class AuxiliaryWindow(QMainWindow):
  
  closed = pyqtSignal( int )
  
  def __init__(self, parent, geometryWin, numWin):
    
    def populateStatusBar():
      statusBar = self.statusBar()

      w = QCheckBox( "Render", self )
      w.setObjectName( 'renderCheck')
      w.setToolTip( "Toggle map rendering" )
      w.setChecked( True )
      statusBar.addPermanentWidget( w )

      w = QCheckBox( "Marker", self )
      w.setObjectName( 'markerCheck')
      w.setToolTip( "Toggle marker with cursor position from main map" )
      w.setChecked( False )
      statusBar.addPermanentWidget( w, 1 )

      w = QCheckBox( "Extent", self )
      w.setObjectName( 'extentCheck')
      w.setToolTip( "Show extent of main map" )
      w.setChecked( False )
      statusBar.addPermanentWidget( w, 1 )

      w = QToolButton(self)
      w.setObjectName( 'highlightBtn')
      w.setToolTip( "Highlight extent in main map" )
      w.setText("Highlight")
      statusBar.addPermanentWidget( w, 1 )

      w = QLabel( "Scale factor:", self )
      w.setObjectName( 'scaleFactorLabel')
      w.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
      statusBar.addPermanentWidget( w, 1 )

      w = QDoubleSpinBox(self)
      w.setObjectName( 'scaleFactorSpin')
      w.setToolTip( "Current scale factor of main map" )
      w.setMinimum(0.0)
      w.setMaximum(1000.0)
      w.setDecimals(3)
      w.setValue(1)
      w.setSingleStep(.05)
      statusBar.addPermanentWidget( w, 1 )

      w = QToolButton(self)
      w.setObjectName( 'scaleBtn')
      w.setToolTip( "Set scale for main map" )
      w.setText("Scale: ")
      statusBar.addPermanentWidget( w, 1 )

    def setupUi():
      self.setObjectName( "AuxiliaryWindow" )
      self.setGeometry( geometryWin )
      self.addDockWidget ( Qt.LeftDockWidgetArea, self.dockLegend )
      self.actLegend = self.menuBar().addAction("")
      self.actLegend.triggered.connect( self.onActionLegend )
      self.canvas.setMapTool( self.toolPan )
      self.canvas.setCanvasColor( QColor(255,255,255) )
      
      #Capture the selection color of QGIS to apply to auxiliary windows
      prj = QgsProject.instance()
      myRed = prj.readNumEntry( "Gui", "/SelectionColorRedPart")
      myGreen = prj.readNumEntry( "Gui", "/SelectionColorGreenPart")
      myBlue = prj.readNumEntry( "Gui", "/SelectionColorBluePart")
      myAlpha = prj.readNumEntry( "Gui", "/SelectionColorAlphaPart")
      self.canvas.setSelectionColor( QColor(myRed[0], myGreen[0], myBlue[0], myAlpha[0] ))
      
      self.canvas.enableAntiAliasing( False )
      self.canvas.useImageToRender( False )
      self.canvas.setWheelAction( QgsMapCanvas.WheelZoom )
      self.setCentralWidget( centralWidget )
      self.messageBar.setSizePolicy( QSizePolicy.Minimum, QSizePolicy.Fixed )
      layout = QGridLayout()
      layout.setContentsMargins( 0, 0, 0, 0 )
      layout.addWidget( self.canvas, 0, 0, 2, 1 )
      layout.addWidget( self.messageBar, 0, 0, 1, 1 )
      centralWidget.setLayout( layout )

    super( AuxiliaryWindow, self ).__init__( parent )

    centralWidget = QWidget( self )
    self.canvas = QgsMapCanvas( centralWidget )
    self.messageBar = QgsMessageBar( centralWidget )
    self.toolPan = QgsMapToolPan( self.canvas )
    self.qgisCanvas = qgis.utils.iface.mapCanvas()
    self.qgisTView = qgis.utils.iface.layerTreeView()
    self.qgisSyncGroup = None
    self.numWin = numWin

    self.ltg = QgsLayerTreeGroup('', Qt.Unchecked)
    self.dockLegend = AuxiliaryLegend( self, numWin )
    self.root = QgsProject.instance().layerTreeRoot()
    

    self.extent = self.actLegend = None
    self.marker = MarkerWindow( self.canvas )

    setupUi()
    populateStatusBar()

    self.onCurrentLayerChanged( None )
    self.onDestinationCrsChanged_MapUnitsChanged()
    self.onHasCrsTransformEnabledChanged( self.qgisCanvas.hasCrsTransformEnabled() )
    
  def _connect(self, isConnect = True):
    widgets = {
     'scaleBtn': self.findChild( QToolButton, 'scaleBtn'),
     'renderCheck': self.findChild( QCheckBox, 'renderCheck'),
     'markerCheck': self.findChild( QCheckBox, 'markerCheck'),
     'extentCheck': self.findChild( QCheckBox, 'extentCheck'),
     'highlightBtn': self.findChild( QToolButton, 'highlightBtn'),
     'scaleFactorSpin': self.findChild( QDoubleSpinBox, 'scaleFactorSpin')
    }
    signal_slot = (
      { 'signal': widgets['scaleBtn'].clicked, 'slot': self.onClickedScale },
      { 'signal': widgets['renderCheck'].toggled, 'slot': self.onToggledRender },
      { 'signal': widgets['markerCheck'].toggled, 'slot': self.onToggledMarker },
      { 'signal': widgets['extentCheck'].toggled, 'slot': self.onToggledExtent },
      { 'signal': widgets['highlightBtn'].clicked, 'slot': self.onClickedHighlight },
      { 'signal': widgets['scaleFactorSpin'].valueChanged, 'slot': self.onValueChangedScale },
      { 'signal': self.dockLegend.currentLayerChanged, 'slot': self.onCurrentLayerChanged },
      { 'signal': self.dockLegend.currentLayerQgis, 'slot': self.onCurrentLayerQgis },
      { 'signal': self.dockLegend.syncGroupLayer, 'slot': self.onSyncGroupAddLayersQgis },
      { 'signal': self.dockLegend.addSelectedLayersQgis, 'slot': self.onAddSelectedLayersQgis },
      { 'signal': self.dockLegend.removeLayer, 'slot': self.onRemoveLayers },
      { 'signal': self.dockLegend.needSelectLayer, 'slot': self.onNeedSelectLayer },
      { 'signal': self.dockLegend.closed, 'slot': self.onClosedLegend },
      { 'signal': self.canvas.extentsChanged, 'slot': self.onExtentsChangedMirror },
      { 'signal': self.qgisCanvas.extentsChanged, 'slot': self.onExtentsChangedQgisCanvas },
      { 'signal': self.qgisCanvas.xyCoordinates, 'slot': self.marker.onXYCoordinates },
      { 'signal': self.qgisCanvas.destinationCrsChanged, 'slot': self.onDestinationCrsChanged_MapUnitsChanged },
      { 'signal': self.qgisCanvas.mapUnitsChanged, 'slot': self.onDestinationCrsChanged_MapUnitsChanged },
      { 'signal': self.qgisCanvas.hasCrsTransformEnabledChanged, 'slot': self.onHasCrsTransformEnabledChanged },
      { 'signal': self.root.removedChildren, 'slot': self.onRemovedChildrenQgisRoot },
      { 'signal': QgsMapLayerRegistry.instance().layersWillBeRemoved, 'slot': self.onLayersWillBeRemoved }
    )
    if isConnect:
      for item in signal_slot:
        item['signal'].connect( item['slot'] )
    else:
      for item in signal_slot:
        item['signal'].disconnect( item['slot'] )

  def _extentsChanged(self, canvasOrigin, originSlot, canvasDest, scaleFactor=None):
    canvasOrigin.extentsChanged.disconnect( originSlot )

    if scaleFactor is None:
      scale = canvasOrigin.scale()
      canvasOrigin.setExtent( canvasDest.extent() )
      canvasOrigin.zoomScale( scale )
    else:
      canvasOrigin.setExtent( canvasDest.extent() )
      canvasOrigin.zoomScale( scaleFactor * canvasDest.scale() )

    canvasOrigin.extentsChanged.connect( originSlot )

  def _textScaleBtnChanched(self):
    scale = locale.format( "%.0f", self.canvas.scale(), True ) 
    w = self.findChild( QToolButton, 'scaleBtn' )
    w.setText("Scale 1:%s" % scale )

  def _extent(self):
   rect = self.qgisCanvas.extent()
   p1 = QgsPoint( rect.xMinimum() , rect.yMinimum() )
   p2 = QgsPoint( rect.xMinimum() , rect.yMaximum() )
   p3 = QgsPoint( rect.xMaximum() , rect.yMaximum() )
   p4 = QgsPoint( rect.xMaximum() , rect.yMinimum() )
   p5 = QgsPoint( rect.xMinimum() , rect.yMinimum() )
   points = [ p1, p2, p3, p4, p5 ]
   self.extent.setToGeometry(QgsGeometry.fromPolyline (points), None)

  def _execFunction( self, func, arg, signal, slot):
   signal.disconnect( slot )
   func( arg )
   signal.connect( slot )

  def _connectVectorRefresh(self, layer, isConnect=True):
    if isinstance( layer, QgsVectorLayer ):
      f = layer.editCommandEnded.connect if isConnect else layer.editCommandEnded.disconnect
      f( self.canvas.refresh )

  def _addLayersQgis( self, layersQgis, needMsg=True ):
    
    self.dockLegend.clearBridge()

    l1 = set( layersQgis )
    l2 = set( map( lambda item: item.layer(), self.ltg.findLayers() ) )
    layers = list( l1 - l2 )
    if len( layers ) == 0:
      if needMsg:
        self.messageBar.pushMessage("Need select new layer(s) in main map", QgsMessageBar.WARNING, 2 )
    else:
      # Get order by layersQgis
      for item in layersQgis:
        if item in layers:
          self.ltg.addLayer( item )
          self._connectVectorRefresh( item )

    self.dockLegend.setBridge( self.canvas )

  def _syncGroupAddLayersQgis( self, ltg ):
    layersQgis = map( lambda item: item.layer(), ltg.findLayers() )
    if len( layersQgis ) == 0:
      return False

    name = ltg.name()
    if self.qgisSyncGroup == ltg:
      msg = "Already synchronized group (main map) -> '%s'" % name
      self.messageBar.pushMessage( msg, QgsMessageBar.INFO, 4 )
      return True
    
    if not self.qgisSyncGroup is None:
      self.qgisSyncGroup.addedChildren.disconnect( self.addedChildrenLayer )
      
    self.qgisSyncGroup = ltg
    self.qgisSyncGroup.addedChildren.connect( self.addedChildrenLayer )
    
    self.dockLegend.addNameSyncGroup( name )
    msg = "Changed synchronized group (main map) -> '%s'" % name
    self.messageBar.pushMessage( msg, QgsMessageBar.INFO, 4 )
    
    self._addLayersQgis( layersQgis )
    return True

  def run(self):
    
    if len( self.qgisTView.selectedLayerNodes() ) > 0:
      self.onAddSelectedLayersQgis()
    else:
      ltn = self.qgisTView.currentNode()
      if not isinstance( ltn, QgsLayerTreeGroup ):
        return False
      else:
        if ltn == self.root:
          return False
        else:
          if not self._syncGroupAddLayersQgis( ltn ):
            return False

    self.dockLegend.setBridge( self.canvas)

    self.canvas.setRenderFlag( False )
    self.show() # Need show before self._connect()
    self._connect()
    self.canvas.setExtent( self.qgisCanvas.extent() )
    w = self.findChild( QDoubleSpinBox, 'scaleFactorSpin')
    w.setValue( 1 )
    self.canvas.setRenderFlag( True )

    return True

  def getLayersCanvas(self):
    layerIds = map(lambda x: x.layerId(), self.ltg.findLayers() )
    layerChecks = map(lambda x: str( x.isVisible() ), self.ltg.findLayers() )

    return ( layerIds, layerChecks )

  def setLayersCanvas(self, layerIds, layerChecks ):
    prevFlag = self.canvas.renderFlag()
    self.canvas.setRenderFlag( False )

    lyrRegs = QgsMapLayerRegistry.instance()
    for id in range( len( layerIds ) ):
      layer = lyrRegs.mapLayer(  layerIds[id] )
      isVisible = int( layerChecks[id] )
      if not layer is None:
        self.ltg.addLayer( layer ).setVisible( isVisible )

    self.canvas.setRenderFlag( prevFlag )

  def getWindowSetting(self):
    g = self.geometry()
    r = self.canvas.extent()
    nodes = self.ltg.findLayers()
    currentLayer = self.dockLegend.tview.currentLayer()
    currentLayerId = currentLayer.id() if not currentLayer is None else "None"
    
    windowSetting =  {
      'numWin': self.numWin,
      'geometryWin': { 'x': g.x(), 'y': g.y(), 'width': g.width(), 'height': g.height() },
      'extentCanvas': { 'xmin': r.xMinimum(), 'ymin': r.yMinimum(), 'xmax': r.xMaximum(), 'ymax': r.yMaximum() },
      'currentLayerId': currentLayerId,
      'layerIds' : ' '.join( map(lambda item: item.layerId(), nodes ) ),
      'visibles': ' '.join( map(lambda item: str( int( item.isVisible() ) ), nodes ) )
    }
    for item in ( 'render', 'marker', 'extent' ):
      nameGui = "%sCheck" % item
      windowSetting[ item ] = int( self.findChild( QCheckBox, nameGui).isChecked() )

    return windowSetting

  def setWindowSetting(self, windowSetting):
    self.numWin = windowSetting['numWin']

    # Populate with layers and set Bridge for legend
    layerIds = windowSetting['layerIds'].split(' ')
    visibles = map( lambda item: bool( int( item ) ), windowSetting['visibles'].split(' ') )
    ltg = self.qgisTView.layerTreeModel().rootGroup()
    for id in range( len( layerIds ) ):
      node = ltg.findLayer( layerIds[ id ] )
      if node is None:
        continue
      layer = node.layer()
      visible = Qt.Checked if visibles[ id ] else Qt.Unchecked
      self._connectVectorRefresh( layer )
      self.ltg.addLayer( layer ).setVisible( visible )
    self.dockLegend.setBridge( self.canvas)
    
    self.show() # Need show before self._connect()
    self._connect()
    node = ltg.findLayer( windowSetting['currentLayerId'] )
    if not node is None:
      layer = node.layer()
      self.dockLegend.tview.setCurrentLayer( layer )
    w = windowSetting['extentCanvas']
    self.canvas.setExtent( QgsRectangle( w['xmin'], w['ymin'], w['xmax'], w['ymax'] ) )
    for item in ( 'render', 'marker', 'extent' ):
      value = bool( windowSetting[ item ] )
      nameGui = "%sCheck" % item
      self.findChild( QCheckBox, nameGui ).setChecked( value )

  def closeEvent(self, event):
    self._connect( False )
    event.accept()
    self.closed.emit( self.numWin )

  @pyqtSlot(int)
  def onValueChangedScale(self, scaleFactor):
    w = self.findChild( QCheckBox, 'renderCheck')
    if not w.isChecked():
      return
    self._execFunction(
      self.canvas.zoomScale, scaleFactor * self.qgisCanvas.scale(),
      self.canvas.extentsChanged, self.onExtentsChangedMirror
    )
    self._textScaleBtnChanched()

  @pyqtSlot()
  def onClickedScale(self):
    self._execFunction( 
        self.qgisCanvas.zoomScale, self.canvas.scale(),
        self.qgisCanvas.extentsChanged, self.onExtentsChangedQgisCanvas
    )
    w = self.findChild( QDoubleSpinBox, 'scaleFactorSpin' )
    self._execFunction( w.setValue, 1.0, w.valueChanged, self.onValueChangedScale )

  @pyqtSlot()
  def onClickedHighlight(self):
    def removeRB():
      rb.reset( True )
      self.qgisCanvas.scene().removeItem( rb )
    
    rb = QgsRubberBand( self.qgisCanvas, QGis.Polygon)
    rb.setBorderColor( QColor( 255,  0, 0 ) )
    rb.setWidth( 2 )
    rb.setToGeometry( QgsGeometry.fromRect( self.canvas.extent() ), None )
    QTimer.singleShot( 2000, removeRB )

  @pyqtSlot(bool)
  def onToggledRender(self, enabled):
    if enabled:
      self.canvas.setMapTool(self.toolPan)
      w = self.findChild( QDoubleSpinBox, 'scaleFactorSpin' )
      self._extentsChanged( self.canvas, self.onExtentsChangedMirror, self.qgisCanvas, w.value() )
      self._textScaleBtnChanched()
      self.canvas.setWheelAction( QgsMapCanvas.WheelZoom )
    else:
      self.canvas.unsetMapTool(self.toolPan)
      self.canvas.setWheelAction( QgsMapCanvas.WheelNothing )
    self.canvas.setRenderFlag( enabled )

  @pyqtSlot(bool)
  def onToggledMarker(self, enabled):
    self.marker.add() if enabled else self.marker.remove() 

  @pyqtSlot(bool)
  def onToggledExtent(self, enabled):
    def setExtent():
      if not self.extent is None:
        self.canvas.scene().removeItem( self.extent )
      self.extent = QgsRubberBand( self.canvas, QGis.Polygon )
      self.extent.setBorderColor( QColor( 255, 0 , 0 ) )
      self.extent.setWidth( 2 )
      self._extent()

    if enabled:
      setExtent()
    else:
      if not self.extent is None:
        self.canvas.scene().removeItem( self.extent )
        self.extent = None

  @pyqtSlot()
  def onExtentsChangedMirror(self):
    w = self.findChild( QCheckBox, 'renderCheck')
    if not w.isChecked():
      return
    self._extentsChanged( self.qgisCanvas, self.onExtentsChangedQgisCanvas, self.canvas )
    self._textScaleBtnChanched()
    w = self.findChild( QDoubleSpinBox, 'scaleFactorSpin' )
    self._execFunction(
        w.setValue, self.canvas.scale() / self.qgisCanvas.scale(),
        w.valueChanged, self.onValueChangedScale
    )
    if not self.extent is None:
      self._extent()

  @pyqtSlot()
  def onExtentsChangedQgisCanvas(self):
    w = self.findChild( QCheckBox, 'renderCheck')
    if not w.isChecked():
      return
    w = self.findChild( QDoubleSpinBox, 'scaleFactorSpin' )
    self._extentsChanged( self.canvas, self.onExtentsChangedMirror, self.qgisCanvas, w.value() )
    self._textScaleBtnChanched()
    if not self.extent is None:
      self._extent()

  @pyqtSlot()
  def onDestinationCrsChanged_MapUnitsChanged(self):
    prevFlag = self.canvas.renderFlag()
    self.canvas.setRenderFlag( False )

    self.canvas.setDestinationCrs( self.qgisCanvas.mapRenderer().destinationCrs()  )
    self.canvas.setMapUnits( self.qgisCanvas.mapUnits() )

    self.canvas.setRenderFlag( prevFlag )

  @pyqtSlot(bool)
  def onHasCrsTransformEnabledChanged(self, enabled):
    prevFlag = self.canvas.renderFlag()
    self.canvas.setRenderFlag( False )
    self.canvas.mapRenderer().setProjectionsEnabled( enabled )
    self.canvas.setRenderFlag( prevFlag )

  @pyqtSlot(list)
  def onLayersWillBeRemoved( self, theLayerIds ):
    ids = list( set( self.ltg.findLayerIds() ) & set( theLayerIds ) ) # intersection
    nodes = map( lambda item: self.ltg.findLayer( item ), ids )
    for item in nodes:
      self._connectVectorRefresh( item.layer(), False )
      self.ltg.removeChildNode( item )

  @pyqtSlot()
  def onAddSelectedLayersQgis( self ):
    layersQgis = map( lambda item: item.layer(), self.qgisTView.selectedLayerNodes() )
    self._addLayersQgis( layersQgis )

  @pyqtSlot('QgsLayerTreeNode', int, int)
  def addedChildrenLayer(self, ltg, indexFrom, indexTo):
    layersQgis = map( lambda item: item.layer(), ltg.findLayers() )
    self._addLayersQgis( layersQgis, False )

  @pyqtSlot('QgsLayerTreeNode', int, int)
  def onRemovedChildrenQgisRoot(self, ltg, indexFrom, indexTo):
    if not self.qgisSyncGroup is None and not self.qgisSyncGroup in self.root.children():
      self.qgisSyncGroup = None
      self.dockLegend.addNameSyncGroup( "None" )
      msg = "Removed synchronized group (main map)"
      self.messageBar.pushMessage( msg, QgsMessageBar.INFO, 4 )
      
      
  @pyqtSlot()
  def onSyncGroupAddLayersQgis( self):
    
    msg = "Need active a group in main map with new layers"
    ltn = self.qgisTView.currentNode()
    if not isinstance( ltn, QgsLayerTreeGroup ) or ltn == self.root:
      self.messageBar.pushMessage( msg, QgsMessageBar.WARNING, 3 )
      return

    if not self._syncGroupAddLayersQgis( ltn ):
      self.messageBar.pushMessage( msg, QgsMessageBar.WARNING, 3 )

  @pyqtSlot( 'QgsMapLayer' )
  def onRemoveLayers( self, layer ):
    self._connectVectorRefresh(layer, False)

  @pyqtSlot()
  def onNeedSelectLayer(self):
    self.messageBar.pushMessage("Need select layer(s)", QgsMessageBar.WARNING, 2 )    

  @pyqtSlot('QgsMapLayer')
  def onCurrentLayerQgis(self, layer ):
    if layer is None:
      self.messageBar.pushMessage("Need active layer", QgsMessageBar.WARNING, 2 )
    else:
      self.qgisTView.setCurrentLayer( layer )

  @pyqtSlot('QgsMapLayer')
  def onCurrentLayerChanged(self, layer ):
    hasLayer = True if not layer is None else False
    selectName = "Select layer '%s'" % layer.name() if hasLayer else "None select layer"
    title = "#%d - %s" % ( self.numWin, selectName )
    self.setWindowTitle( title )

  @pyqtSlot()
  def onClosedLegend(self):
    self.actLegend.setText( "Show layers" )

  @pyqtSlot()
  def onActionLegend(self):
    self.actLegend.setText( "" )
    self.dockLegend.show()


class ContainerAuxiliaryWindow():
  
  pluginName = "Plugin_Auxiliary_Window"
  pluginSetting = "/windowsSetting"
  
  def __init__(self, parent):
    self.parent = parent
    self.numWin = 0
    self.windows = {}

  def run(self):
    self.numWin += 1
    self.windows[ self.numWin ] = AuxiliaryWindow( self.parent, self.parent.geometry(), self.numWin )
    if not self.windows[ self.numWin ].run():
      del  self.windows[ self.numWin ]
      self.numWin -= 1
      msg = "Need selected layers in legend or group with layers."
      msgBar = qgis.utils.iface.messageBar()
      msgBar.pushMessage( self.pluginName, msg, QgsMessageBar.CRITICAL, 4 )
    else:
      self.windows[ self.numWin ].closed.connect( self.onClosed )

  def close(self):
    for item in self.windows.keys():
      self.windows[ item ].close()

  @pyqtSlot( int )
  def onClosed(self, numWin ):
    del self.windows[ numWin ]

  @pyqtSlot("QDomDocument")
  def onReadProject(self, document):
    proj = QgsProject.instance()
    value, ok = proj.readEntry( self.pluginName, self.pluginSetting )
    if ok and bool( value ):
      if len( self.windows ) > 0:
        self.close()
      numWin = 0
      for item in json.loads( value ):
        w = item['geometryWin']
        geometryWin = QRect ( w['x'], w['y'], w['width'], w['height'] ) 
        self.windows[ item['numWin' ] ] = AuxiliaryWindow( self.parent, geometryWin, item['numWin' ] )
        self.windows[ item['numWin' ] ].setWindowSetting( item )
        self.windows[ item['numWin' ] ].closed.connect( self.onClosed )
        numWin = item['numWin' ] if item['numWin' ]  > numWin else numWin  
      self.numWin = numWin

  @pyqtSlot("QDomDocument")
  def onWriteProject(self, document):
    windowsSetting = []
    for item in self.windows.values():
      windowsSetting.append( item.getWindowSetting() )

    proj = QgsProject.instance()
    if len( windowsSetting ) == 0:
      proj.removeEntry( self.pluginName, self.pluginSetting )
    else:
      proj.writeEntry( self.pluginName, self.pluginSetting, json.dumps( windowsSetting ) )
