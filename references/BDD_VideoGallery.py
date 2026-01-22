import os
import sys
from glob import glob
from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *
import traceback


import sys

# Ensure that the custom cv2 module is loaded by clearing it from sys.modules first
if 'cv2' in sys.modules:
    del sys.modules['cv2']
# Ensure that the custom cv2 module is loaded by clearing it from sys.modules first

if sys.version_info[1] <= 7:
    if 'numpy' in sys.modules:
        del sys.modules['numpy']

currentFilePath = __file__.replace('\\', '/')
TsunamiPath = '/'.join(currentFilePath.split('/')[:-3])+'/Lib'
if TsunamiPath not in sys.path:
    sys.path.append(TsunamiPath)

# Now import your custom cv2 module
import cv2


class WorkerSignals(QObject):
    finished = Signal()
    resize_finished = Signal()
    update_progress = Signal(int)
    video_load_signal = Signal(object, object, object, list, bool)
    add_thumbnail_signal = Signal(object, object)
    selected_widgets = Signal(list)
    store_widget = Signal(object, int, int)
    remove_widget =Signal(object)
    do_thumbnail_signal = Signal(object)
    resize_thumbnail_signal = Signal(object, int, int)
    scene_ready = Signal()


class VideoPlayer(QGraphicsPixmapItem):
    def __init__(self, video_path, size=(1920, 1080), thumbnail_path=None, parent=None):
        super(VideoPlayer, self).__init__(parent)
        self.width = size[0]
        self.height = size[1]

        # OpenCV video capture
        self.cap = cv2.VideoCapture(video_path)
        if not self.cap.isOpened():
            print("Error: Could not open video.")
            sys.exit()

        # Timer for playback
        self.timer = QTimer()
        self.timer.timeout.connect(self.next_frame)

    def start_video(self):
        """Starts the video playback loop."""
        self.timer.start(int(1000 / self.cap.get(cv2.CAP_PROP_FPS)))  # Frame interval in ms

    def stop_video(self):
        """Stops the video playback loop."""
        self.timer.stop()

    def next_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            # If the video reaches the end, reset the capture to the first frame
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # Reset to first frame
            ret, frame = self.cap.read()

        if ret:
            # Convert frame to RGB (OpenCV uses BGR by default)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Crop frame to match aspect ratio of `self.width` and `self.height`
            h, w, ch = frame.shape
            aspect_ratio = w / h

            # Determine cropping dimensions
            target_aspect_ratio = self.width / self.height
            if aspect_ratio > target_aspect_ratio:  # Wider than target
                new_width = int(h * target_aspect_ratio)
                crop_x = (w - new_width) // 2
                frame_rgb = frame_rgb[:, crop_x:crop_x + new_width]
            else:  # Taller than target
                new_height = int(w / target_aspect_ratio)
                crop_y = (h - new_height) // 2
                frame_rgb = frame_rgb[crop_y:crop_y + new_height, :]

            # Resize the cropped frame to fit the desired size
            frame_resized = cv2.resize(frame_rgb, (self.width, self.height))

            # Convert to QImage
            img = QImage(frame_resized.data, self.width, self.height, self.width * ch, QImage.Format_RGB888)

            # Convert QImage to QPixmap and display
            pixmap = QPixmap.fromImage(img)
            self.setPixmap(pixmap)

    def closeEvent(self, event):
        """Release video capture when window is closed."""
        self.cap.release()
        event.accept()


class LoadSceneTask(QRunnable):
    """Thread pour charger une QGraphicsScene en arrière-plan"""
    def __init__(self, parent, width, height):
        super().__init__()
        self.parent = parent  # Référence au widget VideoThumbnail
        self.width = width
        self.height = height
        self.signals = WorkerSignals()

    def run(self):
        self.signals.scene_ready.emit()


