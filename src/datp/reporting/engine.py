from __future__ import annotations

import math

from jinja2 import Environment, PackageLoader, select_autoescape

_env = Environment(
    loader=PackageLoader("datp.reporting", "templates"),
    autoescape=select_autoescape(
        enabled_extensions=("html", "htm", "xml"),
        default_for_string=True,
        default=False,
    ),
    trim_blocks=True,
    lstrip_blocks=True,
)


def format_mean_std(mean: float, std: float, bold: bool) -> str:
    if math.isnan(mean):
        return "---"
    text = f"{mean:.3f} ± {std:.3f}"
    if bold:
        return f"\\textbf{{{text}}}"
    return text


def render(template_name: str, **kwargs: object) -> str:
    return _env.get_template(template_name).render(**kwargs)
