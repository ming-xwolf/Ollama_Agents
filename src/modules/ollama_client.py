# src/modules/ollama_client.py

import requests
import json
import shutil
from rich.console import Console
from rich.live import Live
from rich.text import Text
from rich.style import Style
from .save_history import save_interaction
from .logging_setup import logger

class TextStreamer:
    def __init__(self, width):
        self.width = width
        self.current_line = ""
        self.lines = []
        self.style = Style(color="yellow", bold=True)

    def add_text(self, text):
        if len(self.current_line) + len(text) > self.width:
            self.lines.append(self.current_line)
            self.current_line = text
        else:
            self.current_line += text

    def get_output(self):
        return Text(
            "\n".join(self.lines + [self.current_line]),
            style=self.style
        )

class OllamaClient:
    def __init__(self, base_url="http://localhost:11434"):
        self.base_url = base_url
        self.console = Console()
        self.width = shutil.get_terminal_size().columns
        logger.info(f"OllamaClient initialized with base_url: {base_url}")

    def process_prompt(self, prompt: str, model: str, username: str):
        logger.info(f"Processing prompt for user: {username}, model: {model}")
        url = f"{self.base_url}/api/generate"
        headers = {"Content-Type": "application/json"}
        data = {"model": model, "prompt": prompt}

        try:
            with requests.post(
                url,
                headers=headers,
                json=data,
                stream=True
            ) as response:
                if response.status_code == 200:
                    full_response = ""
                    text_streamer = TextStreamer(self.width)

                    with Live(Text("",
                                   style=Style(color="yellow", bold=True)),
                              refresh_per_second=10) as live:
                        for line in response.iter_lines():
                            if line:
                                json_response = json.loads(line)
                                if "response" in json_response:
                                    chunk = json_response["response"]
                                    full_response += chunk
                                    text_streamer.add_text(chunk)
                                    live.update(text_streamer.get_output())
                                if json_response.get("done", False):
                                    break

                    logger.info(f"Response generated for prompt: {prompt[:50]}...")
                    save_interaction(prompt, full_response.strip(), username, model)

                    return full_response.strip()
                else:
                    error_msg = f"Error: Received status code {response.status_code}"
                    logger.error(error_msg)
                    self.console.print(error_msg, style="bold red")
                    return error_msg
        except requests.RequestException as e:
            error_msg = f"Error connecting to Ollama: {e}"
            logger.error(error_msg)
            self.console.print(error_msg, style="bold red")
            return error_msg

# Create a default client instance
default_client = OllamaClient()

def process_prompt(prompt: str, model: str, username: str):
    logger.info(
        f"Processing prompt: prompt='{prompt[:50]}...',"
        f"model={model}, username={username}"
    )
    return default_client.process_prompt(prompt, model, username)

# Make sure to export the process_prompt function
__all__ = ['process_prompt']