class VideoThumbnail(QWidget):
    selected_changed = Signal(object, bool)
    def __init__(self, asset, video_path, thumbnail_path, preview_size,tags=[], parent=None, create_scene_by_thread=True):
        super(VideoThumbnail, self).__init__(parent)

        self.w = preview_size[0]
        self.h = preview_size[1]
        self.preview_size = preview_size
        self.setFixedSize(QSize(self.w, self.h))
        self.setContentsMargins(0, 0, 0, 0)
        self.asset = asset
        self.video_path = video_path
        self.thumbnail_path = thumbnail_path
        self.selected = False
        self.tags = tags
        self.parent = parent
        # Graphics View and Scene
        self.graphics_view = QGraphicsView(self)
        self.graphics_view.setGeometry(0, 0, self.w, self.h)  # Match button size
        self.graphics_view.setStyleSheet("background: transparent; border: none;")
        self.graphics_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.graphics_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        #self.scene = QGraphicsScene(self)
        self.graphics_view.viewport().installEventFilter(self)
        if not create_scene_by_thread:
            self.scene = QGraphicsScene()
            self.scene.setSceneRect(0, 0, self.w, self.h)
            self.graphics_view.setScene(self.scene)
            self.setupUI(asset)
        else:
            self.scene = None
            self.load_scene_async()


    def load_scene_async(self):
        """Lance un thread pour charger la scène sans bloquer l'UI"""

        task = LoadSceneTask(self, self.w, self.h)
        task.signals.scene_ready.connect(self.setSceneAsync)
        self.parent.thread_pool.start(task,200)


    def setSceneAsync(self):
        """Slot appelé en thread principal pour mettre à jour la scène"""
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        self.scene = QGraphicsScene()
        self.scene.setSceneRect(0, 0, self.w, self.h)
        self.graphics_view.setScene(self.scene)  # Appliquer la scène sans bloquer l'UI
        self.setupUI(self.asset)
        QApplication.restoreOverrideCursor()
        QApplication.restoreOverrideCursor()


    def setupUI(self,asset):

        # Thumbnail
        #pixmap = QPixmap(self.thumbnail_path).scaled(
        #    self.w, self.h, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
        #)
        self.thumbnail_item = QGraphicsPixmapItem()
        self.thumbnail_item.setZValue(0)
        # Center the thumbnail in the scene
        #thumbnail_x = (self.w - pixmap.width()) / 2
        #thumbnail_y = (self.h - pixmap.height()) / 2
        #self.thumbnail_item.setPos(thumbnail_x, thumbnail_y)
        self.scene.addItem(self.thumbnail_item)

        # Asset name overlay with shadow
        font = QFont('Lexend', 12)
        text_color = Qt.white
        shadow_color = QColor(0, 0, 0, 100)  # Black shadow with some transparency

        # Shadow Text Item
        self.asset_name_shadow = QGraphicsTextItem(asset)
        self.asset_name_shadow.setFont(font)
        self.asset_name_shadow.setDefaultTextColor(shadow_color)
        self.asset_name_shadow.setZValue(49)  # Just below the main text
        self.scene.addItem(self.asset_name_shadow)

        # Main Text Item
        self.asset_name_item = QGraphicsTextItem(asset)
        self.asset_name_item.setFont(font)
        self.asset_name_item.setDefaultTextColor(text_color)
        self.asset_name_item.setZValue(50)  # Ensure text always appears on top
        self.scene.addItem(self.asset_name_item)

        # Center the text horizontally and position it slightly above the bottom
        text_width = self.asset_name_item.boundingRect().width()
        text_x = (self.w - text_width) / 2
        text_y = self.h - 30

        # Position both text items
        self.asset_name_item.setPos(text_x, text_y)
        self.asset_name_shadow.setPos(text_x + 1, text_y + 1)  # Slight offset for shadow

        self.video_widget = None

        # Save initial preview size
        self.original_preview_size = QSize(*self.preview_size)
        self.setSize(*self.preview_size)
        self.update_visual_cue()

    def set_thumbnail(self,pixmap=None):
        if not pixmap:
            pixmap = QPixmap(self.thumbnail_path).scaled(
                self.w, self.h, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
            )
        self.thumbnail_item.setPixmap(pixmap)
        self.thumbnail_item.setZValue(0)
        # Center the thumbnail in the scene
        thumbnail_x = (self.w - pixmap.width()) / 2
        thumbnail_y = (self.h - pixmap.height()) / 2
        self.thumbnail_item.setPos(thumbnail_x, thumbnail_y)
        #print("need update")

    def setSize(self, width, height):
        self.w, self.h = width, height
        self.setFixedSize(QSize(self.w, self.h))
        self.graphics_view.setGeometry(0, 0, self.w, self.h)
        self.scene.setSceneRect(0, 0, self.w, self.h)

    def setThumbnailSize(self, width, height):
        scale = self.w/500
        self.thumbnail_item.setScale(scale)
        pixmap = self.thumbnail_item.pixmap()
        thumbnail_x = (500-pixmap.width())/2*scale
        self.thumbnail_item.setPos(thumbnail_x, 0)
        # Reposition text overlays
        text_width = self.asset_name_item.boundingRect().width()
        text_x = (width - text_width) / 2
        text_y = height - 30
        self.asset_name_item.setPos(text_x, text_y)
        self.asset_name_shadow.setPos(text_x + 1, text_y + 1)
        self.asset_name_shadow.setZValue(49)
        self.asset_name_item.setZValue(50)
        self.update()

    def eventFilter(self, watched, event):
        if watched == self.graphics_view.viewport():
            if event.type() == QEvent.MouseMove:
                self.mouseMoveEvent(event)
                return True  # Mark event as handled
            if event.type() == QEvent.MouseButtonRelease:
                self.mouseReleaseEvent(event)
                return True  # Mark event as handled
        return super(VideoThumbnail, self).eventFilter(watched, event)

    def mouseMoveEvent(self, event):
        super(VideoThumbnail, self).mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        super(VideoThumbnail, self).mouseReleaseEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        super(VideoThumbnail, self).mousePressEvent(event)

        try:
            if self.parent:
                modifiers = QApplication.keyboardModifiers()
                if event.button() == Qt.LeftButton:
                    # Gestion des modificateurs
                    if modifiers == Qt.ShiftModifier:  # Ajout à la sélection
                        pass
                    elif modifiers == Qt.ControlModifier:
                        #print("retrait de la selection")
                        self.selected =False
                        self.update_visual_cue()
                        self.selected_changed.emit(self,self.selected)
                        return
                        pass
                    else:  # Sélection simple
                        self.parent.clear_selection()  # Supprime toutes les sélections

                    self.toggle_selection()

                    self.selected_changed.emit(self,self.selected)  # Émet un signal pour notifier le changement
                if event.button() == Qt.RightButton:
                    self.selected = True
                    self.update_visual_cue()
                    self.selected_changed.emit(self, self.selected)
        except:
            print(traceback.format_exc())

    def enterEvent(self, event):
        super(VideoThumbnail, self).enterEvent(event)
        try:
            if self.parent:
                self.hold_cursor = self.parent.viewport().cursor()
                self.parent.viewport().setCursor(Qt.PointingHandCursor)
            self.play_video()
        except:
            print(traceback.format_exc())

    def leaveEvent(self, event):
        try:
            if self.parent:
                self.parent.viewport().setCursor(self.hold_cursor)
                super(VideoThumbnail, self).leaveEvent(event)
            self.stop_video()
        except:
            print(traceback.format_exc())

    def play_video(self):
        try:
            """Starts the video when mouse hovers."""
            if self.parent:
                self.parent.thumbnail_timer.start(200)
            if not self.video_widget:
                self.video_widget = VideoPlayer(
                    self.video_path, (self.w, self.h), thumbnail_path=self.thumbnail_path
                )
                self.video_widget.setZValue(2)
                self.scene.addItem(self.video_widget)
                self.video_widget.start_video()
        except:
            print(traceback.format_exc())

    def stop_video(self):
        """Stops the video when mouse leaves."""
        if self.video_widget:
            self.video_widget.stop_video()
            self.scene.removeItem(self.video_widget)
            self.video_widget.cap.release()
            self.video_widget = None

    def toggle_selection(self):
        self.selected = not self.selected

        self.update_visual_cue()

    def set_selected(self, selected: bool):
        self.selected = selected
        self.update_visual_cue()
        self.selected_changed.emit(self, self.selected)

    def update_visual_cue(self):
        # Change border color to indicate selection
        if self.selected:
            self.graphics_view.setStyleSheet("background: transparent; border: 2px solid rgb(150, 250, 0)")
        else:
            self.graphics_view.setStyleSheet("background: transparent; border: None;")


