# flea.spec — Flea, the Omarchy-first file manager, packaged for Fedora.
#
# Upstream (github.com/thisisgm/flea, MIT) ships Arch only: an Omarchy Package
# Repository recipe (PKGBUILD + Makefile) and nothing Fedora-shaped. This spec is
# the Fedora port. It builds upstream's own invocation unchanged,
# `cargo build --locked --release --workspace --bins`, and installs through
# upstream's Makefile minus the one Arch-only artefact it ships (the libalpm
# removal hook — Fedora has no pacman; its per-user undo lines live in
# docs/install.md and in this package's README).
#
# Measured on Fedora 45 (phase-0 container, 2026-11-21):
#   * rustc/cargo 1.100.0 come from Fedora's own repos — exactly what
#     rust-toolchain.toml pins, so no rustup tarball is needed (unlike
#     hyprglaze's Zig);
#   * no bindgen, cmake, openssl or sqlite anywhere in the build: the only -sys
#     crates that matter are freetype-sys, yeslogic-fontconfig-sys, wayland-sys
#     and xcb;
#   * the final flea-gui link is what needs the -devel set — it links
#     gdk-pixbuf, glib/gobject, xcb, freetype, fontconfig and xkbcommon by
#     soname (`-l:libgdk_pixbuf-2.0.so.0`, `-lxkbcommon-x11`), so
#     gdk-pixbuf2-devel and libxkbcommon-x11-devel are build requirements and
#     the rest are not optional either;
#   * cargo needs network for crates.io AND for the pinned gpui fork
#     (github.com/thisisgm/gpui-omarchy @ 9b2f11b9 — 15 gpui-pre-* crates), so the
#     COPR project MUST have enable_net: true;
#   * `Requires: omarchy` is satisfied by omedora, which Provides
#     `omarchy = 0.3.0~beta.1…` on Fedora, and omedora already requires
#     quickshell, so the QML-entry dependency needs no line of its own;
#   * `bsdtar` is its OWN Fedora package (Fedora's libarchive ships only the
#     library), and flea keeps tar formats on bsdtar on purpose — "7z x on a
#     .tar.gz writes the inner .tar, not the files" — so it is a hard Requires;
#   * flea asks `pacman` who installed it and which version it is
#     (src/update.rs, crates/flea-gui/src/window/settings/provenance.rs), which
#     feeds Settings > About. On Fedora that probe fails and About says so; the
#     port keeps that honest instead of faking a package manager;
#   * the upstream test suite is deliberately NOT run here: it needs unprivileged
#     namespaces, tmpfs, 40 GiB free, a live Hyprland and network. %check
#     validates the desktop entry only, as icloud-for-omarchy does.
#
# Rust release builds carry no debug info, so there is none to extract and an
# empty debuginfo subpackage would fail (same choice as airgraph.spec,
# huru-calendar.spec and icloud-for-omarchy.spec).

%global debug_package %{nil}

Name:           flea
Version:        0.4.3
Release:        1%{?dist}
Summary:        Fast, keyboard-first file manager for the Omarchy desktop

License:        MIT
URL:            https://github.com/thisisgm/flea
# The release asset; it unpacks to one flea-<version>/ directory.
Source0:        %{url}/releases/download/v%{version}/flea-v%{version}.tar.gz

# Built for the arch the hurunagus images target.
ExclusiveArch:  x86_64

BuildRequires:  cargo
BuildRequires:  rust
# cargo fetches crates.io and the pinned gpui fork over git.
BuildRequires:  git
BuildRequires:  gcc
BuildRequires:  make
BuildRequires:  pkgconf-pkg-config
BuildRequires:  fontconfig-devel
BuildRequires:  freetype-devel
BuildRequires:  gdk-pixbuf2-devel
BuildRequires:  libxkbcommon-devel
BuildRequires:  libxkbcommon-x11-devel
BuildRequires:  wayland-devel
BuildRequires:  libxcb-devel
BuildRequires:  desktop-file-utils

# omedora Provides `omarchy` on Fedora (and already requires quickshell, which
# the retained QML entry and the shelf bar plugin need).
Requires:       omarchy
# The renderer: GPUI draws with Vulkan and falls back to OpenGL, both loaded at
# runtime, so the soname generator cannot see them.
Requires:       vulkan-loader
Requires:       libglvnd-egl
Requires:       libwayland-client
Requires:       libwayland-egl
# Preview decoders loaded at runtime: photos, PDFs and the jailed media player.
Requires:       libheif
Requires:       poppler-glib
Requires:       mpv-libs
# Helpers the shipped code shells out to.
Requires:       bsdtar
Requires:       bat
Requires:       bubblewrap
Requires:       expect
Requires:       glib2
Requires:       gvfs
Requires:       gvfs-afc
Requires:       gvfs-gphoto2
Requires:       gvfs-mtp
Requires:       gvfs-nfs
Requires:       gvfs-smb
Requires:       hicolor-icon-theme
Requires:       jq
Requires:       python3
Requires:       python3-gobject
Requires:       qt6-qtdeclarative
Requires:       qt6-qtwebengine
Requires:       quickjs-ng
Requires:       ripgrep
Requires:       shared-mime-info
Requires:       udisks2
Requires:       usbmuxd
Requires:       util-linux
Requires:       wl-clipboard
Requires:       xdg-terminal-exec
Requires:       xdg-utils

