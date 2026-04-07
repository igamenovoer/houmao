## 1. Root Help Surface

- [x] 1.1 Update the top-level `houmao-mgr` Click group so `houmao-mgr --help` and bare `houmao-mgr` output include a short pointer to `https://igamenovoer.github.io/houmao/` for more detailed documentation.
- [x] 1.2 Keep the existing root command list and option help intact while adding the docs-discovery text in a stable location in the rendered help output.

## 2. Verification And Docs Alignment

- [x] 2.1 Add or update CLI help tests to verify both `houmao-mgr --help` and bare `houmao-mgr` expose the detailed docs link.
- [x] 2.2 Update any repo-owned CLI reference text that describes the root `houmao-mgr` help surface so it matches the new docs-link behavior.
