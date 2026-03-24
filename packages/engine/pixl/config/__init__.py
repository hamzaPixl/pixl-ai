"""Configuration module for Pixl CLI.

Provides provider configuration, model resolution, and workflow configuration.

Config search order:
1. ~/.pixl/projects/[PROJECT_NAME]/config.*  # Global project-specific
2. ~/.pixl/config.*                          # Global default
3. project_path/.pixl/config.*               # Local override
4. Bundled defaults                          # Fallback
"""

from pixl.config.providers import (
    DEFAULT_MODELS,
    DEFAULT_PROVIDERS,
    ConcurrencyConfig,
    ProviderConfig,
    ProvidersConfig,
    ProvidersConfigLoadResult,
    load_model_pricing,
    load_providers_config,
    load_providers_config_with_source,
)
from pixl.config.resolver import (
    ConfigSource,
    ensure_global_dir,
    ensure_project_global_dir,
    find_all_config_sources,
    find_config_file,
    get_global_pixl_dir,
    get_project_global_dir,
    get_project_name,
)
from pixl.config.workflow_loader import (
    ModelIssueSeverity,
    ModelValidationIssue,
    ModelValidationResult,
    WorkflowLoader,
    WorkflowLoadError,
    list_yaml_workflows,
    load_workflow_from_yaml,
)

__all__ = [
    # Provider config
    "ConcurrencyConfig",
    "DEFAULT_MODELS",
    "DEFAULT_PROVIDERS",
    "ProviderConfig",
    "ProvidersConfig",
    "ProvidersConfigLoadResult",
    "load_model_pricing",
    "load_providers_config",
    "load_providers_config_with_source",
    # Config resolver
    "ConfigSource",
    "ensure_global_dir",
    "ensure_project_global_dir",
    "find_all_config_sources",
    "find_config_file",
    "get_global_pixl_dir",
    "get_project_global_dir",
    "get_project_name",
    # Workflow loader
    "ModelIssueSeverity",
    "ModelValidationIssue",
    "ModelValidationResult",
    "WorkflowLoadError",
    "WorkflowLoader",
    "list_yaml_workflows",
    "load_workflow_from_yaml",
]
