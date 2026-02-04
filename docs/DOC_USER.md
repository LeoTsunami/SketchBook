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
When you select an image in the gallery, its tags are automatically displayed at the bottom of the thumbnail:
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
  - **Move**: Drag a user tag and drop it onto a category (e.g. "Human") to place it under that category, or onto another tag to make that tag the parent (the user tag then appears under it in the grid).
  - **Add tag**: Click "Add tag" above the grid. Enter a name and optionally pick an icon from the list. The new tag appears under "Miscellaneous:" until you move it by drag-and-drop. You can then apply it to images like any other tag.

### Tags Library Notes
Categories stay collapsed by default and only expand when you add the category tag to your filters.
Categories are displayed as buttons in the first column, with sub-tag buttons revealed horizontally to the right when active.

## Drawing Sessions

You can run timed drawing sessions using the images currently shown (filtered by your tag selection).

### Starting a Session
1. Apply tag filters so the gallery shows the images you want to use.
2. Click **Session Settings** (bottom of the left panel).
3. Choose **Session Type**:
   - **Course**: Phased session (WarmUp → Gesture → Anatomy → Shading) with duration 10–60 minutes (step 10).
   - **Constant interval**: Same duration per image (30 s, 1/3/5/10/20 min).
4. Choose **Window Mode**: FullScreen or Window always on top.
5. Click **Start Session**.

The main window is hidden and the session window opens. The image list is built from your filtered images, in random order.

### Session Window
- **Countdown**: Shown in the top-left for the current image; it decreases second by second and turns red as time approaches zero.
- **Controls** (bottom bar): Previous, Next, and timer controls (Play/Pause, Reset). Press **Space** to show or hide the control bar.
- **Keyboard**: **Space** (toggle controls), **Left/Right** (previous/next), **S** (start/stop timer), **P** (pause), **Escape** (end session and return to main window).

When you close the session window (or finish the last image), the main window is shown again.