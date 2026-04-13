## Importing Images

SketchBook supports two convenient ways to import your reference images:

### Using the File Menu
1. Click on `File > Import Images...` in the menu bar
2. Select one or more images in the file dialog
3. Click "Open" to import the selected images

### Using Drag & Drop
Simply drag image files from your file explorer and drop them into the SketchBook window.

### Supported Formats
- JPEG/JPG
- PNG

### Image Processing
When you import images, SketchBook automatically:
- Resizes large images to fit within the maximum width and height set in **Settings** (File > Settings > Image Import Compression). Defaults: 1920 px width, 1080 px height. Aspect ratio is preserved.
- Optimizes the file size for better performance
- Converts images to a consistent format

### Tips
- You can select multiple files at once in the import dialog
- Dragging a folder containing images is not supported, but you can select multiple images from the folder and drag them
- If some images fail to import, check that they are in a supported format

## Themes

You can switch theme in **File > Settings** (Theme) or **View > Theme**.

Available themes:
- Dark
- Light
- Neon Night
- Sunset Glass
- Midnight Ocean

## Tag library (floating panel)

The tag library is a **floating panel** over the **left edge** of the image gallery (the gallery does not resize when you open it). A compact **Tags filters** vertical strip sits on the left edge of the gallery. **Hover** opens the full library; moving the pointer **away from the panel** closes it. While the panel is open, the **Tags filters** strip stays hidden so it does not sit on top of the library. The panel and strip are **shorter in height** than the viewport so they stay **below the floating logo** (top-left).

**Top bar** (full width, two lines above the gallery):

- **Line 1** (chrome bar): The **SketchBook** logo is **floating** on top of the window (top-left); it does not set the height of the bar. **File**, **View**, **Tools**, and **Help** start to the right of the logo area (import, settings, themes, dev tools, about). Window controls (minimize, maximize, close) are on the far right.
- **Line 2** (tab bar): **Life Drawing**, **WhiteBoard**, and **Market** tab buttons on the left. The active tab has a colored underline matching the current theme. **Shuffle** (when using Session Course Random sort), **Sort** order, **Columns** (slider + count), and **Display** mode are on the right of this line and are only visible when the **Life Drawing** tab is active.

Clicking a tab switches the content area. **WhiteBoard** and **Market** are placeholders for now.

**Below** the tab bar, the **content** fills the remaining space. On the **Life Drawing** tab the **image gallery** uses the full width. **Start session** stays **centered at the bottom** of the gallery viewport and remains **above** other floating controls in that area (tag panel, tag popover).

**Image count and selection size** (number of filtered images and total size of the current selection) appear on the **right side of the status bar**, next to the usual status messages (same band as quick / dev log feedback).

## Image Metadata
SketchBook automatically tracks metadata for your imported images, including:

- Original filename
- Import date
- Image dimensions
- File size
- Image format
- Tags (user-defined)
- Notes (user-defined)

### Adding Tags and Notes
You can add tags and notes to your images to help organize and find them later:

1. Select an image in the gallery
2. Use the metadata panel to:
   - Add or remove tags
   - Write notes about the image

### Viewing Tags on Selected Images
When you select an image in the gallery, its tags are automatically displayed at the bottom of the thumbnail. The small floating tag panel **stays aligned with that thumbnail** when you **scroll** the gallery.
- Each tag appears as a small chip with its icon (if available)
- Click the × button on any tag chip to remove that tag from all selected images (removal runs in the background; a progress indicator may appear when many images are updated)
- Tags are displayed in a grid layout that wraps automatically
- You can drag and drop tags from the tag library directly onto images to add them
- The tags display updates automatically when you modify tags

### Filtering Images
You can filter your image collection using the tag buttons:

1. Click one or more category buttons (e.g., "Human", "Animal")
2. Optionally click sub-tags under each category (e.g., "Male", "Portrait")
3. **Camera-Angle** and similar label tags (e.g. "Wide-Angle", "Close-Up") apply as an extra constraint: only images that match the selected category *and* the selected angle are shown (e.g. Human + Wide-Angle = humans in wide angle only).
4. The gallery updates automatically

