"""Play a test phrase through the same Speaker that ARTEMIS uses."""
from artemis.voice import Speaker

if __name__ == '__main__':
    Speaker(enabled=True).say('Hello. I am Artemis, your personal assistant. How may I help?')
