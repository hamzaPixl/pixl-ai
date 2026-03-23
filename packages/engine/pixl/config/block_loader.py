"""Block loader for reusable workflow stage blocks.

This module loads block definitions from YAML files with cascading precedence:
1. Project blocks: {project}/.pixl/workflows/blocks/ (highest priority)
2. Global blocks: ~/.pixl/workflows/blocks/ (user's personal library)
3. Bundled blocks: built-in to Pixl installation (lowest priority)

Blocks are reusable groups of stages that can be referenced in workflows
using the `use:` syntax.

Example workflow using blocks:
```yaml
stages:
  - use: init           # Expands init block's stages
  - id: custom-stage    # Regular inline stage
    name: Custom Analysis
    prompt: "..."
  - use: tdd-loop       # Expands tdd-loop stages
  - use: finalize       # Expands finalize stages
```
"""

from pathlib import Path

from pixl.models.workflow_config import BlockConfig
from pixl.paths import get_global_pixl_dir, get_workflows_dir


class BlockLoadError(Exception):
    """Error loading a block from YAML."""

    def __init__(self, message: str, path: str | Path | None = None):
        self.message = message
        self.path = str(path) if path else None
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        if self.path:
            return f"Error loading block from {self.path}: {self.message}"
        return self.message


class BlockLoader:
    """Loads reusable stage blocks with cascading resolution.

    Block lookup follows a cascading precedence:
    1. Project: {project}/.pixl/workflows/blocks/ (project-specific, highest priority)
    2. Global: ~/.pixl/workflows/blocks/ (user's personal library)
    3. Bundled: built-in blocks (Pixl defaults, lowest priority)

    Usage:
        loader = BlockLoader(project_path)
        block = loader.load_block("init")  # Returns BlockConfig
        blocks = loader.list_blocks()       # Returns list of block metadata
    """

    # Bundled blocks shipped with the pixl package
    BUNDLED_BLOCKS_DIR = Path(__file__).parent.parent / "assets" / "workflows" / "blocks"

    # Global user blocks directory
    GLOBAL_BLOCKS_DIR = get_global_pixl_dir() / "workflows" / "blocks"

    def __init__(
        self,
        project_path: Path,
        global_blocks_dir: Path | None = None,
        bundled_blocks_dir: Path | None = None,
    ):
        """Initialize the block loader.

        Args:
            project_path: Path to the project root
            global_blocks_dir: Optional override for global blocks dir
                              (primarily for testing)
            bundled_blocks_dir: Optional override for bundled blocks dir
                               (primarily for testing)
        """
        self.project_path = project_path
        self.blocks_dir = get_workflows_dir(project_path) / "blocks"
        self.global_blocks_dir = global_blocks_dir or (
            get_global_pixl_dir() / "workflows" / "blocks"
        )
        self.bundled_blocks_dir = bundled_blocks_dir or self.BUNDLED_BLOCKS_DIR

        # Cache loaded blocks to avoid repeated file I/O
        self._cache: dict[str, BlockConfig] = {}

    def load_block(self, block_id: str) -> BlockConfig:
        """Load a block by ID with cascading resolution.

        Lookup order (first found wins):
        1. Project blocks (.pixl/workflows/blocks/{id}.yaml)
        2. Global blocks (~/.pixl/workflows/blocks/{id}.yaml)
        3. Bundled blocks (built-in to Pixl)

        Args:
            block_id: Block identifier (e.g., "init", "tdd-loop")

        Returns:
            BlockConfig instance

        Raises:
            BlockLoadError: If block not found or invalid
        """
        # Check cache first
        if block_id in self._cache:
            return self._cache[block_id]

        search_dirs = [
            (self.blocks_dir, "project"),
            (self.global_blocks_dir, "global"),
            (self.bundled_blocks_dir, "bundled"),
        ]

        for blocks_dir, _source in search_dirs:
            block_file = blocks_dir / f"{block_id}.yaml"
            if block_file.exists():
                try:
                    block = BlockConfig.from_yaml_file(block_file)
                    self._cache[block_id] = block
                    return block
                except (FileNotFoundError, ValueError) as e:
                    raise BlockLoadError(str(e), block_file) from e

        # Not found anywhere
        searched_locations = [
            str(self.blocks_dir),
            str(self.global_blocks_dir),
            str(self.bundled_blocks_dir),
        ]
        raise BlockLoadError(
            f"Block '{block_id}' not found (searched: {', '.join(searched_locations)})"
        )

    def list_blocks(self) -> list[dict[str, str]]:
        """List all available blocks with source info.

        Returns blocks from all sources, with higher-precedence sources
        overriding lower ones (project > global > bundled).

        Returns:
            List of block metadata dictionaries with keys:
            - id: Block identifier
            - name: Human-readable name
            - description: Block description
            - version: Block version
            - path: Path to YAML file
            - source: Where the block comes from (project, global, bundled)
        """
        blocks: dict[str, dict[str, str]] = {}

        search_dirs = [
            (self.bundled_blocks_dir, "bundled"),
            (self.global_blocks_dir, "global"),
            (self.blocks_dir, "project"),
        ]

        for blocks_dir, source in search_dirs:
            if not blocks_dir.exists():
                continue
            for yaml_file in blocks_dir.glob("*.yaml"):
                try:
                    block = BlockConfig.from_yaml_file(yaml_file)
                    blocks[block.id] = {
                        "id": block.id,
                        "name": block.name,
                        "description": block.description,
                        "version": block.version,
                        "path": str(yaml_file),
                        "source": source,
                    }
                except Exception:
                    # Skip invalid blocks
                    continue

        return list(blocks.values())

    def clear_cache(self) -> None:
        """Clear the block cache.

        Call this if block files have been modified and you need to reload.
        """
        self._cache.clear()

    def is_block_available(self, block_id: str) -> bool:
        """Check if a block is available without loading it.

        Args:
            block_id: Block identifier

        Returns:
            True if block exists in any location
        """
        search_dirs = [
            self.blocks_dir,
            self.global_blocks_dir,
            self.bundled_blocks_dir,
        ]

        for blocks_dir in search_dirs:
            block_file = blocks_dir / f"{block_id}.yaml"
            if block_file.exists():
                return True

        return False


__all__ = [
    "BlockLoadError",
    "BlockLoader",
]