Categories act as a global OR (Human OR Animal). Sub-tags act as AND within their category (Human + Male + Portrait).

### Tips for Using Tags
- Use descriptive tags that help categorize your images (e.g., "landscape", "portrait", "reference")
- Be consistent with your tag naming
- You can add multiple tags to a single image
- Tags are case-sensitive 

### Tags Library: Managing User Tags
- **Default tags** (from the built-in list) cannot be renamed or removed; they can receive new user tags as children (see below).
- **User tags** (tags you added or that exist only on your images) can be edited:
  - **Rename**: Right-click a user tag → "Rename...". The tag is renamed on all images that have it.
  - **Move**: Drag a user tag and drop it onto a category (e.g. "Human") to place it under that category, or onto another tag to make that tag the parent (the user tag then appears under it in the grid). While dragging, moving the cursor near the top or bottom of the tag library area automatically scrolls the list so you can reach tags above or below.
  - **Parent to tag...**: Right-click a user tag → "Parent to tag...". The selected tag(s) are grayed out; a bar appears at the top: "Select parent tag: (none)" with **OK** and **Cancel**. Click another tag or a category to set it as the parent (the label updates). Click **OK** to move the grayed tags under that parent (same result as drag-and-drop); **Cancel** exits without changing anything. To parent **several tags at once**, hold **Ctrl** and click the user tags you want to move so they are selected, then right-click one of them and choose "Parent to tag...".
  - **Add tag**: Click "Add tag" above the grid. Enter a name and optionally pick an icon from the list. The new tag appears under "Miscellaneous:" until you move it by drag-and-drop. You can then apply it to images like any other tag.

### Tags Library Notes
Categories stay collapsed by default and only expand when you add the category tag to your filters.
Categories are displayed as buttons in the first column, with sub-tag buttons revealed horizontally to the right when active.
Entries with children now show an expand/collapse arrow (`▶` when collapsed, `▼` when expanded), including both categories and nested sub-categories. The tag buttons also use depth-based colors so parent/child levels are easier to read.
Simple click is dedicated to filtering and expand/collapse. Multi-selection in the tag library is done with **Ctrl+drag** or **Shift+drag** (drag rectangle); simple click no longer creates tag-library selection.
When a sub-category is expanded, its children are displayed directly on the next line under that parent. Parent order stays stable in the category list (no jump/reorder when expanding).

## Drawing Sessions

You can run timed drawing sessions using the images currently shown (filtered by your tag selection).

### Starting a Session
1. Apply tag filters so the gallery shows the images you want to use.
2. Click **Session Settings** (bottom of the left panel).
3. Choose **Session Type**:
   - **Course**: Phased session (Warm-up → Gesture → Short pose → Anatomy → Shading) with duration 10–60 minutes (step 10).
   - **Constant interval**: Same duration per image (30 s, 1/3/5/10/20 min).
4. Choose **Window Mode**: FullScreen or Window always on top.
5. Click **Start Session**.

The main window is hidden and the session window opens. The image list is built from your filtered images, in random order.

### Start from a specific image (right-click in grid)

- Select **exactly one image** in the grid.
- Right-click it and choose **"Start session from this image"**.
- The Session Settings window opens as usual.
- When the session starts, SketchBook uses that image as the first step and keeps only the images after it in the current grid order; images before it are ignored for that session.