Recommends:     7zip
Recommends:     ImageMagick
Recommends:     evince-thumbnailer
Recommends:     ffmpeg
Recommends:     ffmpegthumbnailer
Recommends:     rclone
Recommends:     tailscale
Recommends:     zoxide
# No Fedora package for upstream's `owly` (AirDrop) or `dropbox-cli`, so those
# optional upstream features simply report as unavailable here.

%description
Flea is a file manager built for Omarchy: list, columns, grid and two-pane views
with tabs, Quick Look previews, undo on every write, seven colour tags, ranked
search, network places (SMB, SFTP, FTPS, WebDAV, NFS), phones and cameras,
encrypted drives, and ISO/IMG writing with byte verification.

It is keyboard-first with Finder-style chords, follows the desktop theme and
window transparency, and ships a drop shelf for the Omarchy bar.

Installing only registers it: making Flea the default file manager
(`flea --default`), the file chooser (`flea --picker`) and the app on Super+Shift+F
is a per-user choice, and both commands undo themselves with `off`.

%prep
%autosetup -n flea-%{version}

%build
# Upstream's own invocation from the README; --locked honours Cargo.lock.
#
# The ONE deliberate divergence from upstream's own build: the release profile
# in Cargo.toml is `lto = true, codegen-units = 1`, and that fat-LTO link is
# effectively single-threaded and enormous — measured on Fedora 45, the crate
# graph compiles in ~31 minutes and the final flea-gui link alone takes ~19 more
# (it also peaked past a 12 GiB memory cgroup cap and was OOM-killed there).
# COPR's builders cannot finish that inside the project's build ceiling: the
# first submission sat in `%build` for 2h46m with no further output and timed out.
# Thin LTO with 16 codegen units builds the same workspace in 10m49s, for
# binaries ~15-20 % larger (flea 14.0 vs 12.3 MB, flea-gui 51.6 vs 42.0 MB).
# It is the same trade upstream itself makes for its own test harness in
# PKGBUILD's check(), which sets exactly these two variables and keeps fat LTO
# only for the shipped binary.
export CARGO_PROFILE_RELEASE_LTO=thin
export CARGO_PROFILE_RELEASE_CODEGEN_UNITS=16
cargo build --locked --release --workspace --bins

%check
# The desktop entry, validated in the source tree (%check runs before %install).
desktop-file-validate packaging/com.thisisgm.flea.desktop

%install
# Upstream's own installer. VERSION is what it stamps into the shelf plugin's
# manifest.json (it greps the file back afterwards and fails).
make DESTDIR=%{buildroot} VERSION=%{version}-%{release} install

# Arch-only artefact: a libalpm (pacman) hook that prints the per-user undo
# commands on removal. Fedora has no pacman, so the whole /usr/share/libalpm
# tree this creates goes away; the same advice is in this package's README.
rm -rf %{buildroot}%{_datadir}/libalpm

# %license owns these paths from the source tree.
rm -rf %{buildroot}%{_licensedir}/flea

%files
%{_bindir}/flea
%{_bindir}/flea-gui
# The helpers keep upstream's /usr/lib/flea path: the packaged D-Bus service
# files name it absolutely, and /usr/lib is the lib64 symlink on this arch.
%{_prefix}/lib/flea/flea-gio-auth
%{_prefix}/lib/flea/flea-udisks
%{_prefix}/lib/flea/flea-portal
%{_prefix}/lib/flea/flea-filemanager1
%{_prefix}/lib/flea/flea-mpris
# The window, the retained QML entry and the translations, as data beside the
# binary (paths.rs looks for /usr/share/flea/ui/boot/shell.qml).
%{_datadir}/flea/ui/
%{_datadir}/flea/shelf/
%{_datadir}/flea/i18n/
%{_datadir}/applications/com.thisisgm.flea.desktop
%{_datadir}/icons/hicolor/scalable/apps/com.thisisgm.flea.svg
%{_datadir}/xdg-desktop-portal/portals/flea.portal
%{_datadir}/dbus-1/services/org.freedesktop.impl.portal.desktop.flea.service
%{_datadir}/dbus-1/services/com.thisisgm.flea.FileManager1.service
%license LICENSE THIRD-PARTY-LICENSES.txt
%doc README.md CHANGELOG.md

%changelog
* Sat Nov 21 2026 Dan <dan@localhost> - 0.4.3-1
- Initial Fedora packaging: the file manager, its D-Bus services, the file
  chooser portal backend, the QML entry and the Omarchy bar shelf plugin.