class UnicVideoLoaderWorker(QRunnable):
    def __init__(self, video, video_gallery):
        super().__init__()
        self.video_gallery = video_gallery
        self.video = video
        self.signals = WorkerSignals()

    def run(self):
        try:
            if self.video["playblast"] and self.video["preview"]:
                visible = True
                if self.video_gallery.BDD_Browser:
                    if len(self.video_gallery.BDD_Browser.current_tags) > 0:
                        for tag in self.video_gallery.BDD_Browser.current_tags:
                            if tag not in self.video["tags"]:
                                visible = False
                    if self.video['asset'] in self.video_gallery.BDD_Browser.current_tags:
                        visible = True
                if '_ TRASH _' in self.video['tags']:
                    visible = False
                self.signals.video_load_signal.emit(self.video['asset'],
                                                    self.video["playblast"],
                                                    self.video["preview"],
                                                    self.video["tags"],
                                                    visible)
        except:
            print(traceback.format_exc())


class VideoLoaderWorker(QRunnable):
    def __init__(self, videos, video_gallery):
        super().__init__()
        self.video_gallery = video_gallery
        self.videos = videos
        self.signals = WorkerSignals()

    def run(self):
        try:
            for asset, data in self.videos.items():
                if data["playblast"] and data["preview"]:
                    visible = True
                    if self.video_gallery.BDD_Browser:
                        if len(self.video_gallery.BDD_Browser.current_tags) > 0:
                            for tag in self.video_gallery.BDD_Browser.current_tags:
                                if tag not in data["tags"]:
                                    visible = False
                        if asset in self.video_gallery.BDD_Browser.current_tags:
                            visible = True
                    if '_ TRASH _' in data['tags']:
                        visible = False
                    self.signals.video_load_signal.emit(asset, data["playblast"], data["preview"], data["tags"], visible)
            self.signals.finished.emit()
        except:
            print(traceback.format_exc())


