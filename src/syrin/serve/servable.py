"""Servable base class — shared serve() logic for HTTP and CLI protocols.

Agent, Pipeline, and DynamicPipeline inherit from Servable to get unified
serve() behavior that respects protocol (HTTP or CLI).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Union, cast

if TYPE_CHECKING:
    from syrin.agent import Agent
    from syrin.agent.multi_agent import DynamicPipeline, Pipeline

_ServableUnion = Union["Agent", "Pipeline", "DynamicPipeline"]


class Servable:
    """Base class for objects that can be served via HTTP or CLI.

    Provides serve() that branches on protocol:
        - HTTP: FastAPI app + uvicorn
        - CLI: Interactive REPL (prompt, run, show cost)

    Agent, Pipeline, and DynamicPipeline inherit from Servable.
    """

    def serve(
        self,
        config: Any = None,
        *,
        stdin: Any = None,
        stdout: Any = None,
        **config_kwargs: Any,
    ) -> None:
        """Serve this object via HTTP or CLI. Blocks until stopped.

        Args:
            config: Optional ServeConfig. If None, uses config_kwargs.
            stdin: Optional input stream for STDIO protocol.
            stdout: Optional output stream for STDIO protocol.
            **config_kwargs: Override ServeConfig fields (protocol, host, port,
                enable_playground, debug, etc.).

        Example:
            >>> agent.serve(port=8000)  # HTTP
            >>> agent.serve(protocol=ServeProtocol.CLI)  # CLI REPL
            >>> pipeline.serve(protocol=ServeProtocol.CLI, enable_playground=False)
        """
        from syrin.enums import ServeProtocol
        from syrin.serve.config import ServeConfig

        cfg = config if isinstance(config, ServeConfig) else ServeConfig(**config_kwargs)

        if cfg.protocol == ServeProtocol.HTTP:
            try:
                import uvicorn
            except ImportError as e:
                raise ImportError(
                    "HTTP serving requires uvicorn. Install with: uv pip install syrin[serve]"
                ) from e
            from syrin.serve.http import create_http_app

            app = create_http_app(cast(_ServableUnion, self), cfg)
            uvicorn.run(app, host=cfg.host, port=cfg.port)

        elif cfg.protocol == ServeProtocol.CLI:
            from syrin.serve.adapter import to_serveable
            from syrin.serve.cli import run_cli_repl

            serveable = to_serveable(cast(_ServableUnion, self))
            run_cli_repl(serveable, cfg)

        elif cfg.protocol == ServeProtocol.STDIO:
            from syrin.serve.adapter import to_serveable
            from syrin.serve.stdio import run_stdio_protocol

            serveable = to_serveable(cast(_ServableUnion, self))
            run_stdio_protocol(serveable, cfg, stdin=stdin, stdout=stdout)

        else:
            raise ValueError(f"Unknown protocol: {cfg.protocol}")
