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
- Resizes large images to a maximum width of 1920 pixels (preserving aspect ratio)
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
- Click the × button on any tag chip to remove that tag from all selected images
- Tags are displayed in a grid layout that wraps automatically
- You can drag and drop tags from the tag library directly onto images to add them
- The tags display updates automatically when you modify tags

### Filtering Images
You can filter your image collection using the tag buttons:

1. Click one or more category buttons (e.g., "Human", "Animal")
2. Optionally click sub-tags under each category (e.g., "Male", "Portrait")
3. The gallery updates automatically

Categories act as a global OR (Human OR Animal). Sub-tags act as AND within their category (Human + Male + Portrait).

### Tips for Using Tags
- Use descriptive tags that help categorize your images (e.g., "landscape", "portrait", "reference")
- Be consistent with your tag naming
- You can add multiple tags to a single image
- Tags are case-sensitive 

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