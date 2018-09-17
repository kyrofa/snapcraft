#!/usr/bin/make -f

SRC_DIR ?= .

DEST_LAUNCHER = glib-extension-launch

build: $(DEST_LAUNCHER)

clean:
	rm -f $(DEST_LAUNCHER)

$(DEST_LAUNCHER):
	@echo "#!/bin/bash" > $(DEST_LAUNCHER)
	@cat $(SRC_DIR)/init >> $(DEST_LAUNCHER)
	@cat $(SRC_DIR)/desktop-exports >> $(DEST_LAUNCHER)
	@cat $(SRC_DIR)/mark-and-exec >> $(DEST_LAUNCHER)
		
install: $(DEST_LAUNCHER)
	install -D -m755 $(DEST_LAUNCHER) "$(DESTDIR)"/snap/command-chain/$(DEST_LAUNCHER)
