# Ultima Underworld Data Extraction Toolkit - Makefile

# Default paths
DATA_PATH = Input/UW1/DATA
OUTPUT_PATH = Output
WEB_PORT = 8080

.PHONY: all extract clean help web maps images serve

# Default target - regenerate all
all: web

# Extract to JSON only
extract:
	python main.py $(DATA_PATH) $(OUTPUT_PATH) --xlsx

# Generate web map images from game data
maps:
	python web/generate_maps.py

# Extract object images for web viewer
images:
	python web/generate_images.py

# Prepare web viewer (extract data + generate maps + extract images)
web: extract maps images
	@echo "Web viewer ready. Run 'make serve' to start a local server."

# Clean generated output files (preserves static assets like web/images/static/)
clean:
	@echo "Cleaning generated files..."
	@python -c "import shutil, glob, os; files = [p for pattern in ['$(OUTPUT_PATH)/*.json', '$(OUTPUT_PATH)/*.xlsx', 'web/data/*.json', 'web/maps/*.png'] for p in glob.glob(pattern)]; [os.remove(p) for p in files]; print(f'  Removed {len(files)} files') if files else None"
	@python -c "import shutil, os; path='web/images/extracted'; existed=os.path.exists(path); shutil.rmtree(path, ignore_errors=True); print('  Removed web/images/extracted/') if existed else None"
	@echo "Done."

# Start a simple static HTTP server for local testing
serve:
	@echo "Press Ctrl+C to stop the server"
	cd web && python server.py $(WEB_PORT)

# Show help
help:
	@echo "Available targets:"
	@echo "  make          - Prepare web viewer (same as 'make web')"
	@echo "  make extract  - Extract game data to JSON and XLSX"
	@echo "  make maps     - Generate map images for web viewer"
	@echo "  make images   - Extract object/NPC images for web viewer"
	@echo "  make web      - Prepare web viewer (extract + maps + images)"
	@echo "  make serve    - Start HTTP server on port $(WEB_PORT) for local testing"
	@echo "  make clean    - Remove all generated files"
	@echo "  make help     - Show this help message"

