schema_ask_user = {
    "type": "function",
    "function": {
        "name": "ask_user",
        "description": "Asks the user one short clarifying question about what they want and returns their answer. Use it when details that change the program's behavior are missing",
        "parameters": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "A single short question for the user",
                },
            },
            "required": ["question"],
        },
    },
}