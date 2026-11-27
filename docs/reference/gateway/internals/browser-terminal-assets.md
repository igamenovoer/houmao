# Browser Terminal Assets

The gateway serves pinned xterm.js browser modules from the Houmao Python package. The terminal imports only gateway-local resources. Python builds and installations include the modules, styles, upstream licenses, and asset checksums.

| Package | Version | Vendored Members |
| --- | --- | --- |
| `@xterm/xterm` | `6.0.0` | `package/lib/xterm.mjs`, `package/css/xterm.css`, `package/LICENSE` |
| `@xterm/addon-fit` | `0.11.0` | `package/lib/addon-fit.mjs`, `package/LICENSE` |

To update the pins, download the selected npm release tarballs into an ignored scratch directory. Query each version's registry metadata and compare its `dist.integrity` to the tarball's SHA-512 digest. The currently packaged releases are [xterm.js 6.0.0](https://registry.npmjs.org/@xterm/xterm/-/xterm-6.0.0.tgz) and [FitAddon 0.11.0](https://registry.npmjs.org/@xterm/addon-fit/-/addon-fit-0.11.0.tgz).

Copy the listed members byte-for-byte to `src/houmao/gateway/_terminal_assets/`, storing each license as `<package>.LICENSE`. Update the version table above and regenerate `vendor.sha256` from that directory.

```sh
cd src/houmao/gateway/_terminal_assets
sha256sum xterm.mjs xterm.css xterm.LICENSE addon-fit.mjs addon-fit.LICENSE > vendor.sha256
sha256sum -c vendor.sha256
```

Use `shasum -a 256` in place of `sha256sum` on macOS. Run `pixi run build-dist` and verify the wheel and source distribution contain all five files and `vendor.sha256`. Exercise the terminal from an installed build with browser requests restricted to the gateway origin.
