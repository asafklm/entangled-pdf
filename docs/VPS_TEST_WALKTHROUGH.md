# VPS Test Walkthrough

Detailed walkthrough for installing and testing EntangledPdf on a clean VPS.

---

## Phase 1: SSH Key Setup (On Your Local Machine)

**Create a new SSH key:**
```bash
ssh-keygen -t ed25519 -C "entangledpdf-vps-test" -f ~/.ssh/entangledpdf_vps
```

**Add to GitHub as Deploy Key:**
1. Copy the public key: `cat ~/.ssh/entangledpdf_vps.pub`
2. Go to https://github.com/asafklm/entangled-pdf/settings/keys
3. Add deploy key (allow write access if needed)

---

## Phase 2: Create VPS (Hetzner Cloud Console)

1. Go to https://console.hetzner.cloud
2. Create new server:
   - Name: `entangledpdf-test`
   - Image: Ubuntu 24.04
   - Type: CPX11 (or cheapest)
   - SSH Keys: Add the public key you created

---

## Phase 3: Connect to Server

**Fix host key if needed:**
```bash
ssh-keygen -R <server-ip>
```

**Connect:**
```bash
ssh -i ~/.ssh/entangledpdf_vps root@<server-ip>
```

---

## Phase 4: Install System Dependencies (as root)

```bash
apt update && apt install -y python3 python3-venv python3-pip nodejs npm git pipx

# Install synctex (required for forward/backward sync)
apt install texlive-extra-utils
```

---

## Phase 5: Create User and Clone Repo

```bash
# Create non-root user
adduser tester
# Enter password, press Enter through prompts

# Switch to user and create ssh folder
su - tester
cd /home/tester
mkdir ~/.ssh
```

**Copy SSH key to server** (from your local machine):
```bash
scp -i ~/.ssh/entangledpdf_vps ~/.ssh/entangledpdf_vps tester@<server-ip>:/home/tester/.ssh/
```

**On server (as tester), set permissions:**
```bash
chmod 600 /home/tester/.ssh/entangledpdf_vps
```

**Clone using SSH with explicit key:**
```bash
GIT_SSH_COMMAND="ssh -i /home/tester/.ssh/entangledpdf_vps" git clone git@github.com:asafklm/entangled-pdf.git
cd entangled-pdf
```

---

## Phase 6: Install EntangledPdf (as tester)

See [README.md - Option 1: Install from GitHub with pipx (Recommended)](README.md#option-1-install-from-github-with-pipx-recommended)

Summary:
```bash
cd entangled-pdf

# Install with pipx
pipx install .

# Build frontend (REQUIRED!)
npm install && npm run build
```

---

## Phase 7: Generate SSL Certificates

See [README.md - Section 2: SSL Certificates (Required)](README.md#2-ssl-certificates-required)

Summary:
```bash
entangle-pdf certs generate
```

---

## Phase 8: Set Up API Key

See [README.md - Section 1: API Key (Required)](README.md#1-api-key-required)

Use any simple password for testing:
```bash
export ENTANGLEDPDF_API_KEY="test-key-123"
echo 'export ENTANGLEDPDF_API_KEY="test-key-123"' >> ~/.bashrc
source ~/.bashrc
```

---

## Phase 9: Start Server with Mock Inverse Search

See [README.md - Starting the Server](README.md#starting-the-server)

To test inverse search without installing vim/neovim, use a mock command:
```bash
entangle-pdf start --inverse-search-command "echo %{file}:%{line}"
```

---

## Phase 10: Test Forward Search

Open a **new terminal** on the server (as tester):

```bash
export ENTANGLEDPDF_API_KEY="test-key-123"

#end-user installation Load PDF with forward search
python3 -c "
import sys
sys.path.insert(0, '.')
from entangledpdf.sync import load_pdf, forward_search
load_pdf('examples/example.pdf', 'http://localhost:8431')
forward_search('examples/example.pdf', 1, 1, 'examples/example.tex', 'http://localhost:8431')
"
```

Or use the CLI (if `pipx install .` worked):
```bash
entangle-pdf sync examples/example.pdf 90:1:example.tex
```

---

## Phase 11: Test Inverse Search

1. In browser: Open `https://<server-ip>:8431/view`
2. Accept certificate warning
3. Enter token from server output
4. Shift+Click on the PDF
5. Check server terminal - should see output like:
   ```
   /home/tester/entangled-pdf/examples/example.tex:42
   ```

---

## Phase 12: Cleanup

1. **Delete VPS**: Hetzner Console → Delete server
2. **Remove deploy key**: GitHub → Settings → Deploy keys → Delete
3. **Remove SSH key**: `rm ~/.ssh/entangledpdf_vps*`

---

## Quick Reference: Commands by README Section

| Step | README Section | Commands |
|------|----------------|----------|
| Install pipx | System requirement | `apt install pipx` (as root) |
| Install | [Option 1](README.md#option-1-install-from-github-with-pipx-recommended) | `pipx install .` |
| Frontend | [Option 1](README.md#option-1-install-from-github-with-pipx-recommended) | `npm install && npm run build` |
| API key | [Section 1](README.md#1-api-key-required) | `export ENTANGLEDPDF_API_KEY=...` |
| SSL certs | [Section 2](README.md#2-ssl-certificates-required) | `entangle-pdf certs generate` |
| Start server | [Starting the Server](README.md#starting-the-server) | `entangle-pdf start --inverse-search-command "echo %{file}:%{line}"` |
| Test sync | [Manual Commands](README.md#manual-commands) | `entangle-pdf sync examples/example.pdf 1:1:example.tex` |

---

## Key Differences from Previous Test

1. **Use pipx** for installation (not `pip install -e .`)
2. **Username: tester** (not asaf)
3. **Mock inverse search** using `--inverse-search-command "echo %{file}:%{line}"` to test without installing vim/neovim
4. **Better SSH key handling** with `GIT_SSH_COMMAND` environment variable
