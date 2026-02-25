PREFIX ?= /usr/local
BUILDDIR = builddir

.PHONY: all setup compile install uninstall run clean register help flatpak-build flatpak-run lint validate

all: setup compile

help:
	@echo "Sift Makefile commands:"
	@echo "  make setup          - Initialize meson build directory"
	@echo "  make compile        - Compile the project"
	@echo "  make install        - Install the application (requires sudo if prefix is /usr/local)"
	@echo "  make uninstall      - Remove the application from the system"
	@echo "  make run            - Run the application directly from source"
	@echo "  make register       - Register the app locally (dev mode, no install)"
	@echo "  make clean          - Remove the build directory"
	@echo "  make flatpak-build  - Build and install Flatpak locally"
	@echo "  make flatpak-run    - Run the installed Flatpak"
	@echo "  make lint           - Lint the Flatpak manifest"
	@echo "  make validate       - Validate desktop and metainfo files"

setup:
	@if [ ! -d "$(BUILDDIR)" ]; then \
		meson setup $(BUILDDIR) --prefix=$(PREFIX); \
	else \
		echo "Build directory already exists. Use 'make clean' first if you want to re-setup."; \
	fi

compile:
	meson compile -C $(BUILDDIR)

install:
	meson install -C $(BUILDDIR)

uninstall:
	@if [ -d "$(BUILDDIR)" ]; then \
		ninja -C $(BUILDDIR) uninstall; \
	else \
		echo "Build directory not found. Please run 'make setup' first."; \
	fi

run:
	python3 sift/main.py

register:
	python3 install_local.py

clean:
	rm -rf $(BUILDDIR)
	rm -rf .flatpak-builder build-flatpak

flatpak-build:
	flatpak-builder --force-clean --user --install build-flatpak io.github.frephs.Sift.json

flatpak-run:
	flatpak run io.github.frephs.Sift

lint:
	@if command -v flatpak-builder-lint >/dev/null; then \
		flatpak-builder-lint manifest io.github.frephs.Sift.json; \
	else \
		echo "flatpak-builder-lint not found. Install it with: flatpak install flathub org.flatpak.Builder"; \
		flatpak run --command=flatpak-builder-lint org.flatpak.Builder manifest io.github.frephs.Sift.json; \
	fi

validate:
	@echo "Validating desktop file..."
	@cp data/io.github.frephs.Sift.desktop.in data/io.github.frephs.Sift.desktop
	@desktop-file-validate data/io.github.frephs.Sift.desktop
	@rm data/io.github.frephs.Sift.desktop
	@echo "Validating metainfo file..."
	@appstreamcli validate data/io.github.frephs.Sift.metainfo.xml.in