class ThumbnailLoaderWorker(QRunnable):
    def __init__(self, thumbnails, gallery):
        super().__init__()
        self.thumbnails = thumbnails
        self.gallery = gallery
        self.signals = WorkerSignals()

    def run(self):
        try:
            for thumbnail in self.thumbnails:
                do = False
                index = self.thumbnails.index(thumbnail)
                if thumbnail['widget'].visibleRegion().isNull() is False:
                    do = True
                if index >= 9:
                    if self.thumbnails[index - 9]['widget'].visibleRegion().isNull() is False:
                        do = True
                if len(self.thumbnails) - index > 3:
                    if self.thumbnails[index + 3]['widget'].visibleRegion().isNull() is False:
                        do = True
                if do:
                    if thumbnail['widget'].thumbnail_item.pixmap().isNull():
                        if self.gallery.BDD_Browser:
                            if self.gallery.BDD_Browser.maya:
                                QThread.msleep(2)
                        QThread.usleep(1)
                        pixmap = QPixmap(thumbnail["preview"]).scaled(500,
                                                                      400,
                                                                      Qt.KeepAspectRatioByExpanding,
                                                                      Qt.SmoothTransformation)
                        self.signals.add_thumbnail_signal.emit(thumbnail['widget'], pixmap)
            self.signals.finished.emit()
        except:
            print(traceback.format_exc())


class RectSelectionWorker(QRunnable):
    def __init__(self, thumbnails, old_selection, selection_rect, add, remove):
        super().__init__()
        self.thumbnails = thumbnails
        self.selection = old_selection[:]
        self.add = add
        self.remove = remove
        self.selection_rect = selection_rect
        self.signals = WorkerSignals()

    def run(self):
        try:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            QThread.usleep(3)

            for thumbnail in self.thumbnails:
                widget = thumbnail["widget"]
                if self.add:
                    if self.selection_rect.intersects(widget.geometry()) and widget.isVisible() and widget not in self.selection:
                        self.selection.append(widget)
                elif self.remove:
                    if self.selection_rect.intersects(widget.geometry()) and widget.isVisible() and widget in self.selection:
                        self.selection.remove(widget)
                else:
                    if self.selection_rect.intersects(widget.geometry()) and widget.isVisible():
                        self.selection.append(widget)
                    else:
                        widget.set_selected(False)
            self.signals.selected_widgets.emit(self.selection)
            QApplication.restoreOverrideCursor()
        except:
            print(traceback.format_exc())


