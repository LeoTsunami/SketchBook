## Image Import System

### Duplicate Detection
The system uses a two-step approach to detect duplicate images:

1. **Exact Path Matching**
   - Checks if the original path of the image matches any existing image
   - Provides immediate detection for reimporting the same file

2. **Metadata Comparison**
   - Compares file size, resolution, and filename
   - Helps detect duplicates even if files are renamed or moved
   - Stored in `ImageMetadata` class with fields:
     ```python
     id: str                  # Unique identifier
     path: str               # Path in storage
     original_filename: str  # Original name
     width: int             # Image width
     height: int           # Image height
     file_size: int        # File size in bytes
     format: str           # Image format
     original_path: str    # Original file path
     tags: Set[str]       # Image tags
     ```

### Import Process
1. Image is checked for duplicates
2. If unique, image is processed (resized if needed, converted to JPEG)
3. Metadata is stored in the database
4. Image is copied to storage with a unique filename

### Logging
Detailed logging during import process:
- Start of duplicate check
- Source image details
- Match details if duplicate found
- Import status and results 