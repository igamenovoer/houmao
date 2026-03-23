## 1. Helper Scaffold

- [x] 1.1 Create the repo-owned helper subtree at `dockers/dev-helpers/filestash/` with the compose entry point, startup/shutdown helpers, verification helper, README, and repo-owned seed configuration assets.
- [x] 1.2 Add or update ignore rules so `dockers/dev-helpers/filestash/.data/` remains untracked runtime state.

## 2. Runtime And Access Contract

- [x] 2.1 Configure the helper to use the upstream Filestash image in a pull-free normal startup path, bind only to `127.0.0.1` on a non-privileged host port, mount the repository read-only at `/repo`, and mount writable helper state at `/app/data/state`.
- [x] 2.2 Implement the startup flow that prepares writable `.data/` state and synchronizes the repo-owned Filestash seed config into runtime state before the service starts.
- [x] 2.3 Preseed the Filestash access flow so the helper uses the documented development password `admin`, lands the operator in the mounted repository root, and shows hidden files without requiring manual `/repo` entry or first-run browser setup.

## 3. Verification And Documentation

- [x] 3.1 Add a repo-owned verification path that confirms the helper starts from repository context and responds on the documented loopback endpoint.
- [x] 3.2 Document the upstream image prerequisite, the local start/stop/access/reset workflow, the default development access convention, and the development-only scope of the helper.

## 4. Final Validation

- [x] 4.1 Run the documented helper startup and verification flow with the required image already present locally and confirm the implemented defaults match the docs.
- [x] 4.2 Confirm that removing `dockers/dev-helpers/filestash/.data/` after shutdown produces the documented clean-reset behavior on the next startup.
