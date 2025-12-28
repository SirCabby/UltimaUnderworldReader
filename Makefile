# Ultima Underworld Data Extraction Toolkit - Makefile

# Default paths
DATA_PATH = Input/UW1/DATA
OUTPUT_PATH = Output

.PHONY: all extract xlsx clean help

# Default target - regenerate with xlsx
all: xlsx

# Extract to JSON only
extract:
	python main.py $(DATA_PATH) $(OUTPUT_PATH)

# Extract to JSON and XLSX
xlsx:
	python main.py $(DATA_PATH) $(OUTPUT_PATH) --xlsx

# Clean output files
clean:
	rm -rf $(OUTPUT_PATH)/*.json $(OUTPUT_PATH)/*.xlsx

# Show help
help:
	@echo "Available targets:"
	@echo "  make          - Extract all data and generate XLSX (same as 'make xlsx')"
	@echo "  make extract  - Extract all data to JSON only"
	@echo "  make xlsx     - Extract all data and generate XLSX"
	@echo "  make clean    - Remove generated files"
	@echo "  make help     - Show this help message"

