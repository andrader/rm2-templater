# reMarkable 2 Template Manager

A command-line tool for managing custom templates on your reMarkable 2 tablet. Easily add, remove, and organize templates with automatic image conversion and SSH-based deployment.

## Features

- **SSH Key Setup**: Automatically generate and install SSH keys for passwordless access
- **Template Management**: Add, list, remove, and backup templates
- **Image Conversion**: Automatically converts images to reMarkable's required format (1872x1404, 226 DPI grayscale PNG)
- **Category Organization**: Organize templates into custom categories
- **Safe Operations**: Automatic backups before any changes
- **Batch Processing**: Add multiple templates from directories

## Installation

### Recommended: Install with uv

#### Install globally (best for repeated use):
```bash
uv tool install git+https://github.com/andrader/rm2-templater.git
```
- Installs the CLI globally for easy reuse: just run `rm2` or `rm2-templater`.

#### Run instantly (no install, best for one-off use):
```bash
uvx --from git+https://github.com/andrader/rm2-templater.git --help
```
- Runs the CLI directly from the repo, no global install or environment changes.

To uninstall:
```bash
uv tool uninstall rm2-templater
```

Choose `uv tool install` for persistent, system-wide access. Use `uvx` for quick, disposable runs without installing anything globally.

---

### Alternative: Install with pip

```bash
pip install rm2-templater
```

Or install from source:

```bash
git clone https://github.com/andrader/rm2-templater.git
cd rm2-templater
pip install -e .
```

## Quick Start

### 1. Find Your reMarkable's Connection Info

On your reMarkable 2:

1. Go to **Settings** (bottom left)
2. Select **Help** (bottom of menu)
3. Tap **Copyrights and licenses**
4. Scroll to **GPLv3 Compliance** section
5. Note the IP address, username (usually `root`), and password

### 2. Set Up SSH Access

```bash
rm2 setup-ssh
# Enter your reMarkable's root password when prompted
```

This command:

- Generates an SSH key pair if one doesn't exist
- Installs your public key on the reMarkable
- Enables passwordless access for future operations

### 3. Add Your First Template

```bash
# Add a single template
rm2 add my-template.png

# Add multiple templates with a custom category
rm2 add template1.jpg template2.png --category "Work"

# Add all images from a directory
rm2 add ./my-templates/
```

## Commands

### `setup-ssh`

Install your SSH public key on the reMarkable for passwordless access.

```bash
rm2 setup-ssh
```

### `add`

Convert and upload template images to your reMarkable.

```bash
rm2 add [OPTIONS] PATHS...

Options:
  -c, --category TEXT    Additional category besides 'Custom'
  --force               Overwrite existing template entries
```

**Examples:**

```bash
# Basic usage
rm2 add notebook-template.png

# Add with custom category
rm2 add planner.jpg --category "Productivity"

# Add multiple files
rm2 add template1.png template2.jpg template3.webp

# Add all images from a directory
rm2 add ./templates-folder/

# Force overwrite existing template
rm2 add existing-template.png --force
```

### `list`

Display all current templates and their categories.

```bash
rm2 list
```

### `remove`

Remove templates by name, filename, or category.

```bash
rm2 remove [OPTIONS]

Options:
  --name TEXT           Remove by display name
  --filename TEXT       Remove by filename (e.g. Custom/my_template)
  --category TEXT       Remove ALL entries in a category
  --delete-files        Also delete remote PNG files
  -y                    Skip confirmation prompt
```

**Examples:**

```bash
# Remove by name
rm2 remove --name "My Template"

# Remove by filename
rm2 remove --filename "Custom/my_template"

# Remove all templates in a category
rm2 remove --category "Work"

# Remove and delete files without confirmation
rm2 remove --name "Old Template" --delete-files -y
```

### `backup`

Create a timestamped backup of your templates.json file.

```bash
rm2 backup
```

## Configuration

The tool uses these default settings, which can be customized via environment variables:

```python
REMARKABLE_IP = "10.11.99.1"              # reMarkable IP address
REMARKABLE_USER = "root"                   # SSH username
REMARKABLE_TEMPLATES_DIR = "/usr/share/remarkable/templates"
REMARKABLE_DEFAULT_CATEGORY = "Custom"     # Default category for new templates
REMARKABLE_SSH_KEY = "~/.ssh/id_rsa"      # SSH private key path
```

## Image Requirements

The tool automatically converts your images to meet reMarkable's specifications:

- **Resolution**: 1872×1404 pixels
- **DPI**: 226
- **Format**: Grayscale PNG
- **Supported Input**: PNG, JPG, JPEG, WebP

## File Structure

```
rm2-templater/
├── converted/          # Converted PNG files (temporary)
├── backups/           # Automatic backups of templates.json
├── templates.json     # Local copy of reMarkable's template registry
└── src/rm2_templater/
    ├── cli.py         # Main CLI interface
    ├── settings.py    # Configuration
    ├── Template.py    # Data models
    ├── convert_image.py   # Image processing
    └── ensure_ssh_key.py  # SSH key management
```

## How It Works

1. **SSH Connection**: Uses SSH to securely connect to your reMarkable
2. **Image Processing**: Converts images to reMarkable's required format using Pillow
3. **File Upload**: Transfers converted PNGs to `/usr/share/remarkable/templates/Custom/`
4. **Registry Update**: Updates `templates.json` with new template metadata
5. **UI Restart**: Restarts the reMarkable UI (`xochitl`) to load new templates

## Safety Features

- **Automatic Backups**: Creates timestamped backups before any changes
- **Idempotent Operations**: Safe to run multiple times
- **Confirmation Prompts**: Asks before destructive operations
- **Error Handling**: Graceful handling of network and file system errors

## Troubleshooting

### Connection Issues

**Problem**: `Authentication failed` error

```bash
# Solution: Re-run SSH setup
rm2 setup-ssh
```

**Problem**: `Connection timeout`

- Ensure your reMarkable is awake and connected to the same network
- Verify the IP address in Settings > Help > GPLv3 Compliance
- Check that SSH is enabled (it should be by default)

### Template Issues

**Problem**: Templates don't appear after adding

```bash
# The UI restart should happen automatically, but you can manually restart:
ssh root@<remarkable-ip> "systemctl restart xochitl"
```

**Problem**: Image quality issues

- Ensure your source images are high resolution
- The tool converts to grayscale automatically
- Templates work best with simple line art and text

## Inspiration

This tool was inspired by the excellent tutorials from [Simply Kyra](https://www.simplykyra.com/):

- [Learn How to Access Your reMarkable Through the Command Line](https://www.simplykyra.com/blog/learn-how-to-access-your-remarkable-through-the-command-line/)
- [How to Make Template Files for Your reMarkable](https://www.simplykyra.com/blog/how-to-make-template-files-for-your-remarkable/)

## Requirements

- Python 3.13+
- reMarkable 2 tablet
- Network connection between your computer and reMarkable

## Dependencies

- `typer` - CLI framework
- `paramiko` - SSH client
- `pillow` - Image processing
- `pydantic` - Data validation
- `loguru` - Logging

## License

This project is open source. Please check the license file for details.

## Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

---

**Note**: This tool modifies system files on your reMarkable. While it includes safety measures like automatic backups, use at your own risk. Always ensure your reMarkable is backed up before making changes.
