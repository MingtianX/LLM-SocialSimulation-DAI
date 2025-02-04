import os
import openai
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
)  # for exponential backoff
 
import logging  
  
# Configure logging  
logging.basicConfig(level=logging.INFO)  
  
# Error callback function
def log_retry_error(retry_state):  
    logging.error(f"Retrying due to error: {retry_state.outcome.exception()}")  

DEFAULT_CONFIG = {
    "engine": "devgpt4-32k",
    "temperature": 0.0,
    "max_tokens": 5000,
    "top_p": 1.0,
    "frequency_penalty": 0.0,
    "presence_penalty": 0.0,
    "stop": None
}

class OpenAIWrapper:
    def __init__(self, config = DEFAULT_CONFIG, system_message=""):
        # TODO: set up your API key with the environment variable OPENAIKEY
        # openai.api_key = "5c09a47bc6a44b44a6094f952882d958"
        # openai.api_type = "azure"
        # openai.api_base = "https://zjudai.openai.azure.com/"
        # openai.api_version = "2023-03-15-preview"
        # openai.api_key = os.environ.get("OPENAI_API_KEY")      

        # if os.environ.get("USE_AZURE")=="True":
        #     print("using azure api")
        #     openai.api_type = "azure"
        # openai.api_base = os.environ.get("API_BASE")
        # openai.api_version = os.environ.get("API_VERSION")

        self.config = config
        print("api config:", config, '\n')

        # count total tokens
        self.completion_tokens = 0
        self.prompt_tokens = 0

        # system message
        self.system_message = system_message # "You are an AI assistant that helps people find information."

    # retry using tenacity
    @retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6), retry_error_callback=log_retry_error)
    def completions_with_backoff(self, **kwargs):
        # print("making api call:", kwargs)
        # print("====================================")
        return openai.ChatCompletion.create(**kwargs)

    def run(self, prompt, n=1, system_message=""):
        """
            prompt: str
            n: int, total number of generations specified
        """
        try:
            # overload system message
            if system_message != "":
                sys_m = system_message
            else:
                sys_m = self.system_message
            if sys_m != "":
                print("adding system message:", sys_m)
                messages = [
                    {"role":"system", "content":sys_m},
                    {"role":"user", "content":prompt}
                ]
            else:
                messages = [
                    {"role":"user","content":prompt}
                ]
            text_outputs = []
            raw_responses = []
            while n > 0:
                cnt = min(n, 10) # number of generations per api call
                n -= cnt
                res = self.completions_with_backoff(messages=messages, n=cnt, **self.config)
                text_outputs.extend([choice["message"]["content"] for choice in res["choices"]])
                # add prompt to log
                res['prompt'] = prompt
                if sys_m != "":
                    res['system_message'] = sys_m
                raw_responses.append(res)
                # log completion tokens
                self.completion_tokens += res["usage"]["completion_tokens"]
                self.prompt_tokens += res["usage"]["prompt_tokens"]

            return text_outputs, raw_responses
        except Exception as e:
            print("an error occurred:", e)
            return [], []

    def compute_gpt_usage(self):
        model = self.config["model"]
        if model == "gpt-3.5-turbo":
            cost = self.completion_tokens / 1000 * 0.002 + self.prompt_tokens / 1000 * 0.0015
        else:
            cost = 0 # TODO: add custom cost calculation for other engines
        # engine = self.config["engine"]
        # if engine == "devgpt4-32k":
        #     cost = self.completion_tokens / 1000 * 0.12 + self.prompt_tokens / 1000 * 0.06
        # else:
        #     cost = 0 # TODO: add custom cost calculation for other engines
        return {"completion_tokens": self.completion_tokens, "prompt_tokens": self.prompt_tokens, "cost": cost}