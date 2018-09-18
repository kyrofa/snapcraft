#!/bin/sh -e

# Restore patched files
PYTHON_PACKAGE_PATH="$SNAPCRAFT_PART_INSTALL/usr/lib/python3.5/"
[ -f "patched/ctypes/__init__.py.orig" ] && mv "patched/ctypes/__init__.py.orig" "$PYTHON_PACKAGE_PATH/ctypes/__init__.py"

SITE_PACKAGES_PATH="$SNAPCRAFT_PART_INSTALL/lib/python3.5/site-packages"
[ -f "patched/yaml/emitter.py.orig" ] && mv "patched/yaml/emitter.py.orig" "$SITE_PACKAGES_PATH/yaml/emitter.py"
[ -f "patched/yaml/reader.py.orig" ] && mv "patched/yaml/reader.py.orig" "$SITE_PACKAGES_PATH/yaml/reader.py"

# Apply patches
echo "Patching ctypes..."
patch -s -b "$PYTHON_PACKAGE_PATH/ctypes/__init__.py" patches/ctypes_init.diff
echo "Patching PyYAML..."
patch -s -b -d "$SITE_PACKAGES_PATH/" -p1 < patches/pyyaml-support-high-codepoints.diff

# Save patches to allow rebuilding
mkdir -p patched/ctypes
[ -f "$PYTHON_PACKAGE_PATH/ctypes/__init__.py.orig" ] && mv "$PYTHON_PACKAGE_PATH/ctypes/__init__.py.orig" patched/ctypes

mkdir -p patched/yaml
[ -f "$SITE_PACKAGES_PATH/yaml/emitter.py.orig" ] && mv "$SITE_PACKAGES_PATH/yaml/emitter.py.orig" patched/yaml
[ -f "$SITE_PACKAGES_PATH/yaml/reader.py.orig" ] && mv "$SITE_PACKAGES_PATH/yaml/reader.py.orig" patched/yaml

# Now that everything is built, let's disable user site-packages
# as stated in PEP-0370
echo "Compiling pyc files..."
sed -i $SNAPCRAFT_PART_INSTALL/usr/lib/python3.5/site.py -e 's/^ENABLE_USER_SITE = None$/ENABLE_USER_SITE = False/'
# This is the last step, let's now compile all our pyc files.
$SNAPCRAFT_PART_INSTALL/usr/bin/python3 -m compileall -q .
