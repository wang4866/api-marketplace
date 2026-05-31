"""local-ai: Turn your local Ollama into a production-ready API."""
import click
import webbrowser

from . import api
from . import __version__

@click.group(invoke_without_command=True)
@click.version_option(__version__, prog_name="local-ai")
@click.pass_context
def cli(ctx):
    """Local AI Proxy - Turn your local Ollama into a production-ready API."""
    if ctx.invoked_subcommand is not None:
        return
    print("Local AI Proxy v{}".format(__version__))
    try:
        h = api.health()
        models = api.list_models()
        print("API: {} | Models: {}".format(h.get("service", "ok"), len(models)))
    except Exception as e:
        print("API not running: {} - {}".format(type(e).__name__, e))
        print("Start with: local-ai serve")
    print()
    print("Commands: models, chat, embed, serve, dashboard, api")

@cli.command()
def models():
    """List available models."""
    try:
        models = api.list_models()
        for m in models:
            print("{} [tier: {}, cost: ${}/1K]".format(
                m.get("id", "?"),
                m.get("tier_required", "free"),
                m.get("cost_per_1k", "0")
            ))
    except Exception as e:
        print("Error: {} - {}".format(type(e).__name__, e))

@cli.command()
@click.argument("prompt", nargs=-1, required=True)
@click.option("-m", "--model", default="qwen2.5:7b")
def chat(prompt, model):
    """Chat with AI."""
    text = " ".join(prompt)
    try:
        response = api.chat(model, text)
        print(response)
    except Exception as e:
        print("Error: {}".format(e))

@cli.command()
@click.argument("text", nargs=-1, required=True)
def embed(text):
    """Get embeddings."""
    text_str = " ".join(text)
    try:
        data = api.embed(text_str)
        dim = len(data["data"][0]["embedding"])
        print("Dimension: {} | Tokens: {} | Cost: ${}".format(
            dim, data["usage"]["total_tokens"], data.get("cost", 0)
        ))
    except Exception as e:
        print("Error: {}".format(e))

@cli.command()
def serve():
    """Start API server."""
    import subprocess, os
    plist = os.path.expanduser("~/Library/LaunchAgents/com.marketplace.web2md-api.plist")
    if os.path.exists(plist):
        r = subprocess.run(["launchctl", "load", plist], capture_output=True, text=True, timeout=5)
        if r.returncode == 0:
            print("API started at http://localhost:8000")
        else:
            print("Error: {}".format(r.stderr.strip() or r.stdout.strip()))
    else:
        print("launchd plist not found")
        print("Manual: cd ~/api-marketplace && .venv/bin/python -m uvicorn app.main:app")

@cli.command()
def dashboard():
    """Open admin panel."""
    webbrowser.open("http://localhost:8000/admin")
    print("Opening admin panel...")

@cli.command()
def api():
    """Show API examples."""
    print("""Use with Python:
  from openai import OpenAI
  client = OpenAI(base_url="http://localhost:8000/v1", api_key="sk-local")
  r = client.chat.completions.create(model="qwen2.5:7b", messages=[{"role":"user","content":"Hello"}])
  print(r.choices[0].message.content)
    
Use with curl:
  curl http://localhost:8000/v1/chat/completions -H "Content-Type: application/json" -d '{"model":"qwen2.5:7b","messages":[{"role":"user","content":"Hello"}]}'

USDT Donations: 0x85Ea457bE39E42C05D296D9b526e03a68D48A1f
""")

if __name__ == "__main__":
    cli()