class UpdateGalleryWorker(QRunnable):
    def __init__(self, thumbnails, current_tag_list, gallery):
        super().__init__()
        self.thumbnails = thumbnails
        self.current_tags_list = current_tag_list
        self.gallery = gallery
        self.signals = WorkerSignals()

    def run(self):
        try:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            QThread.usleep(3)
            row, col = 0, 0
            for thumbnail in self.thumbnails:
                asset_name = thumbnail["asset"]
                widget = thumbnail["widget"]
                tags = thumbnail['tags']
                visible = True
                if len(self.current_tags_list) > 0:
                    for tag in self.current_tags_list:
                        if tag not in tags:
                            visible = False
                else:
                    visible = True
                if asset_name.lower() in self.current_tags_list:
                    visible = True
                if '_ TRASH _' in tags:
                    visible = False
                    if '_ TRASH _' in self.current_tags_list:
                        visible = True
                if visible:
                    self.signals.store_widget.emit(widget, row, col)
                    col = (col + 1) % self.gallery.column_number
                    row += col == 0
                    if self.gallery.BDD_Browser.maya:
                        #QThread.usleep(15)
                        pass
                else:
                    self.signals.remove_widget.emit(widget)
            QApplication.restoreOverrideCursor()
            self.signals.finished.emit()
        except:
            print(traceback.format_exc())


class ResizeWorker(QRunnable):
    def __init__(self, grid_layout, new_width, new_height):
        super().__init__()
        self.grid_layout = grid_layout
        self.new_width = new_width
        self.new_height = new_height
        self.signals = WorkerSignals()
    def run(self):
        try:
            for i in range(self.grid_layout.count()):
                widget = self.grid_layout.itemAt(i).widget()
                if isinstance(widget, VideoThumbnail):
                    widget.setSize(self.new_width, self.new_height)
            self.signals.resize_finished.emit()
        except:
            print(traceback.format_exc())


class ResizeThumbnailWorker(QRunnable):
    def __init__(self, grid_layout, new_width, new_height):
        super().__init__()
        self.grid_layout = grid_layout
        self.new_width = new_width
        self.new_height = new_height
        self.signals = WorkerSignals()

    def run(self):
        for i in range(self.grid_layout.count()):
            widget = self.grid_layout.itemAt(i).widget()
            if isinstance(widget, VideoThumbnail):
                self.signals.resize_thumbnail_signal.emit(widget, self.new_width, self.new_height)
        self.signals.finished.emit()


class SelectionOverlay(QFrame):
    def __init__(self, parent, scrollable_area):
        super().__init__(parent)
        self.setStyleSheet("background: transparent; border: 0px;")  # Temporary debug border
        self.selection_rect = QRect()
        # Debug the widget geometry
        # Set geometry to match the scrollable area's widget
        self.setGeometry(0,0,5000,5000)
        self.show()
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.parent = parent
        self.scrollable_area = scrollable_area

    def update_position(self,value,max):

        self.setGeometry(0,-value,5000,max+5000)

    def start_selection(self, QRect_Value):
        try:
            self.selection_rect = QRect_Value
            self.update()
        except Exception:
            print(traceback.format_exc())

    def update_selection(self,QRect_Value):
        try:
            self.selection_rect = QRect_Value
            self.update()

        except Exception:
            print(traceback.format_exc())

    def clear_selection(self):
        try:
            self.selection_rect = QRect()
            self.update()
        except Exception:
            print(traceback.format_exc())

    def paintEvent(self, event):
        try:
            painter = QPainter(self)
            painter.setPen(QPen(Qt.green, 2, Qt.DashLine))
            painter.setBrush(QColor(0, 255, 0, 50))
            painter.drawRect(self.selection_rect)
            painter.end()
        except Exception:
            print(traceback.format_exc())


