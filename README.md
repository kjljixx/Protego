# Protego
An anti-spam discord bot written in discord.py

Invite Link: https://discord.com/api/oauth2/authorize?client_id=1175197240130797658&permissions=8&scope=bot

Protego uses a weighted moving total of the "spam scores" of every message a user sends out - the spam score of each message is calculated with several different elements, including how similar it is to other messages the user sent, how long the message is, and how much space the message takes up
This allows Protego to have a low false-positive and false-negative rate.

# Technical Details

The weighting formula for each message is: 0.95^(time in seconds since message was sent)

OpenAI's [tiktoken](https://github.com/openai/tiktoken) is used to calculate message similarity
