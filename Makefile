# Ultima Underworld Data Extraction Toolkit - Makefile

# Default paths
DATA_PATH = Input/UW1/DATA
OUTPUT_PATH = Output
WEB_PORT = 8080

.PHONY: all extract xlsx clean help web maps images start open

# Default target - regenerate with xlsx
all: xlsx

# Extract to JSON only
extract:
	python main.py $(DATA_PATH) $(OUTPUT_PATH)

# Extract to JSON and XLSX
xlsx:
	python main.py $(DATA_PATH) $(OUTPUT_PATH) --xlsx

# Generate web map images from game data
maps:
	python web/generate_maps.py

# Extract object images for web viewer
images:
	python web/generate_images.py

# Prepare web viewer (extract data + generate maps + extract images)
web: extract maps images
	@echo "Web viewer data ready. Run 'make start' to start the server."

# Start the web server
start:
	@echo "Checking for processes using port $(WEB_PORT)..."
	@python web/kill_port.py $(WEB_PORT) || true
	@echo "Starting web server at http://localhost:$(WEB_PORT)"
	@echo "Press Ctrl+C to stop the server"
	python web/server.py $(WEB_PORT) 127.0.0.1

# Open the web viewer in default browser (cross-platform)
open:
	python -m webbrowser http://localhost:$(WEB_PORT)

# Clean output files
clean:
	rm -rf $(OUTPUT_PATH)/*.json $(OUTPUT_PATH)/*.xlsx
	rm -rf web/data/*.json web/maps/*.png web/images/objects/*.png

# Show help
help:
	@echo "Available targets:"
	@echo "  make          - Extract all data and generate XLSX (same as 'make xlsx')"
	@echo "  make extract  - Extract all data to JSON only"
	@echo "  make xlsx     - Extract all data and generate XLSX"
	@echo "  make maps     - Generate map images for web viewer"
	@echo "  make images   - Extract object images for web viewer"
	@echo "  make web      - Prepare web viewer (extract + maps + images)"
	@echo "  make start    - Start the web server on port $(WEB_PORT)"
	@echo "  make open     - Open the web viewer in your browser"
	@echo "  make clean    - Remove all generated files"
	@echo "  make help     - Show this help message"