class VideoGallery(QScrollArea):
    customContextMenuRequested = Signal(object,object,list)
    selection_changed = Signal(list)

    def __init__(self, videos, column_number=3, parente=None):
        super().__init__()
        self.video_data = videos  # Store video data for filtering
        self.thumbnails = []  # Store references to thumbnails for quick access
        self.is_dragging = False
        self.start_pos = None
        self.column_number = column_number
        self.BDD_Browser = parente
        # Scrollable area
        self.setWidgetResizable(True)

        # Main widget and layout for the gallery
        self.gallery_widget = QWidget(self)
        self.gallery_widget.setStyleSheet("background-color: rgb(43, 54, 58)")
        self.setWidget(self.gallery_widget)

        self.grid_layout = QGridLayout(self.gallery_widget)
        self.gallery_widget.setLayout(self.grid_layout)
        self.cached_width = self.width()

        gallery_width = self.width()-20
        num_columns = self.column_number  # Fixed number of columns
        new_width = gallery_width // num_columns - 10  # Add margin spacing
        new_height = int(new_width * 0.8)
        self.new_width = new_width
        self.new_height = new_height

        # Populate gallery
        self.thread_pool = QThreadPool.globalInstance()
        self.thread_pool.setMaxThreadCount(100)

        self.thumbnail_timer = QTimer(self)
        self.thumbnail_timer.setSingleShot(True)  # Only trigger once after the timeout
        self.thumbnail_timer.timeout.connect(self.update_visible_widgets)
        self.populate_worker = None
        self.thumbnails_runtime_worker = None
        self.rect_sel_worker = None
        self.update_gallery_worker = None
        self.populate_thumbnails()

        # Create a timer to delay resize
        self.resize_worker = None
        self.resize_thumbnail_worker= None
        self.resize_timer = QTimer(self)
        self.resize_timer.setSingleShot(True)  # Only trigger once after the timeout
        self.resize_timer.timeout.connect(self.on_resize_timeout)

        # Create a timer to delay rectSelection
        self.rect_selection_timer = QTimer(self)
        self.rect_selection_timer.setSingleShot(True)  # Only trigger once after the timeout
        self.rect_selection_timer.timeout.connect(self.on_rect_selection_timeout)
        self.rect_selection_add = False
        self.rect_selection_remove = False

        self.selected_items = []
        self.oldSelection = []

        # Add the selection overlay
        self.selection_overlay = SelectionOverlay(self,self)

        self.verticalScrollBar().valueChanged.connect(self.scrollBar_Value_Changed)

    # __________ LOAD Thumbnails _____________

    def addUnicthumbnail(self,asset):
        try:
            task = UnicVideoLoaderWorker(asset, self)
            task.signals.video_load_signal.connect(self.add_thumbnail_to_gallery)
            task.signals.finished.connect(self.on_videos_loaded)
            self.thread_pool.start(task,200)
        except:
            print(traceback.format_exc())

    def populate_thumbnails(self):
        """Start the populate operation in a separate thread."""
        print("Start the populate operation in a separate thread.")
        try:
            task = VideoLoaderWorker(self.video_data, self)
            task.signals.video_load_signal.connect(self.add_thumbnail_to_gallery)
            task.signals.finished.connect(self.on_videos_loaded)
            self.thread_pool.start(task,200)
        except:
            print(traceback.format_exc())

    def update_pixmap(self,widget,pixmap):
        widget.set_thumbnail(pixmap)
        widget.setThumbnailSize(self.new_width, self.new_height)

    def add_thumbnail_to_gallery(self, asset, playblast, preview, tags, visible):
        """This method adds a thumbnail to the gallery from the worker thread."""
        try:
            row = self.grid_layout.count() // self.column_number
            col = self.grid_layout.count() % self.column_number
            thumbnail = VideoThumbnail(asset, playblast, preview, (self.new_width,self.new_height), tags, self)

            if visible:
                self.grid_layout.addWidget(thumbnail, row, col)

            thumbnail.selected_changed.connect(self.update_selection)
            self.thumbnails.append({"widget": thumbnail,
                                    "asset": asset,
                                    "playblast": playblast,
                                    "preview": preview,
                                    "tags": tags})
            thumbnail.setContextMenuPolicy(Qt.CustomContextMenu)
            thumbnail.customContextMenuRequested.connect(
                lambda pos, thumbnail=thumbnail: self.open_context_menu(pos, thumbnail)
            )
            if row == 0 and col == 0:
                thumbnail.toggle_selection()
                self.selected_items.append(thumbnail)
                self.selection_changed.emit(self.selected_items)

        except:
            print(traceback.format_exc())

    def on_videos_loaded(self):
        """This method is called when all videos are loaded."""
        print("Video loading is complete.")
        self.thumbnail_timer.start(10)
        # You can do something after all videos are loaded if needed

    def open_context_menu(self, pos: QPoint, thumbnail):
        """Open a context menu for a thumbnail."""
        self.customContextMenuRequested.emit(pos,thumbnail,self.selected_items)

    # ___________ UPDATE Gallery _____________

    def update_gallery(self,current_tags_list):
        self.thread_pool.clear()
        task = UpdateGalleryWorker(self.thumbnails,current_tags_list,self)
        task.signals.store_widget.connect(self.store_widget)
        task.signals.remove_widget.connect(self.remove_widget)
        self.thread_pool.start(task,100)

    def store_widget(self,widget,row,col):
        widget.setVisible(True)
        self.grid_layout.removeWidget(widget)
        self.grid_layout.addWidget(widget, row, col)
        self.thumbnail_timer.start(10)

    def remove_widget(self,widget):
        try:
            widget.setVisible(False)
        except:
            print(traceback.format_exc())

    def update_visible_widgets(self):
        #print('___________ check for visible widgets ______________')
        try:
            self.thread_pool.clear()
            task = ThumbnailLoaderWorker(self.thumbnails,self)
            task.signals.add_thumbnail_signal.connect(self.update_pixmap)
            self.thread_pool.start(task)
        except:
            print(traceback.format_exc())

    # ___________ SELECTION _____________

    def update_selection(self, widget: object, selected: bool):
        # Clear the selection and update the selected items
        try:
            if selected:
                if widget not in self.selected_items:
                    self.selected_items.append(widget)
            else:
                if widget in self.selected_items:
                    self.selected_items.remove(widget)
            self.selection_changed.emit(self.selected_items)
        except:
            print(traceback.format_exc())

    def clear_selection(self):
        #print([item.asset for item in self.selected_items])
        removelist = self.selected_items[:]
        for item in removelist:
            self.selected_items.remove(item)
            item.set_selected(False)

        self.selection_changed.emit(self.selected_items)

    def mousePressEvent(self, event: QMouseEvent):
        self.left_click = False
        if event.button() == Qt.LeftButton:
            self.left_click = True
            self.start_pos= event.pos()+QPoint(0, self.verticalScrollBar().value())

    def mouseMoveEvent(self, event: QMouseEvent):
        super(VideoGallery, self).mouseMoveEvent(event)
        try:
            if self.left_click:
                self.is_dragging = True
            modifiers = QApplication.keyboardModifiers()
            if self.is_dragging:
                self.viewport().setCursor(Qt.CrossCursor)
                # Défilement automatique si nécessaire
                if event.pos().y() < 30:  # Haut de la vue
                    self.verticalScrollBar().setValue(self.verticalScrollBar().value() - int((30-event.pos().y())/2))
                elif event.pos().y() > self.height() - 30:  # Bas de la vue
                    self.verticalScrollBar().setValue(self.verticalScrollBar().value() +
                                                      int((event.pos().y()-(self.height() - 30))/2))
                self.end_point = event.pos() + QPoint(0, self.verticalScrollBar().value())
                self.selection_rect = QRect(self.start_pos, self.end_point).normalized()
                self.selection_overlay.update_selection(self.selection_rect)
                if modifiers == Qt.ShiftModifier:  # Ajout à la sélection
                    self.rect_selection_add = True
                    self.rect_selection_remove = False
                elif modifiers == Qt.ControlModifier:
                    self.rect_selection_remove=True
                    self.rect_selection_add = False
                else:
                    self.rect_selection_remove=False
                    self.rect_selection_add = False
                #self.rect_selection_timer.start(500)
        except:
            print(traceback.format_exc())

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self.is_dragging:
            self.select_items_within_box()
        self.left_click = False
        if event.button() == Qt.LeftButton and self.is_dragging:
            self.is_dragging = False
            self.update()
            self.selection_overlay.clear_selection()
            self.viewport().setCursor(Qt.ArrowCursor)
            self.oldSelection = []
            for thumbnail in self.thumbnails:
                widget = thumbnail["widget"]
                if widget.selected:
                    self.oldSelection.append(widget)

            # Perform selection logic
            #self.on_rect_selection_timeout()
            #self.select_items_within_box()


    def scrollBar_Value_Changed(self,value):
        max = self.verticalScrollBar().maximum()
        self.selection_overlay.update_position(value,max)
        self.thumbnail_timer.start(400)

    def on_rect_selection_timeout(self):
        self.select_items_within_box()

    def select_items_within_box(self):
        try:
            self.thread_pool.clear()
            task = RectSelectionWorker(self.thumbnails,self.selected_items,self.selection_rect,self.rect_selection_add,self.rect_selection_remove)
            task.signals.selected_widgets.connect(self.rect_selected_items)
            self.thread_pool.start(task,100)
        except:
            print(traceback.format_exc())

    def rect_selected_items(self,selection):
        self.clear_selection()
        for widget in selection:
            try:
                widget.set_selected(True)
            except:
                print(traceback.format_exc())

    # ___________ RESIZE ______________

    def on_resize_timeout(self):
        """Called when the resize timer times out."""
        # Perform the actual resize operation in a background thread
        self.update_thumbnails_size(self.new_width, self.new_height)

    def start_resize(self):
        """Start the resize process with a delay, called when the user changes size."""
        # Determine new size for thumbnails based on gallery width
        gallery_width = self.width()-20
        num_columns = self.column_number  # Fixed number of columns
        new_width = gallery_width // num_columns - 10  # Add margin spacing
        new_height = int(new_width * 0.8)
        self.new_width = new_width
        self.new_height = new_height
        try:
            self.resize_timer.start(100)  # Start the timer, and wait 30ms before resizing
        except:
            print(traceback.format_exc())

    def resizeEvent(self,event):
        super(VideoGallery, self).resizeEvent(event)
        self.start_resize()

    def update_thumbnails_size(self, new_width, new_height):
        """Start the resizing operation in a separate thread."""
        try:
            self.thread_pool.clear()
            task = ResizeWorker(self.grid_layout, new_width, new_height)
            task.signals.resize_finished.connect(self.on_resize_finished)
            self.thread_pool.start(task)

            thumbnail_task = ResizeThumbnailWorker(self.grid_layout, new_width, new_height)
            thumbnail_task.signals.resize_thumbnail_signal.connect(self.resize_thumbnail)
            thumbnail_task.signals.finished.connect(self.on_resize_finished)
            self.thread_pool.start(thumbnail_task)

        except:
            print(traceback.format_exc())

    def on_resize_finished(self):
        """This method is called when resizing is finished."""
        pass
        #print("Thumbnail resizing is complete.")

    def resize_thumbnail(self, widget , width, height):
        widget.setThumbnailSize(width,height)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    path_to_chars = r"P:\__PROD__\Tsunami\BDD\01_Workflow\Assets\CHARS"
    assets_dict = {}
    all_assets = glob(path_to_chars+'\\*')
    for asset in all_assets:
        asset_name = asset.split('\\')[-1]
        asset_preview = f'P:\__PROD__\Tsunami\BDD\\00_Pipeline\Assetinfo\\{asset_name}_preview.jpg'
        all_blasts = []
        for root,dirs,files in os.walk(f'{asset}\\Playblasts'):
            for file in files:
                if file.endswith('.mp4'):
                    all_blasts.append(root+'\\'+file)
        if len(all_blasts) > 0:
            asset_blast = all_blasts[-1]
        else:
            asset_blast = None
        assets_dict[asset_name] = {"preview": asset_preview,
                                   "playblast": asset_blast,
                                   "tags":[]}
    print(assets_dict)

    gallery = VideoGallery(assets_dict,3)
    gallery.resize(800, 600)
    gallery.show()

    sys.exit(app.exec_())
