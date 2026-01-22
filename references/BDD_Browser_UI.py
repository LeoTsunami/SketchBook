import shutil
import traceback
from glob import glob
import json
import os
import sys

from qtpy.QtCore import *
from qtpy.QtGui import *

from qtpy.QtWidgets import *
import subprocess

currentFilePath = __file__.replace('\\', '/')
TsunamiPath = '/'.join(currentFilePath.split('/')[:-3])
if TsunamiPath not in sys.path:
    sys.path.append(TsunamiPath)
from Scripts.BDD_Browser import BDD_VideoGallery

from Scripts.Tsunami_Module import TsuFunctions
from Scripts.Tsunami_Module import TsuUi

# Ensure that the custom cv2 module is loaded by clearing it from sys.modules first
if 'cv2' in sys.modules:
    del sys.modules['cv2']
# Ensure that the custom cv2 module is loaded by clearing it from sys.modules first
import cv2
if sys.version_info[1] <= 7:
    if 'numpy' in sys.modules:
        del sys.modules['numpy']

from importlib import reload
reload(TsuUi)
reload(BDD_VideoGallery)

iconPath = __file__.split('\Scripts\\')[0]+r"\Ressources\Icon/"
BDD_Path = r"P:\__PROD__\Tsunami\BDD"
BDD_dataBase = f'{BDD_Path}\\00_Pipeline\Assetinfo\\assetInfo.json'
BDD_commonTags = f'{BDD_Path}\\00_Pipeline\Assetinfo\\commonTags.json'

def read_database():
    with open(BDD_dataBase, 'r') as f:
        database = json.load(f)
        assets_database = database["assets"]
        return assets_database


def write_database(assets_database):
    with open(BDD_dataBase, 'r') as f:
        database = json.load(f)
        database["assets"] = assets_database
    with open(BDD_dataBase, 'w') as f:
        json.dump(database, f,indent=4)


def write_commonTags(commonTags):
    with open(BDD_commonTags, 'w') as f:
        json.dump(commonTags, f,indent=4)


def read_commonTags():
    if not os.path.exists(BDD_commonTags):
        commonTags = {"Projets":[]}
        write_commonTags(commonTags)
    with open(BDD_commonTags, 'r') as f:
        commonTags = json.load(f)
        return commonTags


def add_item(item_name,tags,preview_path =""):
    print(f'Ajout de {item_name} à la data base')
    assets_database = read_database()
    for tag in tags:
        if item_name not in assets_database:
            assets_database[item_name] = {"metadata": {}, "playblast": "", "preview": preview_path, "tags": []}
        if not tag in assets_database[item_name]["tags"]:
            assets_database[item_name]["tags"].append(tag)
            print(f"ajout du tag {tag} a {item_name}")
    write_database(assets_database)


class CustomSlider(QSlider):
    def __init__(self, orientation=Qt.Horizontal, parent=None):
        super().__init__(orientation, parent)
        self.setOrientation(orientation)

    def mousePressEvent(self, event):
        if self.orientation() == Qt.Horizontal:
            pos = event.pos().x() / self.width()  # Position relative dans le slider (0.0 à 1.0)
        else:
            pos = 1.0 - (event.pos().y() / self.height())  # Inversé pour correspondre aux valeurs

        value = self.minimum() + pos * (self.maximum() - self.minimum())
        self.setValue(int(value))  # Définit immédiatement la nouvelle valeur

        super().mousePressEvent(event)  # Continue le comportement normal du QSlider


