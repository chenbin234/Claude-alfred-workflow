#!/usr/bin/python3

import os
import sys
import json
from pathlib import Path

# import anthropic
import requests


def env_var(var_name):
    return os.environ.get(var_name)


def file_exists(path):
    return os.path.exists(path)


def file_modified(path):
    return os.path.getmtime(path)


def delete_file(path):
    os.remove(path)


def write_file(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def read_chat(path):
    with open(path, "r", encoding="utf-8") as f:
        chat_string = f.read()
    return json.loads(chat_string)


def append_chat(path, message):
    ongoing_chat = read_chat(path) + [message]
    chat_string = json.dumps(ongoing_chat)
    write_file(path, chat_string)


def markdown_chat(messages, ignore_last_interrupted=True):
    def format_message(msg, idx, all_msgs):
        if msg["role"] == "assistant":
            return f"{msg['content']}\n\n"
        elif msg["role"] == "user":
            user_message = "\n".join(
                [f"### {line}" for line in msg["content"].split("\n")]
            )
            user_twice = idx + 1 < len(all_msgs) and all_msgs[idx + 1]["role"] == "user"
            last_message = idx == len(all_msgs) - 1
            if user_twice or (last_message and not ignore_last_interrupted):
                return f"{user_message}\n\n[Answer Interrupted]\n\n"
            else:
                return f"{user_message}\n\n"
        return ""

    return "".join(
        format_message(msg, idx, messages) for idx, msg in enumerate(messages)
    )


def start_stream(api_endpoint, api_key, model, system_prompt, contextChat):

    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    # Set up the request payload
    payload = {
        "model": model,
        "max_tokens": 2048,
        "system": system_prompt,
        "messages": [{"role": "user", "content": "{}".format(contextChat)}],
    }

    # Send the request
    response = requests.post(api_endpoint, headers=headers, data=json.dumps(payload))

    return response


if __name__ == "__main__":

    # Set up the API endpoint and headers and other parameters
    api_endpoint = "https://api.anthropic.com/v1/messages"
    api_key = env_var("claude_api_key")
    model = env_var("claude_model")
    role = env_var("role_select")
    system_prompt = env_var(role)
    current_question = env_var("current_question")

    conversation_history_file = (
        Path(os.environ.get("alfred_workflow_data")) / "chat.json"
    )

    # load the chat.json file
    conversation_history = read_chat(conversation_history_file)
    conversation_history.append({"role": "user", "content": current_question})

    response = start_stream(
        api_endpoint, api_key, model, system_prompt, conversation_history
    )

    response_data = response.json()

    if response.status_code == 200:

        # Append the assistant's response to the conversation history
        conversation_history.append(
            {
                "role": "assistant",
                "content": response_data["content"][0]["text"],
            }
        )

    else:
        conversation_history.append(
            {
                "role": "assistant",
                "content": "Error-" + str(response.status_code),
            }
        )

    # print("fine")
    # print(type(conversation_history))
    # print(conversation_history)

    data = {
        "response": markdown_chat(conversation_history),
        "footer": "Anatomy of fruits and vegetables",
        "behaviour": {"response": "append", "scroll": "end", "inputfield": "select"},
    }

    print(json.dumps(data))