### Session Window
- **Screen awake**: While the session window is open, the screen and computer stay awake (no sleep or screen saver). Normal power behavior is restored when you close the session.
- **Countdown**: Shown in the top-left for the current image; it decreases second by second and turns red as time approaches zero.
- **Controls** (bottom bar): **Previous**, **Next**, and **Play/Pause** for the timer. The bar can auto-hide after a moment; move the mouse or press a key to show it again. **Next** and **Previous** move one step at a time: the first screen (Get ready), each phase title, and each image are steps you can move through and come back to like images.
- **Pause and edit**: When the session is **paused** (Play is shown), an **Éditer** button appears. It opens the **same image viewer** as when you **double-click** an image in the grid (zoom, rotate, crop, etc.). While the viewer is open, the session bar hides **Previous**, **Next**, **Play/Pause**, and **Éditer**; close the viewer window to return to the paused session with the slide reloaded from disk if you saved changes.
- **Keyboard**: **Space** (toggle pause/play when focus is on the image area), **Left/Right** (previous/next), **Escape** (fullscreen → window, or close session in window mode).

When you close the session window (or finish the last image), the main window is shown again.

### Session Course Random sort mode

- In the image grid, the **Sort** combo box includes a mode called **"Session Course Random"**.
- When this mode is active, the grid shows your filtered images in the same deterministic random order that will be used during a Course session (or Constant interval session when using random order).
- By default, SketchBook now starts with **"Session Course Random"** selected the first time you open the app, so you immediately see a course-style random order for your gallery.
- When you change the sort mode, SketchBook remembers your last choice and restores it the next time you launch the application.

### Image display mode

The **Display** combo box (next to the Columns slider in the top bar) lets you choose how images are fitted inside each grid cell:

- **Crop All** (default) — fills the entire cell, cropping excess on both axes (classic "cover" mode).
- **Fit All** — the entire image is visible, no crop. Bars may appear on the shorter axis.
- **Fit Height** — fills the cell height; width may be clipped if the image is wider than the cell.
- **Fit Width** — fills the cell width; height may be clipped if the image is taller than the cell.

The choice is saved automatically and restored on relaunch.

### Thumbnail quality and loading in the image grid

- When you scroll through the grid, a fast low-quality preview appears for each new thumbnail almost instantly. A moment later it is silently replaced by a crisp, high-quality version. This two-phase approach keeps the grid responsive even with thousands of images.
- While you **drag a window edge** to resize the main window, previews may look slightly softer or blocky for a moment so the UI stays responsive; a moment after you **release** the mouse, thumbnails are refitted with full smooth scaling again.
- Internally, SketchBook loads a 2x-resolution version of each image for thumbnails and lets Qt downscale it, which produces a sharp result, especially after window resizes or when using many columns.
- When you change tag filters repeatedly, the grid discards the previous thumbnail widgets completely so old images cannot linger as non-interactive scraps in the margins.

## Single Image Viewer

When you double-click an image in the grid, SketchBook opens a dedicated viewer window.

### Initial display and zoom

- The viewer window opens maximized by default.
- The area around the image (when the aspect ratio does not fill the view) uses the **same themed window background** as the rest of the app, not a flat gray panel.
- The image is automatically **fit in view** the first time you open the viewer in a session, so it uses the full available space instead of appearing very small.
- You can use the mouse wheel to zoom in and out (the cursor position is used as the zoom anchor).

### Navigating between images

- The viewer reads the current ordered list of images from the main grid.
- Use the **Previous** and **Next** buttons at the bottom of the window to move to the neighbouring images in the same order as they appear in the grid.

### Rotating an image

- Use **Rotate ⟲** to rotate the image 90° counterclockwise.
- Use **Rotate ⟳** to rotate the image 90° clockwise.
- Rotation is applied directly to the underlying file and saved; the image and its metadata (size) are updated in the library.

### Cropping and saving

- To crop:
  1. Click the **Crop** button at the bottom of the window. A rule-of-thirds grid appears over the image and the crop area is initially the full image.
  2. Drag the **four corner handles** (white circles) to adjust the crop rectangle. The grid updates to show thirds inside the selected area.
  3. Click **Valider** to apply the crop and save the image to disk, or **Annuler** to cancel and leave the image unchanged.
- The cropped region replaces the original file (non-reversible inside SketchBook), and the viewer reloads the result.
- This allows you to quickly reframe reference photos without leaving the application.