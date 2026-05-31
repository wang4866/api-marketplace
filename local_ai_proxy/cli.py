"""local-ai: Turn your local Ollama into a production-ready API."""
import click, webbrowser
from . import __version__
from . import client as svc

@click.group(invoke_without_command=True)
@click.version_option(__version__, prog_name="local-ai")
@click.pass_context
def cli(ctx):
    if ctx.invoked_subcommand is not None:
        return
    print(f"Local AI Proxy v{__version__}")
    try:
        h = svc.health()
        print(f"API: {h.get('service','ok')} | Models: {len(svc.list_models())}")
    except Exception as e:
        print(f"API not running ({type(e).__name__}: {e})")
        print("Start with: local-ai serve")
    print("Commands: models, chat, embed, serve, dashboard, docs")

@cli.command()
def models():
    try:
        for m in svc.list_models():
            print(f"  {m['id']:25s} tier={m.get('tier_required','free')}  cost=${m.get('cost_per_1k',0)}/1K")
    except Exception as e:
        print(f"Error: {e}")

@cli.command()
@click.argument("prompt", nargs=-1, required=True)
@click.option("-m", "--model", default="qwen2.5:7b")
def chat(prompt, model):
    text = " ".join(prompt)
    try:
        print(svc.chat(model, text))
    except Exception as e:
        print(f"Error: {e}")

@cli.command()
@click.argument("text", nargs=-1, required=True)
def embed(text):
    text_str = " ".join(text)
    try:
        data = svc.embed(text_str)
        dim = len(data["data"][0]["embedding"])
        print(f"Dim: {dim} | Tokens: {data['usage']['total_tokens']} | Cost: ${data.get('cost', 0):.6f}")
    except Exception as e:
        print(f"Error: {e}")

@cli.command()
def serve():
    import subprocess, os
    plist = os.path.expanduser("~/Library/LaunchAgents/com.marketplace.web2md-api.plist")
    if not os.path.exists(plist):
        print("launchd plist not found")
        return
    r = subprocess.run(["launchctl", "load", plist], capture_output=True, text=True, timeout=5)
    if r.returncode == 0:
        print("API started at http://localhost:8000")

@cli.command()
def dashboard():
    webbrowser.open("http://localhost:8000/admin")

@cli.command()
def docs():
    print("""PYTHON:
  from openai import OpenAI
  client = OpenAI(base_url="http://localhost:8000/v1", api_key="sk-local")
  r = client.chat.completions.create(model="qwen2.5:7b", messages=[{"role":"user","content":"Hello"}])

CURL:
  curl http://localhost:8000/v1/chat/completions -H "Content-Type: application/json" -d '{"model":"qwen2.5:7b","messages":[{"role":"user","content":"Hello"}]}'

DONATE USDT (TRC20): 0x85Ea457bE39E42C05D296D9b526e03a68D48A1f""")
