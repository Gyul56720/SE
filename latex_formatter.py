"""
Discord LaTeX rendering helper / formatter.
Transforms LaTeX expressions or provides image/markdown rendering hints for Discord.
"""
def format_latex(formula: str) -> str:
    # Basic formatter that wraps or converts LaTeX for chat display
    return f"```math\n{formula}\n```"