class VideoPlayerWidget(QWidget):
    def __init__(self, video_path):
        super().__init__()
        self.video_path = video_path
        self.cap = cv2.VideoCapture(video_path)

        if not self.cap.isOpened():
            pass
            #raise ValueError("Cannot open video file")

        self.frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.current_frame = 0
        self.is_playing = False

        # GUI Setup
        self.setWindowTitle("Video Player")
        #self.setMinimumSize(320, 180)

        self.video_label = QLabel()
        self.video_label.setScaledContents(True)
        #self.video_label.setMinimumSize(320, 180)
        #self.video_label.setMaximumSize(1280, 720)

        self.timeline_slider = CustomSlider(Qt.Horizontal)
        self.timeline_slider.setRange(0, self.frame_count - 1)
        self.timeline_slider.valueChanged.connect(self.on_slider_changed)
        self.timeline_slider.setValue(1)
        self.timeline_slider.setValue(0)

        self.play_button = QPushButton("Play")
        self.play_button.clicked.connect(self.toggle_playback)

        self.first_frame_label = QLabel("0")
        self.last_frame_label = QLabel(str(self.frame_count - 1))

        # Layouts
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.first_frame_label)
        button_layout.addWidget(self.timeline_slider)
        button_layout.addWidget(self.last_frame_label)
        button_layout.addWidget(self.play_button)


        main_layout = QVBoxLayout()
        main_layout.addWidget(self.video_label)
        main_layout.addLayout(button_layout)

        self.setLayout(main_layout)

        # Timer for video playback
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.play_video)

    def play_video(self):
        if self.is_playing:
            ret, frame = self.cap.read()
            if not ret:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                self.current_frame = 0
                return

            self.current_frame += 1
            self.timeline_slider.setValue(self.current_frame)
            self.display_frame(frame)

    def toggle_playback(self):
        self.is_playing = not self.is_playing
        if self.is_playing:
            self.timer.start(30)
            self.play_button.setText("Pause")
        else:
            self.timer.stop()
            self.play_button.setText("Play")

    def on_slider_changed(self, value):
        self.current_frame = value
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
        ret, frame = self.cap.read()
        if ret:
            self.display_frame(frame)

    def display_frame(self, frame):
        frame = cv2.resize(frame, (self.video_label.width(), int(self.video_label.width()/1.77)))
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        height, width, channel = frame_rgb.shape
        bytes_per_line = channel * width
        q_image = QImage(frame_rgb.data, width, int(width/1.77), bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(q_image)
        self.video_label.setPixmap(pixmap)

    def change_video(self,new_video_path):
        # Example of changing video dynamically
        self.video_path = new_video_path
        self.cap.release()
        self.cap = cv2.VideoCapture(new_video_path)

        if not self.cap.isOpened():
            raise ValueError("Cannot open the new video file")

        self.frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.current_frame = 0
        self.timeline_slider.setRange(0, self.frame_count - 1)
        self.first_frame_label.setText("0")
        self.last_frame_label.setText(str(self.frame_count - 1))

        # Reset playback
        self.is_playing = False
        self.timer.stop()
        self.play_button.setText("Play")

        # Display the first frame of the new video
        ret, frame = self.cap.read()
        if ret:
            self.display_frame(frame)

    def resizeEvent(self, event):
        self.video_label.setFixedHeight(int(self.width()/1.77))
        pass

    def closeEvent(self, event):
        self.cap.release()
        event.accept()


class search_tag_widget(QWidget):
    delete_button_signal = Signal(object)
    def __init__(self, tag_name,parenter,item=None):
        super(search_tag_widget, self).__init__()
        self.tag_name = tag_name
        self.parenter = parenter
        self.item = item
        # Set the size and style of the widget
        self.setMinimumSize(100, 40)
        self.setStyleSheet("""
            background-color: rgba(0, 0, 0, 51);
            border-radius: 7px;
            padding: 0px 0px;
        """)

        # Enable transparent background support
        #self.setAttribute(Qt.WA_StyledBackground, True)
        #self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.layout_horizontal = QHBoxLayout(self)
        self.layout_horizontal.setContentsMargins(5, 5, 5, 5)  # Add some padding

        self.label_tag_name = QLabel(self.tag_name)
        fnt = QFont('Lexend', 10)
        self.label_tag_name.setFont(fnt)
        self.label_tag_name.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        self.label_tag_name.setStyleSheet("color: white;")  # Ensure label text is visible
        self.layout_horizontal.addWidget(self.label_tag_name)
        self.delete_button = QPushButton('x')
        self.delete_button.setFixedSize(QSize(20,20))
        self.delete_button.setStyleSheet("""
            QPushButton {
                color: white;
                background-color: rgba(0, 0, 0, 0.2); /* Red background for the button */
                border-radius: 10px; /* Rounded corners for the button */
                padding: 0px 0px;
            }
            QPushButton:hover {
                color: white;
                background-color: rgba(0, 0, 0, 0.1); /* Lighter red on hover */
                padding: 0px 0px;
            }
            QPushButton:pressed {
                color: white;
                background-color: rgba(0, 0, 0, 0.5); /* Darker red when pressed */
                padding: 0px 0px;
            }
        """)
        self.layout_horizontal.addWidget(self.delete_button)
        self.delete_button.clicked.connect(self.on_delete_button_clicked)

    def on_delete_button_clicked(self):
        """Handle the delete button click event."""
        #self.parenter.remove_search_tag(self)
        self.delete_button_signal.emit(self)


class commons_tag_button(QPushButton):
    def __init__(self,text,BDD_Browser):
        super(commons_tag_button, self).__init__(text)
        self.BDD_Browser = BDD_Browser
        self.tag_name = text
        fnt = QFont('Lexend',11)
        self.setFont(fnt)
        self.setStyleSheet("""
            QPushButton {
                background-color: rgba(20, 110, 230, 100);
                border-radius: 7px;
                color: white;
                padding: 0px 0px;  /* padding vertical 8px, horizontal 15px */
            }
        """)

        if BDD_Browser.prism and not BDD_Browser.maya:
            text_width = self.fontMetrics().boundingRect(self.text()).width()+ 20
            text_height = self.fontMetrics().boundingRect(self.text()).height()+2
        else:
            text_width = self.fontMetrics().boundingRect(self.text()).width() + 15
            text_height= self.fontMetrics().boundingRect(self.text()).height() -3
        self.setFixedSize(text_width, text_height)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.BDD_Browser.add_commons_tag(self)


class add_tags_window(QDialog):
    def __init__(self, selected_items, completion_list, parent):
        super(add_tags_window, self).__init__()
        self.selected_items = selected_items
        self.completion_list = completion_list

        self.parent = parent
        self.current_tags = []
        self.setMinimumSize(500, 200)
        self.setStyleSheet("background-color: rgb(43, 54, 58)")
        self.setup_Ui()

    def setup_Ui(self):
        try:
            print('SETUP UI')
            fnt = QFont('Lexend', 10)

            # MAIN WIDGET / LAYOUT
            self.layout_vertical_main = QVBoxLayout(self)
            self.setLayout(self.layout_vertical_main)

            #    HORIZONTAL LAYOUT 01
            self.layout_horizontal_01 = QHBoxLayout()
            self.layout_horizontal_01.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
            self.layout_vertical_main.addLayout(self.layout_horizontal_01)
            #        TITLE: TODO create png for text instead
            self.label_title_01 = QLabel("Add tags :")
            self.label_title_01.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            font = QFont('Lexend', 15)
            font.setBold(True)
            self.label_title_01.setFont(font)
            self.label_title_01.setStyleSheet("color: white;")
            self.layout_horizontal_01.addWidget(self.label_title_01)
            spacer = QSpacerItem(50, 0)
            self.layout_horizontal_01.addItem(spacer)
            #       SEARCH BAR:
            self.lineEdit_search = QLineEdit()
            self.lineEdit_search.setFixedHeight(25)
            self.lineEdit_search.setMinimumWidth(200)
            self.lineEdit_search.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.lineEdit_search.setFont(fnt)
            self.layout_horizontal_01.addWidget(self.lineEdit_search)
            self.model = QStandardItemModel()
            completer = QCompleter(self.model, self)
            completer.setCompletionMode(QCompleter.InlineCompletion)
            self.lineEdit_search.setCompleter(completer)
            for item in self.completion_list:
                if not self.model.findItems(item):
                    self.model.appendRow(QStandardItem(item))
            self.lineEdit_search.editingFinished.connect(self.add_search_tag)

            #   HORIZONTAL LAYOUT 02
            self.layout_horizontal_02 = QHBoxLayout()
            self.layout_horizontal_02.setAlignment(Qt.AlignLeft | Qt.AlignTop)
            self.layout_vertical_main.addLayout(self.layout_horizontal_02)
            #        TITLE: TODO create png for text instead
            self.label_title_02 = QLabel("Current Tags:")
            self.label_title_02.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            font = QFont('Lexend', 11)
            font.setBold(True)
            self.label_title_02.setFont(font)
            self.label_title_02.setStyleSheet("color: white;")
            self.layout_horizontal_02.addWidget(self.label_title_02)
            spacer2 = QSpacerItem(50, 0)
            self.layout_horizontal_02.addItem(spacer2)
            #       HORIZONTAL LAYOUT 03
            self.layout_horizontal_03 = QHBoxLayout()
            self.layout_horizontal_03.setAlignment(Qt.AlignRight | Qt.AlignTop)
            self.layout_horizontal_02.addLayout(self.layout_horizontal_03)

            self.accept_button = QPushButton("Apply")
            self.accept_button.setFont(fnt)
            self.layout_vertical_main.addWidget(self.accept_button)
            self.accept_button.setEnabled(False)
            self.accept_button.clicked.connect(self.on_apply)

        except:
            print(traceback.format_exc())

    def add_search_tag(self):
        try:
            entryItem = self.lineEdit_search.text()
            self.lineEdit_search.clear()
            if entryItem and entryItem not in self.current_tags:
                self.current_tags.append(entryItem)
                itemWiget = search_tag_widget(entryItem, self)
                itemWiget.delete_button_signal.connect(self.remove_search_tag)
                self.layout_horizontal_03.addWidget(itemWiget)
                self.update_ui()
        except:
            print(traceback.format_exc())

    def remove_search_tag(self,tag_widget):
        print('remove')
        try:
            print(tag_widget)
            self.current_tags.remove(tag_widget.tag_name)
            self.layout_horizontal_03.removeWidget(tag_widget)
            tag_widget.deleteLater()
            self.update_ui()
        except:
            print(traceback.format_exc())

    def update_ui(self):
        if len(self.current_tags)>0:
            self.accept_button.setEnabled(True)
        else:
            self.accept_button.setEnabled(False)

    def on_apply(self):
        print(f"Apply {self.current_tags}\nto {self.selected_items}")
        try:
            for item in self.selected_items:
                item_name = item.asset
                if item_name in self.parent.assets_database:
                    for tag in self.current_tags:
                        if not tag in self.parent.assets_database[item_name]["tags"]:
                            self.parent.assets_database[item_name]["tags"].append(tag)
                        if tag not in self.parent.completion_list:
                            self.parent.completion_list.append(tag)
                        for thumnail in self.parent.video_gallery_assets.thumbnails:
                            if thumnail["asset"] == item_name:
                                if not tag in thumnail["tags"]:
                                    thumnail["tags"].append(tag)
            self.parent.update_completion_list()
            self.parent.display_item_tags()
            write_database(self.parent.assets_database)

            self.close()
        except:
            print(traceback.format_exc())


class BDD_MainWindow(TsuUi.CustomDockableWindow):
    def __init__(self, parent=None,pcore=None, title="BDD Browser", min_size=(1500, 700)):

        super(BDD_MainWindow, self).__init__(parent,title,min_size)
        self.prism = True
        self.pcore = pcore
        self.maya = True
        if not pcore:
            self.prism = False
            print("No prism instance")
        try:
            import maya.cmds as cmds
        except:
            self.maya = False
            print("No maya instance")
        fnt = QFont('Lexend', 10)
        self.completion_list = []
        self.current_tags = []
        self.common_tags= {'Categories': {"chars": ["humain", "animal", "biped", "quadruped", "volant"],
                                          "props": ["arme", "salle de bain", "batiment", "vetement", "affichage",
                                                    "nourriture", "decoration", "medical", "cuisine", "technologie",
                                                    "musique", "nature", "ecole/bureau", "fete", "sport", "vacances",
                                                    "outils", "jouet"],
                                          "vehicules": ["terrestre", "aerien", "maritime"],
                                          "fx": ["2d", "3d"],
                                          "sets": ["ville", "nature", "interieur"]},
                           'Styles': ["cartoon", "semi realiste", "realiste"],
                           'Periodes': ["medieval", "science fiction", "contemporain", "western"],
                           'Formats': ["maya", "blender", "fbx", "obj", "abc"], "Projets": read_commonTags()["Projets"],
                           'Most commons': []}

        self.import_settings = []
        if self.prism and self.maya:
            self.import_settings.append('Project and current Maya scene (reference)')
        if self.prism:
            self.import_settings.append('Only Project')
        if self.maya:
            self.import_settings.append('Only Maya scene (hard import)')
        self.title=title
        self.assets_database = read_database()
        self.window.setAutoFillBackground(True)
        pal = QPalette()
        pal.setColor(QPalette.Window,QColor(43, 54, 58))
        self.window.setPalette(pal)
        self.setup_Ui()
        QTimer.singleShot(500, self.load_assets_dict)

        # Load data from JSON file

    def setup_Ui(self):
        print('SETUP UI')
        fnt = QFont('Lexend', 10)

        # MAIN WIDGET / LAYOUT
        self.main_widget = QWidget(self.window)
        self.layout_horizontal_main = QHBoxLayout(self.window)
        self.main_widget.setLayout(self.layout_horizontal_main)
        self.splitter = QSplitter(Qt.Horizontal, self.main_widget)
        self.window.setCentralWidget(self.main_widget)
        # Add splitter to main layout
        self.layout_horizontal_main.addWidget(self.splitter)

        # COMMONS TAGS (LEFT)
        width = 175
        self.container_left = QWidget()
        self.container_left.setMinimumWidth(width)
        self.container_left.setMaximumWidth(width+50)

        self.splitter.addWidget(self.container_left)
        self.layout_vertical_container_left = QVBoxLayout(self.container_left)
        self.scrollable_commons_tags = QScrollArea(self.container_left)

        self.layout_vertical_container_left.addWidget(self.scrollable_commons_tags)
        self.scrollable_commons_tags.setWidgetResizable(True)

        self.layout_vertical_01 = QVBoxLayout(self.scrollable_commons_tags)
        # QTreeWidget
        self.tree_widget_commons_tags = QTreeWidget()
        self.tree_widget_commons_tags.setStyleSheet("background-color: rgba(0, 0, 0,30); color: white;")
        self.tree_widget_commons_tags.setHeaderHidden(True)  # Hide the header
        self.tree_widget_commons_tags.setFont(fnt)
        self.layout_vertical_01.addWidget(self.tree_widget_commons_tags)

        # CENTRAL
        self.container_middle = QWidget()
        self.splitter.addWidget(self.container_middle)
        self.layout_vertical_main = QVBoxLayout(self.container_middle)

        #    HORIZONTAL LAYOUT 01
        self.layout_horizontal_01 = QHBoxLayout()
        self.layout_horizontal_01.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        self.layout_vertical_main.addLayout(self.layout_horizontal_01)
        #        TITLE: TODO create png for text instead
        self.label_title_01 = QLabel(self.title)
        self.label_title_01.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        font = QFont('Lexend', 15)
        font.setBold(True)
        self.label_title_01.setFont(font)
        self.label_title_01.setStyleSheet("color: white;")
        self.layout_horizontal_01.addWidget(self.label_title_01)
        spacer= QSpacerItem(50,0)
        self.layout_horizontal_01.addItem(spacer)

        #       SEARCH BAR:
        self.lineEdit_search = QLineEdit()
        self.lineEdit_search.setFixedHeight(25)
        self.lineEdit_search.setMinimumWidth(200)
        self.lineEdit_search.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.lineEdit_search.setFont(fnt)
        self.layout_horizontal_01.addWidget(self.lineEdit_search)
        self.model = QStandardItemModel()
        completer = QCompleter(self.model, self)
        completer.setCompletionMode(QCompleter.InlineCompletion)
        self.lineEdit_search.setCompleter(completer)
        for item in self.completion_list:
            if not self.model.findItems(item):
                self.model.appendRow(QStandardItem(item))
        self.lineEdit_search.editingFinished.connect(self.add_search_tag)
        
        #   HORIZONTAL LAYOUT 02
        self.layout_horizontal_02 = QHBoxLayout()
        self.layout_horizontal_02.setAlignment(Qt.AlignLeft| Qt.AlignTop)
        self.layout_vertical_main.addLayout(self.layout_horizontal_02)
        #        TITLE: TODO create png for text instead
        self.label_title_02 = QLabel("Current Tags:")
        self.label_title_02.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        font = QFont('Lexend', 11)
        font.setBold(True)
        self.label_title_02.setFont(font)
        self.label_title_02.setStyleSheet("color: white;")
        self.layout_horizontal_02.addWidget(self.label_title_02)
        spacer2= QSpacerItem(50,0)
        self.layout_horizontal_02.addItem(spacer2)
        #       HORIZONTAL LAYOUT 03
        self.layout_horizontal_03 = QHBoxLayout()
        self.layout_horizontal_03.setAlignment(Qt.AlignRight | Qt.AlignTop)
        self.layout_horizontal_02.addLayout(self.layout_horizontal_03)


        # VIDEO GALLERY
        self.video_gallery_assets = BDD_VideoGallery.VideoGallery({},3,self)

        self.layout_vertical_main.addWidget(self.video_gallery_assets)
        self.video_gallery_assets.customContextMenuRequested.connect(self.gallery_context_menu)
        self.video_gallery_assets.selection_changed.connect(self.thumbnail_selection_changed)
        self.populate_commons_tags_tree()

        # RIGHT
        self.container_right = QWidget()
        self.splitter.addWidget(self.container_right)
        self.layout_vertical_container_right = QVBoxLayout(self.container_right)
        self.container_right.setMinimumWidth(320)
        self.splitter.setSizes([200, 400,320])

        # blast selection
        self.layout_horizontal_06 = QHBoxLayout()
        self.layout_vertical_container_right.addLayout(self.layout_horizontal_06)
        font = QFont('Lexend', 11)
        font.setBold(True)


        self.label_selected_item = QLabel()
        self.label_selected_item.setFont(font)
        self.label_selected_item.setStyleSheet("color: white;")

        font = QFont('Lexend', 10)
        font.setBold(False)
        self.comboBox_departement = QComboBox()
        self.comboBox_departement.setStyleSheet("color: white;background-color: rgb(30,30,35);")
        self.comboBox_departement.setFont(font)
        self.comboBox_departement.setFixedHeight(25)
        self.comboBox_variation = QComboBox()
        self.comboBox_variation.setStyleSheet("color: white;background-color: rgb(30,30,35);")
        self.comboBox_variation.setFont(font)
        self.comboBox_variation.setFixedHeight(25)
        self.comboBox_version = QComboBox()
        self.comboBox_version.setStyleSheet("color: white;background-color: rgb(30,30,35);")
        self.comboBox_version.setFont(font)
        self.comboBox_version.setFixedHeight(25)

        self.comboBox_departement.currentTextChanged.connect(self.update_combobox_variation)
        self.comboBox_variation.currentTextChanged.connect(self.update_combobox_version)
        self.comboBox_version.currentTextChanged.connect(self.update_current_blast)


        self.layout_horizontal_06.addWidget(self.label_selected_item)
        self.layout_horizontal_06.addWidget(self.comboBox_departement)
        self.layout_horizontal_06.addWidget(self.comboBox_variation)
        self.layout_horizontal_06.addWidget(self.comboBox_version)


        # Video Player
        #first_asset = self.assetsDict[next(iter(self.assetsDict))]["playblast"]
        self.video_player = VideoPlayerWidget("")
        self.layout_vertical_container_right.addWidget(self.video_player)

        # Selection List (if many selected item, hide videoPlayer to show this instead)
        self.scroll_area_selList = QScrollArea()
        self.scroll_area_selList.setFixedHeight(400)
        self.scroll_area_selList.setWidgetResizable(True)
        self.widget_selList = QWidget()
        self.layout_grid_selList = QGridLayout(self.widget_selList)

        self.scroll_area_selList.setWidget(self.widget_selList)
        self.layout_vertical_container_right.addWidget(self.scroll_area_selList)
        self.scroll_area_selList.setVisible(False)

        # Item Tags List
        self.label_item_tags = QLabel("Item tags:")
        self.label_item_tags.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        font = QFont('Lexend', 11)
        font.setBold(True)
        self.label_item_tags.setFont(font)
        self.label_item_tags.setStyleSheet("color: white;")
        self.layout_vertical_container_right.addWidget(self.label_item_tags)

        # add item bar:
        self.layout_horizontal_04 = QHBoxLayout()
        self.layout_vertical_container_right.addLayout(self.layout_horizontal_04)
        self.label_add_item_tags = QLabel("Add tag:")
        self.label_add_item_tags.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        font = QFont('Lexend',8)
        self.label_add_item_tags.setFont(font)
        self.label_add_item_tags.setStyleSheet("color: white;")
        self.layout_horizontal_04.addWidget(self.label_add_item_tags)
        self.lineEdit_addItemTag = QLineEdit()
        self.lineEdit_addItemTag.setFixedHeight(25)
        self.lineEdit_addItemTag.setMinimumWidth(200)
        self.lineEdit_addItemTag.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.lineEdit_addItemTag.setFont(fnt)
        self.lineEdit_addItemTag.setCompleter(completer)
        self.layout_horizontal_04.addWidget(self.lineEdit_addItemTag)
        self.lineEdit_addItemTag.editingFinished.connect(self.add_items_tag)

        self.layout_grid_item_tags = QGridLayout()
        self.layout_vertical_container_right.addLayout(self.layout_grid_item_tags)
        self.item_tag_timer = QTimer(self)
        self.item_tag_timer.setSingleShot(True)  # Only trigger once after the timeout
        self.selection_list = []
        self.item_tag_timer.timeout.connect(self.display_item_tags)

        spacer3 = QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.layout_vertical_container_right.addSpacerItem(spacer3)

        self.layout_horizontal_05 = QHBoxLayout()
        self.layout_vertical_container_right.addLayout(self.layout_horizontal_05)
        self.comboBox_importSettings = QComboBox()
        self.button_import = QPushButton("Import")
        if len(self.import_settings) >0:
            self.comboBox_importSettings.addItems(self.import_settings)
            self.comboBox_importSettings.setStyleSheet("color: white;background-color: rgb(30,30,35);")
            if not self.prism:
                self.button_import.setStyleSheet("color: white;background-color: rgb(30,45,55);")
        else:
            self.comboBox_importSettings.addItem('No prism or maya instances')
            self.comboBox_importSettings.setEnabled(False)
            self.comboBox_importSettings.setStyleSheet("color: grey;background-color: rgb(40,40,45);")
            self.button_import.setEnabled(False)
            self.button_import.setStyleSheet("color: grey;background-color: rgb(40,50,60);")
        font = QFont('Lexend', 10)
        self.comboBox_importSettings.setFont(font)
        font = QFont('Lexend', 12)
        self.button_import.setFont(font)
        self.button_import.setFixedWidth(120)
        self.button_import.clicked.connect(self.import_selected_items)

        self.layout_horizontal_05.addWidget(self.comboBox_importSettings)
        self.layout_horizontal_05.addWidget(self.button_import)

    def thumbnail_selection_changed(self,selection_list):
        self.selection_list = selection_list

        if len(selection_list)==1:
            new_videopath = selection_list[0].video_path
            self.video_player.setVisible(True)
            self.scroll_area_selList.setVisible(False)
            if self.video_player.video_path != new_videopath:
                self.video_player.change_video(new_videopath)

        elif len(selection_list) > 1:
            try:
                for i in reversed(range(self.layout_grid_selList.count())):
                    self.layout_grid_selList.itemAt(i).widget().setParent(None)

                self.video_player.setVisible(False)
                self.scroll_area_selList.setVisible(True)
                # Ajout de labels pour tester
                num_columns = 4  # Fixed number of columns

                new_width = self.scroll_area_selList.width() // num_columns - 10  # Add margin spacing
                new_height = int(new_width * 0.8)
                row = 0
                col = 0
                for item in selection_list:
                    asset = item.asset
                    sel_thumbnail = BDD_VideoGallery.VideoThumbnail(asset,
                                                                    item.video_path,
                                                                    item.thumbnail_path,
                                                                    [new_height,new_width],
                                                                    item.tags,
                                                                    create_scene_by_thread=False)
                    self.layout_grid_selList.addWidget(sel_thumbnail,row,col)
                    QTimer.singleShot(500,sel_thumbnail.set_thumbnail)
                    col += 1
                    if col > num_columns:
                        col = 0
                        row += 1
            except:
                print(traceback.format_exc())
        self.item_tag_timer.start(25)

    def update_comboBox_departement(self):
        if len(self.selection_list) == 1:
            try:
                if len(self.selection_list) == 1:
                    self.label_selected_item.setVisible(True)
                    self.comboBox_departement.setVisible(True)
                    self.comboBox_departement.clear()
                    self.comboBox_variation.setVisible(True)
                    self.comboBox_version.setVisible(True)
                    item = self.selection_list[0]
                    self.label_selected_item.setText(item.asset)
                    assetPath = '\\'.join(item.video_path.split('\\')[:-4])
                    all_departement = [dep.split('\\')[-1] for dep in glob(f'{assetPath}\\Scenefiles\\*')]
                    self.comboBox_departement.addItems(all_departement)
                    if 'rigging' in all_departement:
                        self.comboBox_departement.setCurrentText('rigging')
                    self.update_combobox_variation()

            except:
                print(traceback.format_exc())
        else:
            self.label_selected_item.setVisible(False)
            self.comboBox_departement.setVisible(False)
            self.comboBox_variation.setVisible(False)
            self.comboBox_version.setVisible(False)

    def update_combobox_variation(self):
        try:
            if len(self.selection_list) == 1:
                item = self.selection_list[0]
                assetPath = '\\'.join(item.video_path.split('\\')[:-4])
                self.comboBox_variation.clear()
                all_variation = [var.split('\\')[-1] for var in
                                 glob(f'{assetPath}\\Scenefiles\\{self.comboBox_departement.currentText()}\\*')]
                self.comboBox_variation.addItems(all_variation)
                if 'main' in all_variation:
                    self.comboBox_variation.setCurrentText('main')
                self.update_combobox_version()
        except:
            print(traceback.format_exc())

    def update_combobox_version(self):
        try:
            if len(self.selection_list) == 1:
                item = self.selection_list[0]
                assetPath = '\\'.join(item.video_path.split('\\')[:-4])
                self.comboBox_version.clear()
                all_versions = [ver.split('_')[-1].split('.')[0]
                                for ver in
                                glob(
                                    f'{assetPath}\\Scenefiles\\{self.comboBox_departement.currentText()}\\{self.comboBox_variation.currentText()}\\*')]
                for ver in all_versions:
                    if ver.find('versioninfo') != -1:
                        all_versions.remove(ver)
                self.comboBox_version.addItems(all_versions)
                self.comboBox_version.setCurrentText(all_versions[-1])
                #self.update_current_blast()
        except:
            print(traceback.format_exc())

    def update_current_blast(self):
        if len(self.selection_list) == 1:
            item = self.selection_list[0]
            assetPath = '\\'.join(item.video_path.split('\\')[:-4])
            item_name = item.asset
            departement = self.comboBox_departement.currentText()
            variation = self.comboBox_variation.currentText()
            version =self.comboBox_version.currentText()
            if departement and variation and version:
                new_blast = f"{assetPath}\\Playblasts\\{departement}-{variation}\\{version}\\{item_name}_{departement}_{variation}_{version}.mp4"
                if os.path.exists(new_blast):
                    self.video_player.change_video(new_blast)
                else:
                    print(f'Blast do not exist = {new_blast}')

    def display_item_tags(self):
        self.update_comboBox_departement()
        # Désactiver temporairement les mises à jour du layout
        self.layout_grid_item_tags.parentWidget().setUpdatesEnabled(False)
        # Suppression sécurisée des widgets existants
        for i in reversed(range(self.layout_grid_item_tags.count())):  # Inverser pour éviter les décalages
            item = self.layout_grid_item_tags.takeAt(i)
            if item:
                widget = item.widget()
                if widget:
                    widget.setParent(None)
                    widget.deleteLater()

        self.layout_grid_item_tags.update()
        if len(self.selection_list) == 1:
            try:
                tags = self.selection_list[0].tags
                row = 0
                col = 0
                for tag in tags:
                    button = search_tag_widget(tag, self.main_widget)
                    button.delete_button_signal.connect(self.remove_item_tag)
                    button.setFixedHeight(40)
                    self.layout_grid_item_tags.addWidget(button, row, col)
                    col += 1
                    if col > 3:
                        col = 0
                        row += 1
            except:
                print(traceback.format_exc())

        if len(self.selection_list) > 1:
            try:
                shared_tags = list(set.intersection(*map(set, [item.tags for item in self.selection_list])))
                row = 0
                col = 0
                for tag in shared_tags:
                    button = search_tag_widget(tag, self.main_widget,self.selection_list[0])
                    button.delete_button_signal.connect(self.remove_item_tag)
                    button.setFixedHeight(40)
                    self.layout_grid_item_tags.addWidget(button, row, col)
                    col += 1
                    if col > 3:
                        col = 0
                        row += 1
            except:
                print(traceback.format_exc())

        self.layout_grid_item_tags.parentWidget().setUpdatesEnabled(True)

    def add_items_tag(self):
        try:
            tag = self.lineEdit_addItemTag.text()
            self.lineEdit_addItemTag.clear()
            self.lineEdit_addItemTag.clearFocus()
            if tag != '':
                for item in self.selection_list:
                    item_name = item.asset
                    if item_name in self.assets_database:
                        if not tag in self.assets_database[item_name]["tags"]:
                            self.assets_database[item_name]["tags"].append(tag)
                        if tag not in self.completion_list:
                            self.completion_list.append(tag)
                        for thumnail in self.video_gallery_assets.thumbnails:
                            if thumnail["asset"] == item_name:
                                if not tag in thumnail["tags"]:
                                    thumnail["tags"].append(tag)
                self.update_completion_list()
                self.display_item_tags()
                write_database(self.assets_database)
        except:
            print(traceback.format_exc())

    def remove_item_tag(self,tag_widget):
        for item in self.selection_list:
            tag= tag_widget.tag_name
            item_name = item.asset
            print(f'remove {tag} in {item_name}')
            tag_widget.setParent(None)
            tag_widget.deleteLater()

            if item_name in self.assets_database:
                if tag in self.assets_database[item_name]["tags"]:
                    self.assets_database[item_name]["tags"].remove(tag)
                if tag in item.tags:
                    item.tags.remove(tag)
                for thumnail in self.video_gallery_assets.thumbnails:
                    if thumnail["asset"] == item_name:
                        if tag in thumnail["tags"]:
                            thumnail["tags"].remove(tag)
            write_database(self.assets_database)

    def populate_commons_tags_tree(self):
        # Add main items to the tree
        for main_item_name in self.common_tags.keys():
            title_fnt = QFont("lexend bold",12)
            main_item = QTreeWidgetItem(self.tree_widget_commons_tags)
            main_item.setText(0, main_item_name)
            main_item.setFont(0,title_fnt)
            main_item.setFlags(main_item.flags() & ~Qt.ItemIsSelectable)
            # Add 5 child items with buttons
            for tag in self.common_tags[main_item_name]:
                child_item = QTreeWidgetItem(main_item)
                # Create a button for each child item
                button = commons_tag_button(tag,self)
                child_item.setFlags(main_item.flags() & ~Qt.ItemIsSelectable)
                # Set the button as the child widget
                self.tree_widget_commons_tags.setItemWidget(child_item, 0, button)
                if isinstance(self.common_tags[main_item_name], dict):
                    for sub in self.common_tags[main_item_name][tag]:
                        sub_widget = QTreeWidgetItem(child_item)
                        button = commons_tag_button(sub, self)
                        fnt = QFont('lexend', 10)
                        button.setFont(fnt)
                        button.setStyleSheet("""
                            background-color: rgba(0, 200, 250, 80);
                            border-radius: 7px;
                            color: white;
                            padding: 0px 0px;
                        """)
                        child_item.setFlags(main_item.flags() & ~Qt.ItemIsSelectable)
                        # Set the button as the child widget
                        self.tree_widget_commons_tags.setItemWidget(sub_widget, 0, button)
                        if sub not in self.completion_list:
                            self.completion_list.append(sub)
                if tag not in self.completion_list:
                    self.completion_list.append(tag)
                self.update_completion_list()

        trash_item = QTreeWidgetItem(self.tree_widget_commons_tags)
        # Create a button for each child item
        button = commons_tag_button("_ TRASH _", self)
        button.setStyleSheet("""
                                   background-color: rgba(250, 80, 0, 80);
                                   border-radius: 7px;
                                   color: white;
                                   padding: 0px 0px;
                               """)
        #button.setFixedSize(len(tag) * 8 + 30, 20)
        trash_item.setFlags(trash_item.flags() & ~Qt.ItemIsSelectable)
        # Set the button as the child widget
        self.tree_widget_commons_tags.setItemWidget(trash_item, 0, button)

    def update_completion_list(self):
        for item in self.completion_list:
            if not self.model.findItems(item):
                self.model.appendRow(QStandardItem(item))

    def add_search_tag(self):

        entryItem = self.lineEdit_search.text()
        self.lineEdit_search.clear()
        if entryItem and entryItem not in self.current_tags:
            self.current_tags.append(entryItem)
            itemWiget = search_tag_widget(entryItem, self)
            itemWiget.delete_button_signal.connect(self.remove_search_tag)  # Connect signal
            self.layout_horizontal_03.addWidget(itemWiget)
        self.update_tags()

    def add_commons_tag(self,button):
        tag = button.tag_name
        print(tag)
        if tag not in self.current_tags:
            self.current_tags.append(tag)
            itemWiget = search_tag_widget(tag, self)
            itemWiget.delete_button_signal.connect(self.remove_search_tag)  # Connect signal
            self.layout_horizontal_03.addWidget(itemWiget)
        self.update_tags()

    def remove_search_tag(self,tag_widget):
        print('remove')
        self.current_tags.remove(tag_widget.tag_name)
        self.layout_horizontal_03.removeWidget(tag_widget)
        tag_widget.deleteLater()
        self.update_tags()

    def update_tags(self):
        self.video_gallery_assets.update_gallery(self.current_tags)

    def load_assets_dict(self):
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        assets_dict = {}
        path_to_assets = f"{BDD_Path}\\01_Workflow\Assets"
        all_categories = glob(path_to_assets + '\\*')
        for categorie in all_categories:
            cat = categorie.split('\\')[-1]
            self.completion_list.append(cat.lower())
            path_to_categorie = f"{path_to_assets}\{cat}"
            all_assets = glob(path_to_categorie + '\\*')
            for asset in all_assets:
                asset_name = asset.split('\\')[-1]
                self.completion_list.append(asset_name.lower())
                asset_preview = f'{BDD_Path}\\00_Pipeline\Assetinfo\\{asset_name}_preview.jpg'
                asset_blast = None
                tags = [cat.lower()]
                if asset_name in self.assets_database:
                    if "playblast" in self.assets_database[asset_name]:
                        asset_blast = self.assets_database[asset_name]["playblast"]
                    if "tags" in self.assets_database[asset_name]:
                        tags = self.assets_database[asset_name]["tags"]
                        if cat.lower() not in tags:
                            tags.append(cat.lower())
                if not asset_blast:
                    all_blasts = []
                    for root, dirs, files in os.walk(f'{asset}\\Playblasts'):
                        for file in files:
                            if file.endswith('.mp4'):
                                all_blasts.append(root + '\\' + file)
                    if len(all_blasts) > 0:
                        asset_blast = all_blasts[-1]
                assets_dict[asset_name] = {"preview": asset_preview,
                                           "playblast": asset_blast,
                                           "tags":tags}
                for tag in tags:
                    if not tag in self.completion_list:
                        self.completion_list.append(tag)
                if not asset_name in self.assets_database:
                    self.assets_database[asset_name] = {'metadata': {}}
                self.assets_database[asset_name]["playblast"] = asset_blast
                self.assets_database[asset_name]["preview"] = asset_preview
                self.assets_database[asset_name]["tags"] = tags
                self.video_gallery_assets.addUnicthumbnail({'asset':asset_name,
                                                            "playblast":asset_blast,
                                                            "preview":asset_preview,
                                                            "tags":tags})
        write_database(self.assets_database)
        self.update_completion_list()

        return assets_dict

    def gallery_context_menu(self,pos,thumbnail,selected_items):
        """Open a context menu for a thumbnail."""
        try:
            context_menu = QMenu(self.main_widget)
            # Tags
            tag_action = QAction("Add tags", self)
            context_menu.addAction(tag_action)
            tag_action.triggered.connect(lambda: self.add_tags_window(selected_items))

            # Open File
            open_action = QAction("Open file", self)
            context_menu.addAction(open_action)
            open_action.triggered.connect(lambda: self.open_file(selected_items))
            open_action.setEnabled(False)
            if len(selected_items) == 1:
                open_action.setEnabled(True)

            context_menu.addSeparator()

            # Delete
            delete_action = QAction("Delete file(s)",self)
            context_menu.addAction(delete_action)
            delete_action.triggered.connect(lambda: self.delete_files(selected_items))

            # Show the context menu
            context_menu.exec_(thumbnail.mapToGlobal(pos))
        except:
            print(traceback.format_exc())

    def add_tags_window(self,selected_items):
        addTagsWindow = add_tags_window(selected_items,self.completion_list,self)
        addTagsWindow.exec_()

    def open_scene_file(self, file_path):
        import maya.cmds as cmds
        if cmds.file(q=True, modified=True):
            res = cmds.confirmDialog(
                title='Unsaved Changes',
                message='You have unsaved changes. Do you want to save them?',
                button=['Save', 'Discard', 'Cancel'],
                defaultButton='Save',
                cancelButton='Cancel',
                dismissString='Cancel'
            )
            if res == 'Save':
                current_scene = cmds.file(q=True, sceneName=True)
                if current_scene:
                    cmds.file(save=True)
                else:
                    save_path = cmds.fileDialog2(fileFilter="Maya Binary (*.mb);;Maya ASCII (*.ma)", dialogStyle=2,
                                                 fileMode=0)
                    if save_path:
                        cmds.file(rename=save_path[0])
                        cmds.file(save=True, type='mayaBinary')
                    else:
                        return  # User cancelled the save as dialog
            elif res == 'Cancel':
                return
            elif res == 'Discard':
                try:
                    cmds.file(file_path, open=True, force=True)

                    return
                except RuntimeError as e:
                    QMessageBox.warning(self, "Error", str(e))
                    return

    def open_file(self,selected_items):
        blast = selected_items[0].video_path
        base_path = blast.split('\\Assets\\')[0]
        elements = blast.split('\\Assets\\')[-1].split('\\')
        dep = elements[3].split('-')[0]
        var = elements[3].split('-')[1]
        scene_name = elements[-1].replace('.mp4',"")
        scene_path =f'{base_path}\\Assets\\{elements[0]}\\{elements[1]}\\Scenefiles\\{dep}\\{var}\\'
        scene = [f for f in os.listdir(scene_path)
                    if os.path.isfile(os.path.join(scene_path, f))
                    and f.find(scene_name) != -1][0]
        scene = scene_path + scene
        print(f'Open {scene}')
        try:
            maya_exe = "C:\\Program Files\\Autodesk\\Maya2022\\bin\\maya.exe"
            if self.maya:
                self.open_scene_file(scene)
            elif self.pcore:
                ext = scene.split('.')[-1]
                appPluginName = None
                for plugin in self.pcore.unloadedAppPlugins.values():
                    if ext in plugin.sceneFormats:
                        appPluginName = plugin.pluginName
                print(f'App Plugin Name = {appPluginName}')
                dccEnv = self.pcore.startEnv.copy()
                usrEnv = self.pcore.users.getUserEnvironment(appPluginName=appPluginName)
                for envVar in usrEnv:
                    dccEnv[envVar["key"]] = envVar["value"]
                prjEnv = self.pcore.projects.getProjectEnvironment(appPluginName=appPluginName)
                for envVar in prjEnv:
                    dccEnv[envVar["key"]] = envVar["value"]
                subprocess.Popen([maya_exe, "-file", scene], env=dccEnv)
            else:
                subprocess.Popen([maya_exe, "-file", scene])
                #os.startfile(scene)
        except:
            print(traceback.format_exc())

    def delete_files(self, selected_items):
        print(selected_items)
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("Confirmation")
        msg_box.setText(f"Êtes-vous sûr de vouloir supprimer {len(selected_items)} assets de la BDD?")

        delete_button = msg_box.addButton("Delete", QMessageBox.AcceptRole)
        cancel_button = msg_box.addButton("Cancel", QMessageBox.RejectRole)

        msg_box.exec_()  # Affiche la boîte de dialogue

        if msg_box.clickedButton() == delete_button:
            for item in selected_items:
                item_name = item.asset
                if item_name in self.assets_database:
                    tag = "_ TRASH _"
                    if not tag in self.assets_database[item_name]["tags"]:
                        self.assets_database[item_name]["tags"].append(tag)
                    if tag not in self.completion_list:
                        self.completion_list.append(tag)
                    for thumnail in self.video_gallery_assets.thumbnails:
                        if thumnail["asset"] == item_name:
                            if not tag in thumnail["tags"]:
                                thumnail["tags"].append(tag)
            self.update_completion_list()
            write_database(self.assets_database)
            self.video_gallery_assets.update_gallery(self.current_tags)

            '''
            for widget in selected_items:
                asset = widget.asset
                print(f"Suppression de {asset}")

                blast = widget.video_path
                path = blast.split(f'\\{asset}\\')[0]
                path_to_asset = f'{path}\\{asset}'
                if os.path.exists(path_to_asset):
                    print(f"Remove folder: {path_to_asset}")
                    old_path = f'{path}\\_ ARCHIVED _\\{asset}'
                    shutil.move(path_to_asset, old_path)
                try:
                    self.video_gallery_assets.thumbnails.remove(widget)
                    self.video_gallery_assets.grid_layout.removeWidget(widget)
                    widget.setParent(None)
                    self.assetsDict.pop(asset)
                    if asset in self.assets_database:
                        self.assets_database.pop(asset)
                        write_database(self.assets_database)
                    #self.video_gallery_assets.update_gallery(self.current_tags)
                except:
                    print(traceback.format_exc())
            '''

            print("Suppression confirmée")
            # Ajouter ici le code de suppression
        else:
            print("Suppression annulée")

    def import_selected_items(self):
        print(f'Import of {[item.asset for item in self.selection_list]}')
        option = self.comboBox_importSettings.currentText()
        print(f'import settigns: {option}')
        maya_accepted_extension = ['ma', 'mb', 'obj', 'fbx', 'abc']
        for item in self.selection_list:
            try:
                asset_path_BDD = '\\'.join(item.video_path.split('\\')[:-4])
                if option.find('Project')!= -1:
                    if self.prism:
                        project_path = self.pcore.projectPath
                        asset_path_Project = f'{project_path}01_Workflow\\Assets\\PlaceHolder\\{item.asset}'
                        print(f'Copy from {asset_path_BDD} to {asset_path_Project}')
                        if not os.path.exists(asset_path_Project):
                            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
                            shutil.copytree(asset_path_BDD,asset_path_Project)
                            QApplication.restoreOverrideCursor()
                        else:
                            print(f'Asset {item.asset} Already in project')
                    else:
                        print('Error!!! No prism instance')
                if option.find('Maya') != -1:
                    if len(self.selection_list) == 1:
                        department = self.comboBox_departement.currentText()
                        variation = self.comboBox_variation.currentText()
                        version = self.comboBox_version.currentText()
                    else:
                        playblast = item.video_path
                        department = playblast.split('\\')[-3].split('-')[0]
                        variation = playblast.split('\\')[-3].split('-')[1]
                        version = playblast.split('\\')[-2]

                    if option.find('Project')!=-1:
                        if self.prism:
                            project_path = self.pcore.projectPath
                            asset_path_Project = f'{project_path}01_Workflow\\Assets\\PlaceHolder\\{item.asset}'
                            asset_path = f'{asset_path_Project}\\Export\\{department}\\{department}-{variation}\\{version}\\*'
                            all_files = glob(asset_path)
                            final_path = None
                            for f in all_files:
                                if f.split('.')[-1] in maya_accepted_extension:
                                    final_path = f
                                    break
                            print(f'Reference asset:  {item.asset}_{department}_{variation}_{version} in maya scene')
                            sm = self.pcore.getStateManager()
                            sm.importFile(final_path)
                        else:
                            print('Error!!! No prism instance')

                    else:
                        import maya.cmds as cmds
                        asset_path = f'{asset_path_BDD}\\Export\\{department}\\{department}-{variation}\\{version}\\*'
                        all_files = glob(asset_path)
                        final_path = None
                        for f in all_files:
                            if f.split('.')[-1] in maya_accepted_extension:
                                final_path = f
                                break
                        print(f'Hard import of {final_path}')
                        cmds.file(final_path, i=1,force=1)

            except:
                print(f'\n!!!!!!! Error trying to import {item.asset} !!!!!!!!!!!\n')
                print(traceback.format_exc())


if __name__ == "__main__":

    app = QApplication(sys.argv)
    w= BDD_MainWindow()
    w.show_window()
    sys.exit(app.exec_())