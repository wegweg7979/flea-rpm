# flea — Fedora packaging

Fedora RPM packaging for [flea](https://github.com/thisisgm/flea): the
keyboard-first, Omarchy-native file manager. Upstream ships an Arch-only recipe
(the Omarchy Package Repository PKGBUILD plus its Makefile); this repository
carries only the spec that turns it into an RPM.

## Fedora package (COPR)

```sh
sudo dnf copr enable wegweg7979/flea
sudo dnf install flea
```

Then, in a session, decide what Flea should own — installing only registers it:

```sh
flea --default      # folder handler, "Show in folder", Super+Shift+F, file chooser
flea --picker      # file chooser only
flea --default off # undo
```

## What it builds

| Path | What it is |
|---|---|
| `flea`, `flea-gui` | the backend/launcher/TUI and the GPUI window |
| `/usr/lib/flea/*` | the portal backend, the FileManager1 service, gio-auth, udisks, mpris helpers |
| `/usr/share/flea/ui/` | the retained Quickshell QML entry |
| `/usr/share/flea/shelf/` | the Omarchy bar shelf plugin |
| `/usr/share/flea/i18n/` | the 50 language catalogs |

## Notes the port needed

- **Rust 1.100.0 comes from Fedora** — exactly what upstream's
  `rust-toolchain.toml` pins, so nothing is vendored or shipped for the toolchain.
- **`enable_net: true` is required on the COPR project**: cargo fetches crates.io
  *and* the pinned `gpui-omarchy` git fork (15 `gpui-pre-*` crates).
- **`Requires: omarchy`** resolves on Fedora through `omedora`, which Provides it;
  omedora already requires `quickshell`, which the QML entry and the shelf need.
- **`bsdtar` is a hard dependency** — Fedora's `libarchive` ships only the library,
  and Flea keeps tar formats on bsdtar deliberately.
- **The alpm removal hook is dropped** (no pacman on Fedora). The advice it printed
  is above: `flea --default off` and `flea --picker off` before removing the package,
  because that state lives in each user's home.
- **Settings → About** reports that no package owns Flea on Fedora: upstream queries
  `pacman` for provenance and version. That behaviour is left honest rather than
  faked; everything else in the app is package-manager independent.

## Building

`rpm/flea.spec` is the only file that matters; `bin/spec-sources` re-pins the
`Source0` sha256 after a version bump.

Verify a change without touching the host:

```sh
podman run --rm -v "$PWD":/work:z registry.fedoraproject.org/fedora:45 bash -c '
  dnf5 -y install rpm-build rpmdevtools desktop-file-utils cargo rust git gcc make \
    pkgconf-pkg-config fontconfig-devel freetype-devel libxkbcommon-devel wayland-devel libxcb-devel
  rpmdev-setuptree
  cp /work/rpm/flea.spec /root/rpmbuild/SPECS/
  curl -sSfL -o /root/rpmbuild/SOURCES/flea-v0.4.3.tar.gz \
    https://github.com/thisisgm/flea/releases/download/v0.4.3/flea-v0.4.3.tar.gz
  rpmbuild -bb /root/rpmbuild/SPECS/flea.spec'
```
