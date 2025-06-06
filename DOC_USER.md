## Importing Images

### Duplicate Detection
The application automatically detects and prevents duplicate images from being imported. An image is considered a duplicate if:
- It's the exact same file that was previously imported
- It has the same name, size, and dimensions as an existing image

When a duplicate is detected:
- The import is skipped
- A message is shown in the status bar
- If developer mode is enabled, detailed information about the match is shown in the log

### Import Methods
You can import images in several ways:
1. **File Menu**
   - Use "Import Images..." to select individual files
   - Use "Import Folder..." to import an entire folder

2. **Drag and Drop**
   - Drag files directly into the application window
   - Drag folders to import all images inside

### Supported Formats
- JPEG (.jpg, .jpeg)
- PNG (.png)

### Image Processing
- Large images are automatically resized to a maximum width of 1920 pixels
- Images are converted to JPEG format for storage efficiency
- Original image metadata is preserved 