PREFIX ?= /usr/local
BUILDDIR = builddir

.PHONY: all setup compile install uninstall run clean register help

all: setup compile

help:
	@echo "Sift Makefile commands:"
	@echo "  make setup      - Initialize meson build directory"
	@echo "  make compile    - Compile the project"
	@echo "  make install    - Install the application (requires sudo if prefix is /usr/local)"
	@echo "  make uninstall  - Remove the application from the system"
	@echo "  make run        - Run the application directly from source"
	@echo "  make register   - Register the app locally (dev mode, no install)"
	@echo "  make clean      - Remove the build directory"

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
